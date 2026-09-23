#!/usr/bin/env python3
"""C2's host-side relay: a unix socket in front of the campaign's meter port.

This is ``a0.a1.topology.UnixRelay`` reused, not reimplemented -- the class that
the ``unshare -rn`` arm of the topology already uses is the right component for
the same job here, so it is imported from the repository (the host has it; the
container does not).

Usage: sock_relay.py --sock /tmp/a0ec/run/c2.sock --target 127.0.0.1:8802
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from a0.a1.topology import UnixRelay  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="a0ec-sock-relay")
    parser.add_argument("--sock", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--ready-file", default=None)
    args = parser.parse_args(argv)

    host, _, port = args.target.partition(":")
    relay = UnixRelay(Path(args.sock), (host, int(port)))
    relay.start()
    if args.ready_file:
        Path(args.ready_file).write_text("ready\n", encoding="utf-8")
    sys.stderr.write("sock_relay: %s -> %s\n" % (args.sock, args.target))
    sys.stderr.flush()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        relay.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
