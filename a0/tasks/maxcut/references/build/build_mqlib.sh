#!/usr/bin/env bash
# Rebuild MQLib at the pinned commit.  Reproduces the binary used to produce
# every R_i in ../targets.json.
#
#   bash build_mqlib.sh [destdir]     # destdir defaults to /tmp/mcwork
#
# NOTE ON NETWORK FLAKINESS: on this box the https proxy (127.0.0.1:7890)
# dropped TLS handshakes for roughly half of all requests during the build
# session, so the clone is wrapped in a retry loop.  That is an environment
# property, not a property of the pinned revision.
set -euo pipefail

DEST="${1:-/tmp/mcwork}"
CLONE_URL="https://github.com/MQLib/MQLib.git"
PIN="585496274af5abb0849d0d47e135496b4688680b"

mkdir -p "$DEST"
cd "$DEST"
if [ ! -d MQLib/.git ]; then
  rm -rf MQLib
  for attempt in $(seq 1 40); do
    echo "clone attempt $attempt" >&2
    if timeout 300 git clone "$CLONE_URL" MQLib 2>&1 | tail -2; then :; fi
    [ -d MQLib/.git ] && break
    rm -rf MQLib
    sleep 3
  done
fi
[ -d MQLib/.git ] || { echo "clone failed" >&2; exit 1; }

cd MQLib
git fetch --all --tags || true
git checkout --quiet "$PIN"
test "$(git rev-parse HEAD)" = "$PIN" || { echo "pin mismatch" >&2; exit 1; }
test -z "$(git status --porcelain)" || { echo "tree not clean -- a patch was applied?" >&2; exit 1; }

make clean >/dev/null 2>&1 || true
make -j"$(nproc)"
sha256sum bin/MQLib
echo "built: $DEST/MQLib/bin/MQLib"
