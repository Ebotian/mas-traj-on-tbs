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
upstream" is proved: a refusal that reaches here would leave a line.

Deliberately *not* a general mock: there is no usage computation, no tokenizer, and no model.
Every token figure below is a constant chosen by the test, which is the point — the meter must
reproduce it exactly, and any invention by the meter shows up as a mismatch.
"""

from __future__ import annotations

import argparse
import http.server
import json
import socket
import ssl
import sys
import threading
import time

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


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "a0-fake-upstream/1"

    def log_message(self, *_args):
        pass

    def _record(self, body: bytes) -> dict:
        payload = {}
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
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

    def _handle(self):
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else b""
        record = self._record(body)
        scenario = record["scenario"] or "chat-usage-ns"
        spec = SCENARIOS.get(scenario)
        if spec is None:
            self._send_json(400, {"error": {"message": "unknown fake scenario %r" % scenario}})
            return
        if spec["mode"] == "json":
            self._send_json(spec.get("status", 200), spec["body"])
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
