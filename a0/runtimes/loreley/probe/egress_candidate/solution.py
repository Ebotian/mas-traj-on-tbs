"""Egress probe candidate for the A0 closure check.

This is NOT a member of ``C*`` and is never used for A0.1 or A0.2.  It exists only
to make the *candidate-execution channel* itself attempt egress, so that the claim
"the runtime has no autonomous external acquisition" is measured rather than
configured (protocol ``plan:569``; ``ACCEPTANCE.md`` T7).

E* runs this through the same path as any candidate: copy below the state root,
import, call ``pack_circles(26)``.  Whatever the network context allows (or
refuses) is written verbatim to ``A0_EGRESS_RESULT`` for the adapter to read back.
"""

from __future__ import annotations

import json
import os
import socket
import urllib.request

_ENV_RESULT = os.environ.get("A0_EGRESS_RESULT", "")
# E* deliberately strips the child environment and runs the candidate from a
# private copy (EID* Config.environment_policy: child_env_specified_by_evaluator),
# so the probe cannot rely on an inherited variable and writes to fixed mount
# points as well.
_RESULT_PATHS = tuple(
    path for path in (_ENV_RESULT, "/probe-egress/result.json", "/tmp/a0-egress-result.json")
    if path
)
_ATTEMPTED = {"done": False}


def _attempt(target_host: str, target_port: int, timeout: float = 6.0) -> str:
    try:
        socket.create_connection((target_host, target_port), timeout=timeout).close()
        return "ok"
    except Exception as exc:  # noqa: BLE001 - the failure mode is the measurement
        return f"fail:{type(exc).__name__}:{str(exc)[:80]}"


def _probe() -> dict:
    result: dict[str, object] = {}
    try:
        socket.gethostbyname("example.com")
        result["dns_example_com"] = "ok"
    except Exception as exc:  # noqa: BLE001
        result["dns_example_com"] = f"fail:{type(exc).__name__}"
    result["tcp_example_com_443"] = _attempt("example.com", 443)
    result["tcp_1_1_1_1_53"] = _attempt("1.1.1.1", 53)
    try:
        urllib.request.urlopen("https://example.com", timeout=8)
        result["https_example_com"] = "ok"
    except Exception as exc:  # noqa: BLE001
        result["https_example_com"] = f"fail:{type(exc).__name__}"
    for label, host, port in (
        ("host_loopback_127_0_0_1_5432", "127.0.0.1", 5432),
        ("host_gateway_172_17_0_1_5432", "172.17.0.1", 5432),
        ("sibling_postgres_5432", "a0-loreley-postgres", 5432),
        ("sibling_redis_6379", "a0-loreley-redis", 6379),
    ):
        try:
            socket.create_connection((host, port), timeout=4).close()
            result[label] = "ok"
        except Exception as exc:  # noqa: BLE001
            result[label] = f"fail:{type(exc).__name__}"
    return result


def pack_circles(n: int = 26):
    if not _ATTEMPTED["done"]:
        _ATTEMPTED["done"] = True
        result = _probe()
        for path in _RESULT_PATHS:
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(result, handle, indent=1, sort_keys=True)
            except Exception:  # noqa: BLE001 - never break the evaluation
                pass
    # A trivially valid packing: tiny, well-separated circles.
    return [(0.02 + 0.02 * (index % 13), 0.02 + 0.02 * (index // 13), 0.004) for index in range(n)]
