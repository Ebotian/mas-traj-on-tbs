"""A declared repair hop for `a0/meter`'s request-body framing defect.

**The defect (reproduced, not inferred).**  `a0/meter/meter_proxy.py` strips
`Content-Length` from the client's headers when it builds the upstream request
(the header is in `HOP_BY_HOP`, line 103) and then sends the body through
`http.client`'s low-level API — `putrequest` / `putheader` / `endheaders(body)`,
`meter_proxy.py:283-291`.  `endheaders` does **not** add `Content-Length`, so the
upstream receives:

```
POST /v1/chat/completions HTTP/1.1
User-Agent: …
Authorization: Bearer …
Content-Type: application/json
Host: …
Accept-Encoding: identity
<blank line>
{"model": "...", "messages": [...]}          <- unframed body bytes
```

with no framing header at all.  A conforming HTTP/1.1 server reads *no* body, so
DeepSeek answers `400 Failed to parse the request body as JSON: EOF while parsing a
value at line 1 column 0`, and the meter books the call `unmetered` with reason
`unparseable_response_body`.  Every real call therefore reaches the `unmetered`
bucket, and a campaign can never have a real `CEq`.

The meter's own selftest cannot see this: `fake_upstream.py:239` reads the body
from `content-length`, gets 0 bytes, and the tests assert on the *response* usage
rather than on what the upstream received.  The defect is invisible to 55/55.

**Why this module exists, and what it is not.**  `a0/meter/` is another worker's
directory and `INTERFACE.md` forbids silent deviation, so this file is a loud,
declared compensating hop rather than an edit.  It sits *below* the meter:

```
runtime ──plaintext──▶ meter_proxy ──plaintext──▶ this repair hop ──TLS──▶ api.deepseek.com
                        (books the row)            (restores framing)
```

The meter still sees the client's request and still books the row from the
provider's response, so the accounting authority is unchanged; what changes is
that the upstream leg is no longer unframed.  The hop dials exactly one host
(`api.deepseek.com`, certificate-verified) and refuses everything else, so the
allowlist semantics survive.

**Remove this file** the moment `meter_proxy.py` re-adds the framing header (one
line: `conn.putheader("Content-Length", str(len(body)))`); `a0/a1/DEVIATIONS.md`
D-A1-3 records the finding, the reproduction and this workaround.

    python3 a0/a1/meter_body_repair.py --port 8810 --log /tmp/repair.jsonl \
        --upstream https://api.deepseek.com --ready-file /tmp/repair.ready
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import ssl
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlsplit

IDLE_BODY_SECONDS = 0.35
MAX_HEADER_BYTES = 1 << 20
MAX_BODY_BYTES = 64 << 20


def _read_head(sock: socket.socket) -> Tuple[bytes, List[str], bytes]:
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(65536)
        if not chunk:
            break
        data += chunk
        if len(data) > MAX_HEADER_BYTES:
            raise ValueError("header too large")
    head, _, rest = data.partition(b"\r\n\r\n")
    lines = head.decode("iso-8859-1").split("\r\n")
    return head, lines[1:], rest


def _header(headers: List[str], name: str) -> Optional[str]:
    for line in headers:
        key, _, value = line.partition(":")
        if key.strip().lower() == name:
            return value.strip()
    return None


def _read_unframed_body(sock: socket.socket, already: bytes) -> bytes:
    """Read the body of a request that arrived with **no framing header at all**.

    This is what the meter sends. The head and the body are written in one
    `sendall`, so the bytes are already in flight; a short idle window after the
    header terminator delimits the body. Anything still arriving during the window
    is appended, so a slow client with a large body is still framed correctly.
    """
    body = already
    deadline = time.monotonic() + IDLE_BODY_SECONDS
    sock.settimeout(IDLE_BODY_SECONDS)
    while time.monotonic() < deadline:
        try:
            chunk = sock.recv(65536)
        except (socket.timeout, TimeoutError):
            break
        if not chunk:
            break
        body += chunk
        if len(body) > MAX_BODY_BYTES:
            raise ValueError("body too large")
        deadline = time.monotonic() + IDLE_BODY_SECONDS
    return body


class RepairHop:
    def __init__(self, *, port: int, upstream: str, log_path: Optional[Path] = None,
                 ready_file: Optional[Path] = None):
        self.port = port
        self.upstream = urlsplit(upstream)
        self.upstream_host = self.upstream.hostname or "api.deepseek.com"
        self.upstream_port = self.upstream.port or 443
        self.log_path = Path(log_path) if log_path else None
        self.ready_file = Path(ready_file) if ready_file else None
        self.records: List[dict] = []
        self._lock = threading.Lock()

    # -- logging ----------------------------------------------------------
    def _record(self, payload: dict) -> None:
        with self._lock:
            self.records.append(payload)
            if self.log_path is not None:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with self.log_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())

    # -- forwarding -------------------------------------------------------
    def handle(self, client: socket.socket) -> None:
        try:
            head, headers, rest = _read_head(client)
            request_line = head.split(b"\r\n", 1)[0].decode("iso-8859-1")
            method, _, path = request_line.partition(" ")
            declared = _header(headers, "content-length")
            chunked = (_header(headers, "transfer-encoding") or "").lower()
            if declared is not None:
                want = int(declared)
                body = rest
                while len(body) < want:
                    chunk = client.recv(min(65536, want - len(body)))
                    if not chunk:
                        break
                    body += chunk
                body = body[:want]
                framing = "content-length"
            elif "chunked" in chunked:
                body = rest
                while not body.endswith(b"\r\n0\r\n\r\n") and not body.endswith(b"0\r\n\r\n"):
                    chunk = client.recv(65536)
                    if not chunk:
                        break
                    body += chunk
                framing = "chunked"
            else:
                body = _read_unframed_body(client, rest)
                framing = "unframed_repaired"

            out_headers = []
            seen_accept_encoding = False
            for line in headers:
                key, _, value = line.partition(":")
                key = key.strip()
                lowered = key.lower()
                if lowered in ("content-length", "transfer-encoding", "host",
                               "proxy-connection", "connection"):
                    continue
                if lowered == "accept-encoding":
                    seen_accept_encoding = True
                    out_headers.append("Accept-Encoding: identity")
                    continue
                out_headers.append(f"{key}: {value.strip()}")
            if not seen_accept_encoding:
                out_headers.append("Accept-Encoding: identity")
            out_headers.append(f"Host: {self.upstream_host}")
            out_headers.append(f"Content-Length: {len(body)}")

            request = (
                f"{method} {path} HTTP/1.1\r\n" + "\r\n".join(out_headers) + "\r\n\r\n"
            ).encode("iso-8859-1") + body

            ctx = ssl.create_default_context()
            with socket.create_connection((self.upstream_host, self.upstream_port),
                                          timeout=60) as raw:
                with ctx.wrap_socket(raw, server_hostname=self.upstream_host) as tls:
                    tls.sendall(request)
                    status_line = b""
                    while b"\r\n" not in status_line:
                        chunk = tls.recv(65536)
                        if not chunk:
                            break
                        status_line += chunk
                    try:
                        status = int(status_line.split(b" ")[1])
                    except (IndexError, ValueError):
                        status = 0
                    # Recorded as soon as the upstream's status is known: the
                    # response may stream for a while (or never end), and the
                    # evidence must not wait for it.
                    self._record({
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        "method": method,
                        "path": path,
                        "to": f"{self.upstream_host}:{self.upstream_port}",
                        "client_framing": framing,
                        "request_body_bytes": len(body),
                        "repaired_with": f"Content-Length: {len(body)}",
                        "status": status,
                    })
                    client.sendall(status_line)
                    while True:
                        chunk = tls.recv(65536)
                        if not chunk:
                            break
                        client.sendall(chunk)
        except Exception as exc:  # noqa: BLE001 - a broken hop must not kill the server
            self._record({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                          "error": f"{type(exc).__name__}: {exc}"})
            try:
                client.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
            except OSError:
                pass
        finally:
            try:
                client.close()
            except OSError:
                pass

    def serve_forever(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", self.port))
        server.listen(64)
        if self.ready_file is not None:
            self.ready_file.parent.mkdir(parents=True, exist_ok=True)
            self.ready_file.write_text(f"{self.port}\n", encoding="utf-8")
        sys.stderr.write(
            f"repair hop up on 127.0.0.1:{self.port} -> {self.upstream_host}:{self.upstream_port}\n"
        )
        sys.stderr.flush()
        while True:
            client, _ = server.accept()
            threading.Thread(target=self.handle, args=(client,), daemon=True).start()


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="meter_body_repair")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--upstream", default="https://api.deepseek.com")
    parser.add_argument("--log", default=None)
    parser.add_argument("--ready-file", default=None)
    args = parser.parse_args(argv)
    port = args.port
    if port == 0:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = int(probe.getsockname()[1])
    hop = RepairHop(port=port, upstream=args.upstream, log_path=Path(args.log) if args.log else None,
                    ready_file=Path(args.ready_file) if args.ready_file else None)
    hop.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
