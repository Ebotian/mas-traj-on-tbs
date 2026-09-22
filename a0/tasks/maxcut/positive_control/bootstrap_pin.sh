#!/bin/sh
# One-time bootstrap of the pinned NetworkX used to *verify* PC_i's identity.
#
# The gate itself needs nothing from this script: `pc/solution.py` is a
# self-contained transliteration that runs under plain `python3`.  This venv
# exists only so that `verify_pc_identity.py` can run the real pinned NetworkX
# beside it and compare.
#
# Network notes (see ../DEVIATIONS.md D-PC-6):
#   * this host's configured http(s)_proxy refuses TLS, so the proxy variables
#     are unset for the fetch;
#   * github.com was intermittently unreachable during this round, so the script
#     has a PyPI fallback.  The fallback is only accepted if the `maxcut.py` it
#     installs is *byte-identical* to the pinned commit's file, which is the
#     property the verification actually depends on.
#
# Usage:  sh bootstrap_pin.sh          (idempotent; ~1 minute)
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
VENV="$HERE/.venv-pin"
PIN=b69beb2c4f6e480aaca4b0de7b4883f2b9f1030b
EXPECTED=793419aac0d000051ab9f9e2f9a0c9018d94cc871a8c385131d8fe01ca9590fb

digest() {
    "$VENV/bin/python" -c 'import hashlib, importlib; m = importlib.import_module("networkx.algorithms.approximation.maxcut"); print(hashlib.sha256(open(m.__file__, "rb").read()).hexdigest())'
}

if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV"
fi

current=$(digest 2>/dev/null || echo absent)
if [ "$current" != "$EXPECTED" ]; then
    if ! env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
            "$VENV/bin/pip" install --quiet --no-cache-dir \
            "networkx @ git+https://github.com/networkx/networkx.git@$PIN"; then
        echo "git pin unreachable; falling back to the PyPI wheel (checked by content)" >&2
        env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
            "$VENV/bin/pip" install --quiet --no-cache-dir networkx==3.6.1
    fi
    current=$(digest)
fi

"$VENV/bin/python" - <<PY
import networkx as nx
digest = "$current"
expected = "$EXPECTED"
print("networkx", nx.__version__, "maxcut.py", digest)
if digest != expected:
    raise SystemExit("REFUSING: installed maxcut.py does not match the pin %s" % expected)
print("pin OK")
PY
