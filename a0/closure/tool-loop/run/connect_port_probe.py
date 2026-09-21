#!/usr/bin/env python3
"""CONNECT allowlist port-scope probe: does the allowlist pin host:port, or host?

Runs INSIDE a0tl-cli (the closed-network worker) and speaks raw HTTP to the
proxy, because the Python HTTP clients do not let us put an arbitrary port in a
CONNECT target. Model-free: it makes no completion request and needs no
credential -- the "allowed endpoint works" control is the upstream's own
401 from `GET /v1/models`, which is the same signal the lane evidence uses.

Checks, per run:

  C1  CONNECT api.deepseek.com:443   -- control: the intended allowed endpoint
  C2  CONNECT api.deepseek.com:25    -- the port-scope question
  C3  CONNECT api.deepseek.com:22    -- same, a port with no listener behind it
  C4  CONNECT api.deepseek.com:80
  C5  CONNECT api.deepseek.com:8443
  C6  CONNECT api.deepseek.com       -- no port given: what default applies?
  C7  CONNECT example.com:443        -- control: a host that is not allowlisted
  C8  origin-form GET /v1/models      -- control: the plaintext route reaches upstream (401)
  C9  origin-form GET /v1/responses   -- the variant's route (401 from upstream)
  C10 origin-form GET /nope           -- control: no route -> 403 no_route

When a target gets 200, the tunnel is byte-transparent up to the point the
probe stops: it reports whether a TLS handshake into that port succeeds and
what certificate comes back, which is what distinguishes "a raw TCP channel to
an arbitrary port on the allowed host" from "the same TLS endpoint on another
port".

    python3 connect_port_probe.py --out /work/wd/connect_port_probe.json
"""

from __future__ import annotations

import argparse
import json
import socket
import ssl
import time
from pathlib import Path

PROXY_HOST = "a0tl-proxy"
PROXY_PORT = 8787
ALLOWED_HOST = "api.deepseek.com"
BLOCKED_HOST = "example.com"
TIMEOUT = 6.0

CONNECT_TARGETS = (
    ("c1_allow_443", f"{ALLOWED_HOST}:443"),
    ("c2_port_25", f"{ALLOWED_HOST}:25"),
    ("c3_port_22", f"{ALLOWED_HOST}:22"),
    ("c4_port_80", f"{ALLOWED_HOST}:80"),
    ("c5_port_8443", f"{ALLOWED_HOST}:8443"),
    ("c6_no_port", ALLOWED_HOST),
    ("c7_blocked_host_443", f"{BLOCKED_HOST}:443"),
)


def proxy_sock() -> socket.socket:
    s = socket.socket()
    s.settimeout(TIMEOUT)
    s.connect((PROXY_HOST, PROXY_PORT))
    return s


