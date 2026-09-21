#!/usr/bin/env python3
"""Allowlist egress proxy for the a0 rootless-closure topology.

Listens on one plaintext port inside a docker `--internal` network and is the
only dual-homed peer there, so it is the single egress point for clients.

Two request shapes are served on the same listener:

  * forward-proxy CONNECT (what HTTPS_PROXY= produces):
        CONNECT api.deepseek.com:443 HTTP/1.1
    The destination is matched against ALLOW_CONNECT on **host and port**, so
    the rule pins the intended endpoint rather than every port the host happens
    to listen on (`CONNECT api.deepseek.com:25` is refused). On a match the TLS
    stream is tunnelled end to end -- no MITM, no certificate injection, the
    client validates the real upstream certificate.

  * plaintext "base_url" routing (what ANTHROPIC_BASE_URL=http://proxy:8787/
    or an OpenAI-compatible baseURL produces): the client sends an origin-form
    request over cleartext HTTP to the proxy, and the path selects the upstream
    API shape. This is how one listener serves both Anthropic Messages and
    OpenAI Chat Completions without the client knowing either upstream URL.

Everything else is refused with 403 and logged. Stdlib only.

VARIANT (a0/closure/tool-loop): differs from the proxy-closure original by one
route, `/v1/responses` -> api.deepseek.com, which the codex lane speaks, and by
matching CONNECT on host *and* port (the original matches the host only). See
`CHANGES.md` for both hunks and for the measurement that motivated the second.

Env: PROXY_PORT (default 8787), PROXY_ALLOW (comma-separated CONNECT
destinations, `host` or `host:port`; a bare host means port 443).
"""

import os
import socket
import ssl
import sys
import threading
import time

PORT = int(os.environ.get("PROXY_PORT", "8787"))

# Destination port assumed when PROXY_ALLOW (or a CONNECT target) names a host
# with no port: the TLS port this listener exists to carry.
CONNECT_DEFAULT_PORT = 443


def parse_allow_connect(raw):
    """PROXY_ALLOW entries (`host` or `host:port`) -> a set of (host, port).

    A bare host means CONNECT_DEFAULT_PORT, so `PROXY_ALLOW=api.deepseek.com`
    keeps meaning exactly `api.deepseek.com:443` instead of widening to every
    port on that host.
    """
    allow = set()
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        host, sep, port = entry.rpartition(":")
        if sep and port.isdigit():
            allow.add((host, int(port)))
        else:
            allow.add((entry, CONNECT_DEFAULT_PORT))
    return frozenset(allow)


def parse_connect_target(target):
    """`host:port` -> (host, port); a bare host means CONNECT_DEFAULT_PORT.

    Returns (None, None) when the target names a non-numeric port, which is
    refused like any other non-allowlisted destination rather than raising.
    """
    host, sep, port = target.rpartition(":")
    if not sep:
        return target, CONNECT_DEFAULT_PORT
    if port.isdigit():
        return host, int(port)
    return None, None


# Destinations reachable through CONNECT: (host, port) pairs. Everything else
# is denied.
ALLOW_CONNECT = parse_allow_connect(
    os.environ.get("PROXY_ALLOW", "api.deepseek.com,openrouter.ai"))

# Origin-form request routing, longest prefix wins.
#   (path prefix, upstream host, upstream path prefix)
ROUTES = (
    ("/v1/messages", "api.deepseek.com", "/anthropic"),
    ("/v1/models", "api.deepseek.com", ""),
    ("/v1/chat/completions", "api.deepseek.com", ""),
    # codex 0.155.1 speaks the Responses wire and appends /v1/responses to
    # `base_url`; without this route the codex lane gets 403 reason=no_route.
    ("/v1/responses", "api.deepseek.com", ""),
)

LOCK = threading.Lock()
STATS = {"req": 0, "allow": 0, "deny": 0, "bytes_out": 0, "bytes_in": 0}


def log(msg):
    sys.stdout.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), msg))
    sys.stdout.flush()


