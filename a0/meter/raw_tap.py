#!/usr/bin/env python3
"""A raw TCP tap on the metering proxy's *upstream* leg, and the framing proof built on it.

`fake_upstream.py` is the meter's behavioural mock: it decides what the provider *answers*. It
cannot prove what the proxy *sent*, because it parses the request with `http.server` and the
selftest reads only the response. This tool is the opposite: a socket that records the exact bytes
it receives, so a claim about the outbound request is a claim about captured bytes.

It is deliberately a *wire-shaped* server: it frames its own reads the way a conforming HTTP/1.1
provider does (a request body exists only if `Content-Length` or `Transfer-Encoding: chunked`
declares it), and it answers an unframed body-bearing request the way DeepSeek does:

    400 {"error": {"message": "Failed to parse the request body as JSON:
         EOF while parsing a value at line 1 column 0", ...}}

Usage:

    # the proof: three client shapes, before/after, raw bytes + verdicts
    python3 raw_tap.py --proof --out evidence --label after
    python3 raw_tap.py --proof --out evidence --label before \
        --proxy /tmp/old_meter_proxy.py

    # just the tap (no proxy): record whatever connects to it
    python3 raw_tap.py --port 8899 --log /tmp/tap.jsonl [--plain]

Exit code is non-zero if any client request failed to arrive at the upstream correctly framed,
with a body whose length disagrees with its framing header, or with bytes other than the ones the
client sent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import ssl
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))

IDLE_BODY_SECONDS = 0.4
MAX_HEAD_BYTES = 1 << 20
MAX_BODY_BYTES = 64 << 20

# DeepSeek's answer to a body it could not read, quoted from the failure that motivated this tool.
UNFRAMED_400 = {
    "error": {
        "message": "Failed to parse the request body as JSON: EOF while parsing a value at "
                   "line 1 column 0",
        "type": "invalid_request_error",
        "code": "invalid_request_error",
    }
}

USAGE = {"prompt_tokens": 4096, "completion_tokens": 8, "total_tokens": 4104,
         "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 4096}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_port(port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.05)
    return False


def parse_head(raw: bytes) -> tuple[str, list[tuple[str, str]]]:
    text = raw.decode("iso-8859-1")
    head, _, _ = text.partition("\r\n\r\n")
    lines = head.split("\r\n")
    headers = []
    for line in lines[1:]:
        name, _, value = line.partition(":")
        headers.append((name.strip().lower(), value.strip()))
    return lines[0], headers


def header_of(headers: list[tuple[str, str]], name: str) -> str | None:
    for key, value in headers:
        if key == name:
            return value
    return None


def dechunk(raw: bytes) -> tuple[bytes, str | None]:
    """Decode a chunked body; returns `(body, error_or_None)`."""
    out = bytearray()
    pos = 0
    while True:
        end = raw.find(b"\r\n", pos)
        if end < 0:
            return bytes(out), "missing_chunk_size_line"
        try:
            size = int(raw[pos:end].split(b";")[0].strip(), 16)
        except ValueError:
            return bytes(out), "bad_chunk_size"
        if size == 0:
            return bytes(out), None
        start = end + 2
        if len(raw) < start + size + 2:
            return bytes(out), "truncated_chunk"
        out += raw[start:start + size]
        pos = start + size + 2


class Tap:
    """A raw socket that records the bytes of every request, then answers one canned response."""

    def __init__(self, *, tls_context: ssl.SSLContext | None = None) -> None:
        self.tls_context = tls_context
        self.records: list[dict] = []
        self.lock = threading.Lock()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(16)
        self.port = self.sock.getsockname()[1]
        self._stop = threading.Event()

    def start(self) -> None:
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()
        try:
            self.sock.close()
        except OSError:
            pass

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn: socket.socket) -> None:
        try:
            if self.tls_context is not None:
                conn = self.tls_context.wrap_socket(conn, server_side=True)
            record = self._read_and_record(conn)
            self._answer(conn, record)
        except (OSError, ssl.SSLError) as exc:
            with self.lock:
                self.records.append({"tap_error": "%s: %s" % (type(exc).__name__, exc)})
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _read_and_record(self, conn: socket.socket) -> dict:
        conn.settimeout(10.0)
        raw = b""
        while b"\r\n\r\n" not in raw:
            chunk = conn.recv(65536)
            if not chunk:
                break
            raw += chunk
            if len(raw) > MAX_HEAD_BYTES:
                break
        head_raw, _, body_raw = raw.partition(b"\r\n\r\n")
        request_line, headers = parse_head(raw)
        content_length = header_of(headers, "content-length")
        transfer_encoding = header_of(headers, "transfer-encoding")

        if content_length is not None:
            framing = "content-length"
            want = int(content_length)
            while len(body_raw) < want:
                try:
                    chunk = conn.recv(min(65536, want - len(body_raw)))
                except socket.timeout:
                    break
                if not chunk:
                    break
                body_raw += chunk
            body = body_raw[:want]
            body_note = None
        elif transfer_encoding is not None and "chunked" in transfer_encoding.lower():
            framing = "chunked"
            while not (body_raw.endswith(b"0\r\n\r\n") or body_raw.endswith(b"\r\n0\r\n\r\n")):
                try:
                    chunk = conn.recv(65536)
                except socket.timeout:
                    break
                if not chunk:
                    break
                body_raw += chunk
            body, body_note = dechunk(body_raw)
        else:
            # No framing header. A conforming server reads no body at all; the idle window is
            # only so this recorder can *show* the stray bytes instead of losing them.
            framing = "none"
            garbled = body_raw
            deadline = time.time() + IDLE_BODY_SECONDS
            while time.time() < deadline:
                conn.settimeout(max(0.01, deadline - time.time()))
                try:
                    chunk = conn.recv(65536)
                except socket.timeout:
                    break
                if not chunk:
                    break
                garbled += chunk
            body = garbled
            body_note = "unframed:%d stray bytes after an inert idle window" % len(garbled)

        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "request_line": request_line,
            "head_bytes": head_raw,
            "framing": framing,
            "content_length_header": content_length,
            "transfer_encoding_header": transfer_encoding,
            "declared_length": (int(content_length) if content_length is not None else None),
            "body_bytes": len(body),
            "body": body,
            "body_sha256": sha256(body),
            "body_note": body_note,
        }
        try:
            payload = json.loads(body.decode("utf-8"))
            record["body_json_ok"] = True
            record["model_in_body"] = payload.get("model") if isinstance(payload, dict) else None
        except (ValueError, UnicodeDecodeError):
            record["body_json_ok"] = False
            record["model_in_body"] = None
        with self.lock:
            self.records.append(record)
        return record

    def _answer(self, conn: socket.socket, record: dict) -> None:
        if record.get("framing") == "none" and record.get("body_bytes", 0) > 0:
            payload, status = UNFRAMED_400, 400
        else:
            payload, status = ({"id": "tap-0001", "object": "chat.completion",
                                "model": "deepseek-flash",
                                "choices": [{"index": 0, "finish_reason": "stop",
                                             "message": {"role": "assistant", "content": "ok"}}],
                                "usage": USAGE}, 200)
        body = json.dumps(payload, separators=(",", ":")).encode()
        head = ("HTTP/1.1 %d %s\r\nContent-Type: application/json\r\nContent-Length: %d\r\n"
                "x-request-id: tap-req-1\r\nConnection: close\r\n\r\n"
                % (status, "OK" if status == 200 else "Bad Request", len(body)))
        conn.sendall(head.encode("iso-8859-1") + body)


# ------------------------------------------------------------------------------------------
# RFC 4648-ish helpers used only by the rendering below
# ------------------------------------------------------------------------------------------


def render(record: dict) -> list[str]:
    out = []
    out.append("  request-line: %s" % record.get("request_line"))
    out.append("  framing: %s" % record.get("framing"))
    out.append("      Content-Length header: %r" % record.get("content_length_header"))
    out.append("      Transfer-Encoding header: %r" % record.get("transfer_encoding_header"))
    out.append("      body bytes actually received: %d" % record.get("body_bytes"))
    out.append("      body sha256: %s" % record.get("body_sha256"))
    if record.get("body_note"):
        out.append("      note: %s" % record["body_note"])
    raw = record.get("head_bytes") or b""
    out.append("  --- raw bytes on the wire (head verbatim) ---")
    for line in raw.decode("iso-8859-1").split("\r\n"):
        out.append("      %s" % line)
    body = record.get("body") or b""
    if body:
        text = body.decode("utf-8", "replace")
        out.append("  --- body bytes (%d) ---" % len(body))
        out.append("      %s" % (text if len(text) <= 400 else text[:400] + "...[truncated]"))
    else:
        out.append("  --- body bytes (0) ---  <- nothing followed the blank line")
    return out


def make_certs(work: str) -> tuple[str, str, str]:
    """A throwaway CA and a 127.0.0.1 certificate, so the tap sits behind a real TLS leg."""
    ca_key = os.path.join(work, "tap_ca.key")
    ca_pem = os.path.join(work, "tap_ca.pem")
    srv_key = os.path.join(work, "tap_srv.key")
    srv_csr = os.path.join(work, "tap_srv.csr")
    srv_pem = os.path.join(work, "tap_srv.pem")
    ext = os.path.join(work, "tap_srv.ext")
    with open(ext, "w", encoding="utf-8") as handle:
        handle.write("subjectAltName=IP:127.0.0.1,DNS:localhost\nbasicConstraints=CA:FALSE\n")
    run = lambda *args: subprocess.run(args, check=True, capture_output=True, cwd=work)  # noqa: E731
    run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", ca_key,
        "-out", ca_pem, "-days", "2", "-subj", "/CN=a0-meter-tap-ca",
        "-addext", "basicConstraints=critical,CA:TRUE",
        "-addext", "keyUsage=critical,keyCertSign,cRLSign")
    run("openssl", "req", "-newkey", "rsa:2048", "-nodes", "-keyout", srv_key,
        "-out", srv_csr, "-subj", "/CN=127.0.0.1")
    run("openssl", "x509", "-req", "-in", srv_csr, "-CA", ca_pem, "-CAkey", ca_key,
        "-CAcreateserial", "-out", srv_pem, "-days", "2", "-extfile", ext)
    return ca_pem, srv_pem, srv_key


# ------------------------------------------------------------------------------------------
# The proof
# ------------------------------------------------------------------------------------------

CLIENT_BODY = {"model": "deepseek-flash", "messages": [{"role": "user", "content": "framing"}],
               "max_tokens": 8}


def send_content_length(port: int, token: str, body: dict) -> bytes:
    payload = json.dumps(body).encode()
    raw = (b"POST /v1/chat/completions HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n"
           % port
           + b"Content-Type: application/json\r\nAuthorization: Bearer tap-not-a-real-key\r\n"
           + b"X-A0-Meter-Token: " + token.encode() + b"\r\n"
           + b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload)
    return exchange(port, raw), payload


def send_chunked(port: int, token: str, body: dict) -> bytes:
    payload = json.dumps(body).encode()
    half = len(payload) // 2
    framed = (b"%x\r\n" % half + payload[:half] + b"\r\n"
              + b"%x\r\n" % (len(payload) - half) + payload[half:] + b"\r\n"
              + b"0\r\n\r\n")
    raw = (b"POST /v1/chat/completions HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n"
           % port
           + b"Content-Type: application/json\r\nAuthorization: Bearer tap-not-a-real-key\r\n"
           + b"X-A0-Meter-Token: " + token.encode() + b"\r\n"
           + b"Transfer-Encoding: chunked\r\n\r\n" + framed)
    return exchange(port, raw), payload


def send_unframed(port: int, token: str, body: dict) -> bytes:
    """A body with no framing header: what the proxy itself used to emit. Never legal HTTP/1.1."""
    payload = json.dumps(body).encode()
    raw = (b"POST /v1/chat/completions HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n"
           % port
           + b"Content-Type: application/json\r\nAuthorization: Bearer tap-not-a-real-key\r\n"
           + b"X-A0-Meter-Token: " + token.encode() + b"\r\n\r\n" + payload)
    return exchange(port, raw), payload


def exchange(port: int, raw: bytes, timeout: float = 20.0) -> bytes:
    sock = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    sock.sendall(raw)
    out = b""
    sock.settimeout(timeout)
    while True:
        try:
            chunk = sock.recv(65536)
        except socket.timeout:
            break
        if not chunk:
            break
        out += chunk
    sock.close()
    return out


def run_proof(args: argparse.Namespace) -> int:
    work = os.path.abspath(args.work)
    out = os.path.abspath(args.out)
    os.makedirs(work, exist_ok=True)
    os.makedirs(out, exist_ok=True)

    ctx = None
    ca_pem = None
    if not args.plain:
        ca_pem, srv_pem, srv_key = make_certs(work)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(srv_pem, srv_key)

    tap = Tap(tls_context=ctx)
    tap.start()
    scheme = "http" if args.plain else "https"

    proxy_port = free_port()
    ledger = os.path.join(work, "ledger_%s.jsonl" % args.label)
    for path in (ledger,):
        if os.path.exists(path):
            os.remove(path)
    cmd = [sys.executable, os.path.abspath(args.proxy),
           "--campaign-id", "C_tap", "--arm-id", "A_tap",
           "--port", str(proxy_port), "--ledger", ledger,
           "--upstream-base", "%s://127.0.0.1:%d" % (scheme, tap.port),
           "--allowlist", "127.0.0.1,api.deepseek.com",
           "--no-fsync", "--token", "tok-tap"]
    if ca_pem:
        cmd += ["--upstream-ca", ca_pem]
    log_path = os.path.join(work, "proxy_%s.txt" % args.label)
    handle = open(log_path, "ab")
    # `--proxy` may point at a copy outside this directory (that is how 'before' is captured),
    # so `meter_core` has to be importable from where the proxy is *not*.
    env = dict(os.environ)
    env["PYTHONPATH"] = HERE + os.pathsep + env.get("PYTHONPATH", "")
    proxy = subprocess.Popen(cmd, stdout=handle, stderr=subprocess.STDOUT, cwd=HERE, env=env)
    if not wait_for_port(proxy_port):
        handle.close()
        proxy.kill()
        tap.stop()
        print("proxy failed to start; console:")
        print(open(log_path).read())
        return 1

    clients = [("A: client uses Content-Length", send_content_length),
               ("B: client uses Transfer-Encoding: chunked", send_chunked),
               ("C: client sends an unframed body (illegal, but the old proxy emitted one)",
                send_unframed)]
    observed = []
    for name, sender in clients:
        before = len(tap.records)
        response, sent = sender(proxy_port, "tok-tap", CLIENT_BODY)
        time.sleep(0.4)
        with tap.lock:
            new = tap.records[before:]
        record = new[0] if new and "tap_error" not in new[0] else None
        observed.append({"name": name, "response": response, "sent": sent, "record": record})

    proxy.terminate()
    try:
        proxy.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proxy.kill()
    handle.close()
    tap.stop()

    lines = ["a0/meter framing proof -- label=%s proxy=%s (sha256 %s) upstream=%s://127.0.0.1:%d"
             % (args.label, os.path.abspath(args.proxy),
                hashlib.sha256(open(args.proxy, "rb").read()).hexdigest(), scheme, tap.port),
             "tap: raw socket capture of the bytes the upstream actually received",
             ""]
    verdicts = []
    for item in observed:
        lines.append("=== %s ===" % item["name"])
        status = item["response"].split(b"\r\n")[0].decode("iso-8859-1") if item["response"] else ""
        lines.append("  client sent %d body bytes" % len(item["sent"]))
        lines.append("  proxy answered the client: %s" % (status or "<connection closed, no bytes>"))
        record = item["record"]
        if record is None:
            lines.append("  upstream received: NOTHING (the request never reached the upstream)")
            framed = None
            body_ok = None
            length_ok = None
        else:
            lines.extend(render(record))
            framed = record["framing"] in ("content-length", "chunked")
            body_ok = record["body_sha256"] == sha256(item["sent"])
            length_ok = (record["framing"] != "content-length"
                         or record["declared_length"] == record["body_bytes"])
        lines.append("")
        verdicts.append({
            "shape": item["name"],
            "reached_upstream": record is not None,
            "framing": record.get("framing") if record else None,
            "framing_header_present": framed,
            "declared_length_matches_body": length_ok,
            "body_identical_to_client": body_ok,
            "upstream_status": status,
        })

    with open(ledger, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    lines.append("=== ledger rows for this tap run ===")
    for row in rows:
        lines.append("  %s %s ceq=%r unmetered=%r reason=%r"
                     % (row["provider"], row["endpoint"], row["ceq"], row["unmetered"],
                        row["reason"]))
    lines.append("")

    ok = True
    lines.append("=== verdicts ===")
    for verdict in verdicts:
        if verdict["shape"].startswith("C:"):
            # Case C is the illegal shape: the only correct outcomes are "refused locally" or
            # "framed by the proxy". Both leave the tap with a framed request or nothing.
            good = (not verdict["reached_upstream"]) or bool(verdict["framing_header_present"])
            lines.append("  %-4s %s -> reached_upstream=%s framing=%s"
                         % ("PASS" if good else "FAIL", verdict["shape"][:44],
                            verdict["reached_upstream"], verdict["framing"]))
        else:
            good = (verdict["reached_upstream"] and verdict["framing_header_present"]
                    and verdict["declared_length_matches_body"]
                    and verdict["body_identical_to_client"]
                    and verdict["upstream_status"] == "HTTP/1.1 200 OK")
            lines.append("  %-4s %s -> framing=%s header=%s length_matches=%s body_identical=%s "
                         "status=%s"
                         % ("PASS" if good else "FAIL", verdict["shape"][:44], verdict["framing"],
                            verdict["framing_header_present"],
                            verdict["declared_length_matches_body"],
                            verdict["body_identical_to_client"], verdict["upstream_status"]))
        ok = ok and good
    lines.append("")
    lines.append("RESULT: %s" % ("all captured requests correctly framed" if ok
                                 else "AT LEAST ONE REQUEST WAS NOT CORRECTLY FRAMED"))

    text_path = os.path.join(out, "framing_%s.txt" % args.label)
    json_path = os.path.join(out, "framing_%s.json" % args.label)
    with open(text_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump({"label": args.label, "proxy": os.path.abspath(args.proxy),
                   "proxy_sha256": hashlib.sha256(open(args.proxy, "rb").read()).hexdigest(),
                   "verdicts": verdicts, "ok": ok, "ledger_rows": rows}, fh, indent=2)
        fh.write("\n")
    print("\n".join(lines))
    print("\nwrote %s and %s" % (text_path, json_path))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="raw TCP tap for the a0 meter's upstream leg")
    parser.add_argument("--proof", action="store_true",
                        help="run the before/after framing proof through a live proxy")
    parser.add_argument("--proxy", default=os.path.join(HERE, "meter_proxy.py"),
                        help="proxy under test (point it at an older copy to capture 'before')")
    parser.add_argument("--out", default=os.path.join(HERE, "evidence"))
    parser.add_argument("--work", default="/tmp/a0-meter-tap")
    parser.add_argument("--label", default="run")
    parser.add_argument("--plain", action="store_true",
                        help="tap the upstream leg over plaintext HTTP instead of TLS")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--log")
    args = parser.parse_args(argv)

    if args.proof:
        return run_proof(args)

    tap = Tap()
    tap.start()
    print("raw tap listening on 127.0.0.1:%d (plaintext); Ctrl-C to stop" % tap.port)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    tap.stop()
    if args.log:
        with open(args.log, "w", encoding="utf-8") as fh:
            for record in tap.records:
                fh.write(json.dumps({k: v for k, v in record.items() if k != "body"},
                                    default=repr) + "\n")
    for record in tap.records:
        print("\n".join(render(record)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
