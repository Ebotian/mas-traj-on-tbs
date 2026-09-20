#!/usr/bin/env python3
"""Egress canary for one runtime's candidate-execution channel.

This is the payload the closure probes run *inside* the channel they are
testing (host shell, codex CLI sandbox, `unshare -rn`, container). It must run
on a bare interpreter with no third-party imports, because the same text has to
work on the host and inside an alpine container.

It deliberately uses three independent methods, because "curl is missing" and
"DNS is not configured" must not be reported as "network is blocked":

  dns   name resolution of the sentinel host
  tcp   raw TCP connect to the sentinel, by name and by IP literal
  https an HTTP GET that also exercises TLS

and one local action, so that a channel which is merely broken (no network
stack at all) is distinguishable from a channel that is sandboxed:

  local writes a file into the cwd and reads it back

One line of output, machine-parseable:

  LANE_PROBE dns=ok tcp=ok tcpvia=example.com:443 https=ok local=ok egress=OPEN

`egress=OPEN` iff tcp or https succeeded. Exit status is always 0: the caller
classifies from the line, so a missing interpreter or a refused connection
cannot masquerade as a probe crash.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import urllib.request

SENTINEL_HOST = os.environ.get("LANE_PROBE_HOST", "example.com")
SENTINEL_URL = os.environ.get("LANE_PROBE_URL", "https://example.com/")
TCP_CANDIDATES = [
    f"{SENTINEL_HOST}:443",
    "1.1.1.1:443",
    "8.8.8.8:443",
    "1.1.1.1:80",
    "8.8.8.8:53",
]
TIMEOUT = float(os.environ.get("LANE_PROBE_TIMEOUT", "8"))


def probe_dns() -> str:
    try:
        socket.gethostbyname(SENTINEL_HOST)
        return "ok"
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        return f"fail:{type(exc).__name__}"


def probe_tcp() -> tuple[str, str]:
    for target in TCP_CANDIDATES:
        host, _, port = target.rpartition(":")
        try:
            sock = socket.create_connection((host, int(port)), timeout=TIMEOUT)
            sock.close()
            return "ok", target
        except Exception:  # noqa: BLE001 - try the next target
            continue
    return "fail", "none"


def probe_https() -> str:
    try:
        urllib.request.urlopen(SENTINEL_URL, timeout=TIMEOUT)  # noqa: S310
        return "ok"
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        return f"fail:{type(exc).__name__}"


def probe_local() -> str:
    """A non-network action: the channel must still be able to do real work."""
    path = os.path.join(os.getcwd(), ".lane_probe_local")
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("lane-probe\n")
        with open(path, encoding="utf-8") as handle:
            handle.read()
        os.unlink(path)
        return "ok"
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        return f"fail:{type(exc).__name__}"


def main() -> int:
    dns = probe_dns()
    tcp, tcpvia = probe_tcp()
    https = probe_https()
    local = probe_local()
    egress = "OPEN" if (tcp == "ok" or https == "ok") else "BLOCKED"

    if "--json" in sys.argv:
        sys.stdout.write(
            json.dumps(
                {
                    "schema": "a0.closureprobe.canary/v1",
                    "sentinel_host": SENTINEL_HOST,
                    "sentinel_url": SENTINEL_URL,
                    "dns": dns,
                    "tcp": tcp,
                    "tcpvia": tcpvia,
                    "https": https,
                    "local": local,
                    "egress": egress,
                }
            )
            + "\n"
        )
    else:
        sys.stdout.write(
            f"LANE_PROBE dns={dns} tcp={tcp} tcpvia={tcpvia} "
            f"https={https} local={local} egress={egress}\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