def bump(field, n=1):
    with LOCK:
        STATS[field] += n


def read_head(sock):
    """Read bytes up to and including the CRLFCRLF that ends a header block."""
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            return buf if buf else None
        buf += chunk
        if len(buf) > 1 << 20:
            raise ValueError("header block too large")
    return buf


def split_head(raw):
    text = raw.decode("iso-8859-1")
    head, _, rest = text.partition("\r\n\r\n")
    lines = head.split("\r\n")
    return lines[0], lines[1:], rest.encode("iso-8859-1")


def header_get(headers, name):
    for h in headers:
        k, _, v = h.partition(":")
        if k.strip().lower() == name:
            return v.strip()
    return None


def read_body(sock, headers, already):
    """Return the full request body, honouring Content-Length / chunked."""
    body = already
    te = (header_get(headers, "transfer-encoding") or "").lower()
    cl = header_get(headers, "content-length")
    if "chunked" in te:
        while b"\r\n0\r\n\r\n" not in body and not body.endswith(b"0\r\n\r\n"):
            chunk = sock.recv(65536)
            if not chunk:
                break
            body += chunk
        return body
    if cl is not None:
        want = int(cl)
        while len(body) < want:
            chunk = sock.recv(min(65536, want - len(body)))
            if not chunk:
                break
            body += chunk
        return body
    return body


def pump(src, dst, counter):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
            if counter:
                bump(counter, len(data))
    except OSError:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def tls_connect(host, port=443, timeout=30):
    ctx = ssl.create_default_context()
    raw = socket.create_connection((host, port), timeout=timeout)
    return ctx.wrap_socket(raw, server_hostname=host)


def send_simple(conn, code, reason, body=b"", extra_headers=()):
    head = "HTTP/1.1 %d %s\r\n" % (code, reason)
    for k, v in extra_headers:
        head += "%s: %s\r\n" % (k, v)
    head += "Content-Length: %d\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n" % len(body)
    conn.sendall(head.encode() + body)


def handle_connect(conn, target, peer):
    host, port = parse_connect_target(target)
    if host is None or (host, port) not in ALLOW_CONNECT:
        bump("deny")
        log("event=connect peer=%s target=%s decision=DENY" % (peer, target))
        send_simple(conn, 403, "Forbidden",
                    b"a0pc-proxy: destination not on allowlist\n")
        return
    bump("allow")
    try:
        upstream = socket.create_connection((host, port), timeout=30)
    except OSError as exc:
        log("event=connect peer=%s target=%s decision=ALLOW uplink=fail err=%s"
            % (peer, target, exc))
        send_simple(conn, 502, "Bad Gateway",
                    b"a0pc-proxy: upstream unreachable\n")
        return
    conn.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
    log("event=connect peer=%s target=%s decision=ALLOW tunnel=open"
        % (peer, target))
    # Both sockets are owned by the tunnel until it closes; serve_client must
    # not close them underneath us, so the relay is driven synchronously here.
    conn.settimeout(None)
    upstream.settimeout(None)
    back = threading.Thread(target=pump, args=(conn, upstream, None), daemon=True)
    back.start()
    pump(upstream, conn, None)
    back.join(timeout=5)
    try:
        upstream.close()
    except OSError:
        pass
    log("event=connect peer=%s target=%s tunnel=closed" % (peer, target))


def route(path):
    for prefix, host, up_prefix in ROUTES:
        if path.startswith(prefix):
            return host, up_prefix + path
    return None, None


