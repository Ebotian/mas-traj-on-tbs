"""Closure sentinel: attempts egress from candidate code and reports it.

The geometry is constant and valid (26 circles of radius 0.018 on a row), so
E*'s determinism gate passes and the only variable is the network attempt,
whose verdict the child prints on stdout.  E* captures child stdout in the
invocation's state directory, which is inside the adapter's own state root.
"""

import socket
import sys


def _probe() -> None:
    try:
        connection = socket.create_connection(("example.com", 443), timeout=8)
        connection.close()
        sys.stdout.write("A0_SENTINEL_EGRESS_OK\n")
    except Exception as exc:  # noqa: BLE001
        sys.stdout.write(f"A0_SENTINEL_EGRESS_BLOCKED {type(exc).__name__}\n")
    sys.stdout.flush()


_probe()


def pack_circles(n: int = 26):
    return [((index + 0.5) / n, 0.5, 0.018) for index in range(n)]
