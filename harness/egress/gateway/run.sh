#!/bin/bash
# Egress gateway v0 launcher. Binds the docker bridge IP so trial containers
# can reach it (once 172.17.0.1/32 is allowlisted at activation).
# Usage: bash run.sh [task]  (default: tumor-immune-interface)
set -eu
TASK="${1:-tumor-immune-interface}"
cd /home/ebt/harbor-runs/egress/gateway
export GITHUB_TOKEN="${GITHUB_TOKEN:-$(gh auth token 2>/dev/null || true)}"
exec python3 server.py --task "$TASK" --bind 172.17.0.1 --port 8788
