"""Minimal HTTP CONNECT (tunnelling) proxy.

Purpose: prove whether opencode honours HTTPS_PROXY / HTTP_PROXY.  Every
CONNECT target is logged, then the tunnel is relayed verbatim so the upstream
TLS session still works.  No request bodies or headers are logged.
"""
import json
import select
import socket
import sys
import threading

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8098
LOG = sys.argv[2] if len(sys.argv) > 2 else "/dev/stdout"


def record(payload):
    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def relay(client, upstream):
    sockets = [client, upstream]
    while True:
        readable, _, _ = select.select(sockets, [], [], 60)
        if not readable:
            return
        for source in readable:
            target = upstream if source is client else client
            try:
                chunk = source.recv(65536)
            except OSError:
                return
            if not chunk:
                return
            try:
                target.sendall(chunk)
            except OSError:
                return


def handle(client):
    try:
        client.settimeout(60)
        buffer = b""
        while b"\r\n\r\n" not in buffer:
            chunk = client.recv(4096)
            if not chunk:
                return
            buffer += chunk
        head = buffer.split(b"\r\n\r\n", 1)[0].decode("latin-1")
        parts = head.split("\r\n")[0].split()
        if len(parts) < 2 or parts[0].upper() != "CONNECT":
            record({"proxy": "non-connect", "line": head.split("\r\n")[0]})
            client.sendall(b"HTTP/1.1 405 Method Not Allowed\r\nContent-Length: 0\r\n\r\n")
            return
        target = parts[1]
        host, _, port = target.partition(":")
        record({"proxy": "connect", "target": target})
        upstream = socket.create_connection((host, int(port or 443)), timeout=30)
        client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        relay(client, upstream)
    except Exception as error:  # noqa: BLE001 - diagnostic proxy
        record({"proxy": "error", "error": type(error).__name__})
    finally:
        try:
            client.close()
        except OSError:
            pass


if __name__ == "__main__":
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", PORT))
    listener.listen(64)
    record({"proxy": "listening", "port": PORT})
    while True:
        connection, _ = listener.accept()
        threading.Thread(target=handle, args=(connection,), daemon=True).start()
