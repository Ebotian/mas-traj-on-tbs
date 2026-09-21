#!/usr/bin/env bash
# =============================================================================
# control_open.sh -- POSITIVE control for the in-lane probe.
#
# The same probe, same image, same proxy, but on the default `bridge` network
# where there IS an uplink. This is what makes the closed result mean something:
# the probe is demonstrably capable of reporting a successful DNS lookup, a
# successful direct TCP connection and a successful direct HTTP fetch, so
# "ENETUNREACH / gaierror" inside the closed network is a property of the
# barrier and not of the probe.
#
# The proxy is addressed by its bridge-side IP here, so the allowlist's DENY for
# a non-allowlisted host is observable in BOTH postures.
#
# No model call, no credential.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROXY_NAME="${PROXY_NAME:-a0tl-proxy}"
IMAGE="${IMAGE:-python:3.12-slim}"
PROXY_BRIDGE_IP="$(docker inspect "$PROXY_NAME" \
  --format '{{(index .NetworkSettings.Networks "bridge").IPAddress}}')"

echo "== positive control: probe on the default bridge (uplink present)"
echo "   proxy bridge-side address: $PROXY_BRIDGE_IP"
docker run --rm --network bridge \
  -v "$HERE:/opt/a0tl:ro" \
  -v /home/ebt/rsi-dev:/home/ebt/rsi-dev:ro \
  -v /home/ebt/.local/share/uv/python:/home/ebt/.local/share/uv/python:ro \
  -e A0TL_PROXY="http://$PROXY_BRIDGE_IP:8787" \
  "$IMAGE" python3 /opt/a0tl/inlane/inlane_probe.py \
    --out /work/open_control_probe.json 2>&1 | tee "$HERE/evidence/open_control_probe.json"
