#!/usr/bin/env python3
"""Capture-only Anthropic-compatible mock. Logs the auth headers Claude Code actually sends.

Never logs header *values* (only presence + a short non-reversible fingerprint), so the key
cannot leak into the evidence log. Answers with a minimal Messages payload so the CLI exits
quickly without retrying a network error.

Usage: python3 mock_anthropic.py <port> <logfile> [fullbody]
"""
import hashlib
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
LOG = sys.argv[2]
FULL = sys.argv[3] if len(sys.argv) > 3 else None
INTERESTING = ("authorization", "x-api-key", "anthropic-version", "anthropic-beta",
               "content-type", "accept", "user-agent")

count = 0


def fp(v: str) -> str:
    """Fingerprint: length + sha256 prefix. Lets us prove which variable was used
    without reproducing the secret."""
    return f"len={len(v)} sha256[:8]={hashlib.sha256(v.encode()).hexdigest()[:8]}"


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _capture(self, body: bytes):
        global count
        count += 1
        with open(FULL, "a") as fh:
            fh.write(body.decode("utf-8", "replace"))
            fh.write("\n---REQ---\n")
        with open(LOG, "a") as fh:
            fh.write(f"\n=== request #{count}: {self.command} {self.path}\n")
            for k, v in self.headers.items():
                lk = k.lower()
                if lk in ("authorization", "x-api-key"):
                    fh.write(f"HEADER {lk}: <present> {fp(v)}\n")
                elif lk in INTERESTING:
                    fh.write(f"HEADER {lk}: {v}\n")
            if body:
                try:
                    doc = json.loads(body)
                    fh.write("BODY keys: " + ",".join(sorted(doc.keys())) + "\n")
                    fh.write(f"BODY stream={doc.get('stream')} model={doc.get('model')} "
                             f"max_tokens={doc.get('max_tokens')} "
                             f"n_tools={len(doc.get('tools') or [])} "
                             f"n_messages={len(doc.get('messages') or [])}\n")
                    sysp = doc.get("system")
                    if isinstance(sysp, list):
                        sysp = "".join(b.get("text", "") for b in sysp if isinstance(b, dict))
                    fh.write(f"BODY system_chars={len(sysp or '')}\n")
                    for m in (doc.get("messages") or []):
                        c = m.get("content")
                        if isinstance(c, list):
                            kinds = [b.get("type") for b in c if isinstance(b, dict)]
                        else:
                            kinds = ["text"]
                        fh.write(f"BODY msg role={m.get('role')} blocks={kinds}\n")
                except Exception as e:  # noqa: BLE001
                    fh.write(f"BODY unparsed ({e}): {body[:200]!r}\n")
            fh.flush()

    def _reply(self):
        payload = json.dumps({
            "id": "msg_mock_0001",
            "type": "message",
            "role": "assistant",
            "model": "mock-capture",
            "content": [{"type": "text", "text": "MOCK_OK"}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 3, "output_tokens": 2},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else b""
        self._capture(body)
        self._reply()

    def do_GET(self):
        self._capture(b"")
        self._reply()


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
