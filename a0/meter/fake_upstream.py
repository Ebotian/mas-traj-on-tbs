#!/usr/bin/env python3
"""A local stand-in for `api.deepseek.com`, used only to prove the meter without spending money.

It speaks the same wire shapes DeepSeek serves on its two faces — OpenAI chat completions (with
DeepSeek's native `prompt_cache_*` fields), the OpenAI Responses API, and Anthropic Messages with
`cache_read_input_tokens` — and it can be told to misbehave in the two ways that matter for a
usage ledger: **omit usage entirely**, and **cut the stream before usage arrives**.

The scenario is selected by the non-hop-by-hop header `X-Fake-Scenario`, not by the path or the
model name, so the requests a test sends can be realistic (`model: "deepseek-flash"`) while the
response shape stays under the test's control.

Every request is appended to `--log` as jsonl. That log is how "the refusal never touched the
upstream" is proved: a refusal that reaches here would leave a line. It is *also* how "the proxy
sent a correctly framed request" is proved: the log records the request's framing headers
verbatim, the number of body bytes the server actually read, and that body's sha256. A mock that
records only the response cannot tell a body that arrived from a body that was silently dropped --
which is precisely how this upstream used to let 55/55 checks pass while it read zero bytes of
every request (`_read_body` below is now the *server's* framing decision, not a `content-length`
lookup).

Its shape is deliberately the wire's, not the test's:

* a request body exists only if `Content-Length` or `Transfer-Encoding: chunked` declares it --
  the rule a conforming HTTP/1.1 server applies, and the rule the proxy used to violate;
* a body-bearing request without framing, with an empty body, or with a body that is not JSON is
  answered `400` with DeepSeek's own wording -- a real provider never parses nothing and calls it
  success;
* a request with no `Authorization`/`x-api-key` is answered `401`, as the real endpoint is.

Deliberately *not* a general mock: there is no usage computation, no tokenizer, and no model.
Every token figure below is a constant chosen by the test, which is the point — the meter must
reproduce it exactly, and any invention by the meter shows up as a mismatch.
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import socket
import ssl
import sys
import threading
import time

# DeepSeek's wording for a body it could not read, quoted from the failure that motivated the
# framing fix in `meter_proxy.py`.
BODY_400 = {
    "error": {
        "message": "Failed to parse the request body as JSON: EOF while parsing a value at "
                   "line 1 column 0",
        "type": "invalid_request_error",
    }
}
AUTH_401 = {"error": {"message": "Authentication Fails", "type": "authentication_error"}}
BODY_METHODS = {"POST", "PUT", "PATCH"}

SCENARIOS = {
    # OpenAI chat completions, non-streaming, DeepSeek's native usage fields.
    "chat-usage-ns": {"mode": "json", "body": {
        "id": "fake-chatcmpl-0001", "object": "chat.completion", "created": 1789000000,
        "model": "deepseek-flash",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": "ok"}}],
        "usage": {"prompt_tokens": 11520, "completion_tokens": 312, "total_tokens": 11832,
                  "prompt_cache_hit_tokens": 1280, "prompt_cache_miss_tokens": 10240,
                  "prompt_tokens_details": {"cached_tokens": 1280}}}},
    # OpenAI chat completions, streaming, usage only in the final data chunk.
    "chat-usage-stream": {"mode": "sse", "kind": "chat_stream", "delay_before_usage": 0.4},
    # OpenAI chat completions, non-streaming, usage deliberately absent.
    "chat-nousage": {"mode": "json", "body": {
        "id": "fake-chatcmpl-0002", "object": "chat.completion", "created": 1789000001,
        "model": "deepseek-flash",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": "no usage here"}}]}},
    # Anthropic Messages, non-streaming, carrying cache-read and cache-creation fields.
    "anthropic-cache": {"mode": "json", "body": {
        "id": "fake-msg-0001", "type": "message", "role": "assistant",
        "model": "deepseek-flash", "stop_reason": "end_turn",
        "content": [{"type": "text", "text": "ok"}],
        "usage": {"input_tokens": 120, "output_tokens": 55,
                  "cache_read_input_tokens": 2048, "cache_creation_input_tokens": 64}}},
    # Anthropic Messages, streaming: usage is split across message_start and message_delta.
    "anthropic-stream": {"mode": "sse", "kind": "anthropic_stream", "delay_before_usage": 0.0},
    # Anthropic Messages, streamed, then cut before message_delta ever carries output usage.
    "anthropic-truncated": {"mode": "sse", "kind": "anthropic_truncated"},
    # OpenAI Responses API, streaming, usage inside response.completed.
    "responses-stream": {"mode": "sse", "kind": "responses_stream"},
    # OpenAI Responses API, non-streaming: input total present, cache split present.
    "responses-ns": {"mode": "json", "body": {
        "id": "fake-resp-0001", "object": "response", "model": "deepseek-flash",
        "output": [], "status": "completed",
        "usage": {"input_tokens": 4000, "output_tokens": 200,
                  "input_tokens_details": {"cached_tokens": 1500},
                  "output_tokens_details": {"reasoning_tokens": 40}}}},
    # A generic OpenAI-compatible provider that reports a prompt total but no cache split.
    "generic-nosplit": {"mode": "json", "body": {
        "id": "fake-generic-0001", "object": "chat.completion", "model": "some-other-model",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": "ok"}}],
        "usage": {"prompt_tokens": 1000, "completion_tokens": 10, "total_tokens": 1010}}},
    # An HTTP error body, which never carries usage.
    "error-401": {"mode": "json", "status": 401, "body": {
        "error": {"message": "Authentication Fails", "type": "authentication_error"}}},
    # A non-2xx whose body is not JSON at all: a gateway's HTML page, an auth proxy's text.
    # Nothing in the body names the status, so the row must.
    "error-502-html": {"mode": "raw", "status": 502, "content_type": "text/html",
                       "body": b"<html><body><h1>502 Bad Gateway</h1></body></html>"},
    "error-429-text": {"mode": "raw", "status": 429, "content_type": "text/plain",
                       "body": b"rate limited: slow down"},
    # A 2xx whose body is not JSON: the reason must stay `unparseable_response_body`.
    "ok-200-notjson": {"mode": "raw", "status": 200, "content_type": "text/plain",
                       "body": b"not json at all"},
    # A 2xx with an empty body: the reason must be `empty_response_body`.
    "ok-200-empty": {"mode": "raw", "status": 200, "content_type": "application/json",
                     "body": b""},
}

CHAT_CHUNKS = [
    {"id": "fake-stream-0001", "object": "chat.completion.chunk", "model": "deepseek-flash",
     "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}}]},
    {"id": "fake-stream-0001", "object": "chat.completion.chunk", "model": "deepseek-flash",
     "choices": [{"index": 0, "delta": {"content": "hello "}}]},
    {"id": "fake-stream-0001", "object": "chat.completion.chunk", "model": "deepseek-flash",
     "choices": [{"index": 0, "delta": {"content": "world"}}]},
    {"id": "fake-stream-0001", "object": "chat.completion.chunk", "model": "deepseek-flash",
     "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
]

CHAT_USAGE = {"prompt_tokens": 11264, "completion_tokens": 296, "total_tokens": 11560,
              "prompt_cache_hit_tokens": 1024, "prompt_cache_miss_tokens": 10240}

ANTHROPIC_START = {
    "type": "message_start",
    "message": {"id": "fake-msg-stream-0001", "type": "message", "role": "assistant",
                "model": "deepseek-flash", "content": [], "stop_reason": None,
                "usage": {"input_tokens": 96, "output_tokens": 1,
                          "cache_read_input_tokens": 3072,
                          "cache_creation_input_tokens": 0}}}
ANTHROPIC_DELTAS = [
    {"type": "content_block_start", "index": 0,
     "content_block": {"type": "text", "text": ""}},
    {"type": "content_block_delta", "index": 0,
     "delta": {"type": "text_delta", "text": "hello "}},
    {"type": "content_block_delta", "index": 0,
     "delta": {"type": "text_delta", "text": "world"}},
    {"type": "content_block_stop", "index": 0},
]
ANTHROPIC_DONE = {"type": "message_delta", "delta": {"stop_reason": "end_turn"},
                  "usage": {"output_tokens": 73}}

RESPONSES_DELTAS = [
    {"type": "response.created", "response": {"id": "fake-resp-stream-0001",
                                              "model": "deepseek-flash", "status": "in_progress",
                                              "usage": None}},
    {"type": "response.output_text.delta", "item_id": "item_1", "delta": "hello "},
    {"type": "response.output_text.delta", "item_id": "item_1", "delta": "world"},
]
RESPONSES_COMPLETED = {
    "type": "response.completed",
    "response": {"id": "fake-resp-stream-0001", "model": "deepseek-flash",
                 "status": "completed", "output": [],
                 "usage": {"input_tokens": 2048, "output_tokens": 128,
                           "input_tokens_details": {"cached_tokens": 512}}},
}


def sse(event: str | None, payload: dict) -> bytes:
    out = b""
    if event:
        out += ("event: %s\n" % event).encode()
    out += b"data: " + json.dumps(payload, separators=(",", ":")).encode() + b"\n\n"
    return out


def dechunk(raw: bytes) -> tuple[bytes, bool]:
    """Decode a chunked body; returns `(body, saw_terminating_chunk)`."""
    out = bytearray()
    pos = 0
    while True:
        end = raw.find(b"\r\n", pos)
        if end < 0:
            return bytes(out), False
        try:
            size = int(raw[pos:end].split(b";")[0].strip(), 16)
        except ValueError:
            return bytes(out), False
        if size == 0:
            return bytes(out), True
        start = end + 2
        if len(raw) < start + size + 2:
            return bytes(out), False
        out += raw[start:start + size]
        pos = start + size + 2


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "a0-fake-upstream/1"

    def log_message(self, *_args):
        pass

    def _read_body(self) -> tuple[bytes, dict]:
        """Frame the request body the way an HTTP/1.1 server does.

        Returns `(body, info)`. `info["framing"]` is the mechanism the *client* used -- this is a
        property of the bytes on the socket, not of the scenario the test wants, so a client that
        sends nothing framed is visible here as `framing: "none"` with an empty body rather than
        as a request whose body the mock quietly invented a length of zero for.
        """
        transfer_encoding = (self.headers.get("transfer-encoding") or "").lower()
        content_length = self.headers.get("content-length")
        info: dict = {
            "request_line": self.requestline,
            "content_length_header": content_length,
            "transfer_encoding_header": transfer_encoding or None,
            "declared_length": None,
            "framing": None,
        }
        if "chunked" in transfer_encoding:
            info["framing"] = "chunked"
            raw = b""
            while True:
                line = self.rfile.readline(65536)
                if not line:
                    break
                raw += line
                try:
                    size = int(line.split(b";")[0].strip(), 16)
                except ValueError:
                    break
                if size == 0:
                    while True:  # trailer section, terminated by a blank line
                        trailer = self.rfile.readline(65536)
                        raw += trailer
                        if trailer in (b"\r\n", b"\n", b""):
                            break
                    break
                raw += self.rfile.read(size)
                raw += self.rfile.readline(3)
            body, complete = dechunk(raw)
            info["chunked_complete"] = complete
            return body, info
        if content_length is not None:
            info["framing"] = "content-length"
            try:
                want = int(content_length)
            except ValueError:
                info["framing_error"] = "unparsable_content_length"
                return b"", info
            info["declared_length"] = want
            return self.rfile.read(want), info
        info["framing"] = "none"
        return b"", info

    def _record(self, body: bytes, framing: dict, framing_error: str | None) -> dict:
        payload = {}
        json_ok = False
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
            json_ok = True
        except (ValueError, UnicodeDecodeError):
            pass
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "method": self.command,
            "path": self.path,
            "host_header": self.headers.get("host"),
            "scenario": self.headers.get("x-fake-scenario"),
            "model": payload.get("model") if isinstance(payload, dict) else None,
            "stream": payload.get("stream") if isinstance(payload, dict) else None,
            "authorization_present": bool(self.headers.get("authorization")),
            "x_api_key_present": bool(self.headers.get("x-api-key")),
            "accept_encoding": self.headers.get("accept-encoding"),
            # --- what the upstream actually read, as opposed to what it answered ---
            "request_line": framing.get("request_line"),
            "framing": framing.get("framing"),
            "content_length_header": framing.get("content_length_header"),
            "transfer_encoding_header": framing.get("transfer_encoding_header"),
            "declared_length": framing.get("declared_length"),
            "chunked_complete": framing.get("chunked_complete"),
            "framing_error": framing_error,
            "body_bytes": len(body),
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "body_json_ok": json_ok,
        }
        log_path = self.server.log_path
        if log_path:
            with self.server.log_lock:
                with open(log_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, separators=(",", ":")) + "\n")
        return record

    def _send_json(self, status: int, body: dict) -> None:
        raw = json.dumps(body, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("x-request-id", "fake-req-%d" % int(time.time() * 1000))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(raw)

    def _send_raw(self, status: int, body: bytes, content_type: str) -> None:
        """Answer with bytes that are deliberately not JSON, to exercise the unparseable path."""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("x-request-id", "fake-req-%d" % int(time.time() * 1000))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _flush_chunked(self, data: bytes) -> None:
        """Write one HTTP/1.1 chunk and flush it, so the proxy can forward it immediately."""
        self.wfile.write(b"%x\r\n" % len(data) + data + b"\r\n")
        self.wfile.flush()

    def _finish_chunked(self) -> None:
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()

    def _stream_chat(self, delay_before_usage: float) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Connection", "close")
        self.end_headers()
        for chunk in CHAT_CHUNKS:
            self._flush_chunked(sse(None, chunk))
        time.sleep(delay_before_usage)
        self._flush_chunked(sse(None, {"id": "fake-stream-0001", "object": "chat.completion.chunk",
                                       "model": "deepseek-flash", "choices": [],
                                       "usage": CHAT_USAGE}))
        self._flush_chunked(b"data: [DONE]\n\n")
        self._finish_chunked()

    def _stream_anthropic(self, truncate: bool) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Connection", "close")
        self.end_headers()
        self._flush_chunked(sse("message_start", ANTHROPIC_START))
        for delta in ANTHROPIC_DELTAS:
            self._flush_chunked(sse(delta["type"], delta))
        if truncate:
            # Cut here: message_delta (which carries output_tokens) never arrives, and neither
            # does message_stop. The terminating 0-length chunk is deliberately omitted.
            self.close_connection = True
            try:
                self.wfile.flush()
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            return
        self._flush_chunked(sse("message_delta", ANTHROPIC_DONE))
        self._flush_chunked(sse("message_stop", {"type": "message_stop"}))
        self._finish_chunked()

    def _stream_responses(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Connection", "close")
        self.end_headers()
        for item in RESPONSES_DELTAS:
            self._flush_chunked(sse(item["type"], item))
        self._flush_chunked(sse("response.completed", RESPONSES_COMPLETED))
        self._finish_chunked()

    def _framing_error(self, body: bytes, framing: dict) -> str | None:
        """Why a *real* provider would refuse this request, or None if it would serve it.

        The mock must not be more forgiving than the wire: every reason here is one a conforming
        server applies, and each of them was invisible while the mock read `content-length` and
        called a missing body zero bytes.
        """
        if framing.get("framing_error"):
            return framing["framing_error"]
        if self.command in BODY_METHODS:
            if framing["framing"] == "none":
                return "unframed_request_body"
            if framing["framing"] == "chunked" and not framing.get("chunked_complete"):
                return "truncated_chunked_body"
            if framing["framing"] == "content-length" \
                    and len(body) < (framing.get("declared_length") or 0):
                return "short_body"
            if not body:
                return "empty_body"
            try:
                json.loads(body.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return "body_not_json"
            if not (self.headers.get("authorization") or self.headers.get("x-api-key")):
                return "no_credentials"
        return None

    def _handle(self):
        body, framing = self._read_body()
        framing_error = self._framing_error(body, framing)
        record = self._record(body, framing, framing_error)
        if framing_error == "no_credentials":
            self._send_json(401, AUTH_401)
            return
        if framing_error is not None:
            self._send_json(400, BODY_400)
            return
        scenario = record["scenario"] or "chat-usage-ns"
        spec = SCENARIOS.get(scenario)
        if spec is None:
            self._send_json(400, {"error": {"message": "unknown fake scenario %r" % scenario}})
            return
        if spec["mode"] == "json":
            self._send_json(spec.get("status", 200), spec["body"])
            return
        if spec["mode"] == "raw":
            self._send_raw(spec.get("status", 200), spec["body"],
                           spec.get("content_type", "application/octet-stream"))
            return
        kind = spec["kind"]
        if kind == "chat_stream":
            self._stream_chat(spec.get("delay_before_usage", 0.0))
        elif kind == "anthropic_stream":
            self._stream_anthropic(truncate=False)
        elif kind == "anthropic_truncated":
            self._stream_anthropic(truncate=True)
        elif kind == "responses_stream":
            self._stream_responses()
        else:
            self._send_json(500, {"error": {"message": "unimplemented kind %r" % kind}})

    do_GET = _handle
    do_POST = _handle
    do_HEAD = _handle


class FakeUpstream(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, addr, handler, *, log_path, certfile=None, keyfile=None):
        super().__init__(addr, handler)
        self.log_path = log_path
        self.log_lock = threading.Lock()
        if certfile:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(certfile, keyfile)
            self.socket = ctx.wrap_socket(self.socket, server_side=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="local fake DeepSeek upstream (no spend)")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--cert")
    parser.add_argument("--key")
    parser.add_argument("--log")
    parser.add_argument("--port-file", help="write the bound port here once listening")
    args = parser.parse_args(argv)

    server = FakeUpstream((args.host, args.port), Handler, log_path=args.log,
                          certfile=args.cert, keyfile=args.key)
    port = server.server_address[1]
    if args.port_file:
        with open(args.port_file, "w", encoding="utf-8") as handle:
            handle.write(str(port))
    sys.stderr.write("fake upstream on %s://%s:%d\n"
                     % ("https" if args.cert else "http", args.host, port))
    sys.stderr.flush()
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