def connect_probe(target: str) -> dict:
    """Send CONNECT <target> and report the proxy's status line + headers."""
    started = time.monotonic()
    try:
        s = proxy_sock()
    except OSError as exc:
        return {"target": target, "status_line": None,
                "error": f"{type(exc).__name__}: {exc}"}
    try:
        s.sendall(f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n".encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = s.recv(4096)
            if not chunk:
                break
            head += chunk
            if len(head) > 65536:
                break
        text = head.decode("iso-8859-1", "replace")
        block, _, _ = text.partition("\r\n\r\n")
        lines = block.splitlines()
        return {"target": target,
                "status_line": lines[0] if lines else "<no response>",
                "headers": lines[1:],
                "sec": round(time.monotonic() - started, 3)}
    except OSError as exc:
        return {"target": target, "status_line": None,
                "error": f"{type(exc).__name__}: {exc}",
                "sec": round(time.monotonic() - started, 3)}
    finally:
        s.close()


def tls_through_connect(target: str, servername: str) -> dict:
    """If CONNECT <target> is established, try a TLS handshake into the tunnel.

    A tunnel that returns 200 is a raw byte pipe; this says whether the port
    behind it (a) completes a TLS handshake and presents which certificate, so
    the reader can judge whether the port scope matters for reachability or only
    for documentation.
    """
    out: dict = {"target": target, "servername": servername}
    try:
        s = proxy_sock()
    except OSError as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out
    try:
        s.sendall(f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n".encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = s.recv(4096)
            if not chunk:
                break
            head += chunk
        first = head.decode("iso-8859-1", "replace").splitlines()
        out["status_line"] = first[0] if first else "<no response>"
        if "200" not in out["status_line"]:
            return out
        ctx = ssl.create_default_context()
        try:
            tls = ctx.wrap_socket(s, server_hostname=servername)
        except Exception as exc:  # noqa: BLE001 - a refusal here is the result
            out["tls_handshake"] = f"failed: {type(exc).__name__}: {exc}"
            return out
        cert = tls.getpeercert() or {}
        out["tls_handshake"] = "ok"
        out["tls_version"] = tls.version()
        out["peer_subject"] = cert.get("subject")
        out["peer_subjectAltName"] = cert.get("subjectAltName")
        tls.close()
        return out
    except OSError as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out
    finally:
        try:
            s.close()
        except OSError:
            pass


def raw_through_connect(target: str, payload: bytes, read_bytes: int = 400) -> dict:
    """Establish CONNECT <target> and send raw bytes down the tunnel.

    The tunnel is byte-transparent; this reports what, if anything, answers on
    the port so the port scope can be judged against a measurement instead of an
    assumption about what lives on the allowed host's other ports.
    """
    out: dict = {"target": target, "payload_head": payload[:40].decode("iso-8859-1", "replace")}
    try:
        s = proxy_sock()
    except OSError as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out
    try:
        s.sendall(f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n".encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = s.recv(4096)
            if not chunk:
                break
            head += chunk
        first = head.decode("iso-8859-1", "replace").splitlines()
        out["status_line"] = first[0] if first else "<no response>"
        if "200" not in out["status_line"]:
            return out
        s.sendall(payload)
        try:
            data = s.recv(read_bytes)
        except OSError as exc:
            out["reply"] = f"<{type(exc).__name__}: {exc}>"
            return out
        out["reply_head"] = data.decode("iso-8859-1", "replace")[:200] if data else "<eof, no bytes>"
        return out
    except OSError as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out
    finally:
        try:
            s.close()
        except OSError:
            pass


def http_raw(request: str) -> dict:
    try:
        s = proxy_sock()
    except OSError as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    try:
        s.sendall(request.encode())
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
            if len(data) > 65536:
                break
        text = data.decode("iso-8859-1", "replace")
        head, _, body = text.partition("\r\n\r\n")
        lines = head.splitlines()
        return {"status_line": lines[0] if lines else "<no response>",
                "headers": lines[1:], "body_head": body.strip()[:120]}
    except OSError as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    finally:
        s.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="/work/wd/connect_port_probe.json")
    args = ap.parse_args()

    result: dict = {
        "schema": "a0.ttoolloop.connect_port_probe/v1",
        "when": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "container_hostname": socket.gethostname(),
        "proxy": f"{PROXY_HOST}:{PROXY_PORT}",
        "connect": {},
        "tls_through_connect": [],
        "plaintext_routes": {},
    }

    for name, target in CONNECT_TARGETS:
        result["connect"][name] = connect_probe(target)

    for label, target in (("c1_allow_443", f"{ALLOWED_HOST}:443"),
                          ("c2_port_25", f"{ALLOWED_HOST}:25")):
        result["tls_through_connect"].append(tls_through_connect(target, ALLOWED_HOST))

    result["raw_through_connect"] = [
        raw_through_connect(f"{ALLOWED_HOST}:80",
                            b"GET / HTTP/1.1\r\nHost: " + ALLOWED_HOST.encode()
                            + b"\r\nConnection: close\r\n\r\n"),
    ]

    result["plaintext_routes"] = {
        "c8_get_v1_models": http_raw(
            "GET /v1/models HTTP/1.1\r\nHost: " + ALLOWED_HOST + "\r\nConnection: close\r\n\r\n"),
        "c9_get_v1_responses": http_raw(
            "GET /v1/responses HTTP/1.1\r\nHost: " + ALLOWED_HOST + "\r\nConnection: close\r\n\r\n"),
        "c10_get_nope": http_raw(
            "GET /nope HTTP/1.1\r\nHost: " + ALLOWED_HOST + "\r\nConnection: close\r\n\r\n"),
    }

    text = json.dumps(result, indent=1, sort_keys=True)
    Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
