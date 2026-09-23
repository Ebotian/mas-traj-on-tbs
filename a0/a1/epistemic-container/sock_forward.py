#!/usr/bin/env python3
"""C2's in-container forwarder: TCP 127.0.0.1:PORT -> a bind-mounted unix socket.

Deliberately standalone (stdlib only).  The container it runs in has no network
namespace uplink and must not contain the repository, so it cannot import
``a0.a1.topology``; this is that module's ``forwarder_main`` reduced to what this
variant needs.  It is a byte pump and nothing else -- it cannot meter, and the
metering proxy on the far side is the only thing that can let a request out.
"""

from __future__ import annotations

import argparse
import socket
import sys
import threading
from pathlib import Path


def splice(left: socket.socket, right: socket.socket) -> None:
    try:
        while True:
            data = left.recv(65536)
            if not data:
                break
            right.sendall(data)
    except OSError:
        pass
    finally:
        for sock in (left, right):
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="a0ec-sock-forward")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--sock", required=True)
    parser.add_argument("--ready-file", default=None)
    args = parser.parse_args(argv)

    if not Path(args.sock).exists():
        sys.stderr.write("sock_forward: %s does not exist\n" % args.sock)
        return 2

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", args.port))
    server.listen(64)
    if args.ready_file:
        Path(args.ready_file).write_text("ready\n", encoding="utf-8")
    sys.stderr.write("sock_forward: 127.0.0.1:%d -> %s\n" % (args.port, args.sock))
    sys.stderr.flush()

    while True:
        try:
            client, _ = server.accept()
        except OSError:
            return 0
        try:
            upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            upstream.connect(args.sock)
        except OSError:
            client.close()
            continue
        threading.Thread(target=splice, args=(client, upstream), daemon=True).start()
        threading.Thread(target=splice, args=(upstream, client), daemon=True).start()


if __name__ == "__main__":
    sys.exit(main())