def handle_http(conn, request_line, headers, rest, peer):
    parts = request_line.split()
    if len(parts) != 3:
        send_simple(conn, 400, "Bad Request", b"a0pc-proxy: malformed request line\n")
        return
    method, target, _version = parts
    if target.startswith("http://") or target.startswith("https://"):
        path = "/" + target.split("/", 3)[3] if target.count("/") >= 3 else "/"
    else:
        path = target

    host, up_path = route(path)
    if host is None:
        bump("deny")
        log("event=deny proto=http peer=%s method=%s path=%s reason=no_route"
            % (peer, method, path))
        send_simple(conn, 403, "Forbidden",
                    b"a0pc-proxy: path not on allowlist\n")
        return

    try:
        body = read_body(conn, headers, rest)
    except (OSError, ValueError) as exc:
        log("event=error peer=%s path=%s stage=body err=%s" % (peer, path, exc))
        return

    out_head = "%s %s HTTP/1.1\r\n" % (method, up_path)
    for h in headers:
        name = h.partition(":")[0].strip().lower()
        if name in ("host", "connection", "proxy-connection", "keep-alive",
                    "upgrade", "te"):
            continue
        out_head += h + "\r\n"
    out_head += "Host: %s\r\nConnection: close\r\n\r\n" % host

    bump("req")
    try:
        up = tls_connect(host)
    except OSError as exc:
        log("event=error peer=%s upstream=%s stage=connect err=%s" % (peer, host, exc))
        send_simple(conn, 502, "Bad Gateway", b"a0pc-proxy: upstream unreachable\n")
        return

    try:
        up.sendall(out_head.encode("iso-8859-1") + body)
        bump("bytes_out", len(body))
        raw = read_head(up)
        if raw is None:
            log("event=error peer=%s upstream=%s stage=response err=empty" % (peer, host))
            return
        status_line, up_headers, up_rest = split_head(raw)
        te = (header_get(up_headers, "transfer-encoding") or "").lower()
        cl = header_get(up_headers, "content-length")

        resp = status_line + "\r\n"
        for h in up_headers:
            name = h.partition(":")[0].strip().lower()
            if name in ("connection", "keep-alive", "proxy-connection"):
                continue
            # a body framed by Transfer-Encoding must not also carry length
            if name == "content-length" and "chunked" in te:
                continue
            resp += h + "\r\n"
        resp += "Connection: close\r\n\r\n"
        conn.sendall(resp.encode("iso-8859-1"))

        sent = len(up_rest)
        conn.sendall(up_rest)
        if "chunked" in te:
            buf = up_rest
            while b"0\r\n\r\n" not in buf[-8:] and not buf.endswith(b"0\r\n\r\n"):
                data = up.recv(65536)
                if not data:
                    break
                conn.sendall(data)
                sent += len(data)
                buf = data
        elif cl is not None:
            want = int(cl) - sent
            while want > 0:
                data = up.recv(min(65536, want))
                if not data:
                    break
                conn.sendall(data)
                want -= len(data)
                sent += len(data)
        else:
            while True:
                data = up.recv(65536)
                if not data:
                    break
                conn.sendall(data)
                sent += len(data)
        bump("bytes_in", sent)
        log("event=req peer=%s method=%s path=%s upstream=https://%s%s status=%s "
            "resp_bytes=%d" % (peer, method, path, host, up_path,
                               status_line.split()[1], sent))
    except OSError as exc:
        log("event=error peer=%s upstream=%s stage=relay err=%s" % (peer, host, exc))
    finally:
        try:
            up.close()
        except OSError:
            pass


def serve_client(conn, addr):
    peer = "%s:%d" % addr
    try:
        conn.settimeout(300)
        raw = read_head(conn)
        if raw is None:
            return
        request_line, headers, rest = split_head(raw)
        parts = request_line.split()
        if parts and parts[0].upper() == "CONNECT":
            handle_connect(conn, parts[1], peer)
            # the two pump threads own the socket from here
            time.sleep(0)
        else:
            handle_http(conn, request_line, headers, rest, peer)
    except (OSError, ValueError) as exc:
        log("event=error peer=%s stage=accept err=%s" % (peer, exc))
    finally:
        try:
            conn.close()
        except OSError:
            pass


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(64)
    log("event=start port=%d allow_connect=%s routes=%s"
        % (PORT, sorted(ALLOW_CONNECT), [r[0] for r in ROUTES]))
    while True:
        try:
            conn, addr = srv.accept()
        except OSError:
            continue
        threading.Thread(target=serve_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
