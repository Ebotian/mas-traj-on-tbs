#!/usr/bin/env bash
# End-to-end reproduction of references/ : build MQLib, then run the full
# staged pipeline (ensemble -> SCIP -> top-up -> upper bounds -> table).
#
#   bash tools/reproduce.sh [workdir]
#
# The stages themselves live in tools/resume.sh, which is idempotent; this
# script only adds the one-time MQLib build in front of them.  Keeping a single
# implementation of the pipeline means the "reproduce from nothing" path and the
# "resume after an interruption" path cannot drift apart.
#
# Everything is local computation: no model calls, no spend.  The only network
# access is the single `git clone` of MQLib at the pinned commit in
# build/build_mqlib.sh.  Roughly 16 CPU-hours for the ensemble plus the top-up,
# SCIP and bound stages, i.e. about 2 hours of wall clock at --jobs 11-12 on a
# 12-thread box.
#
# workdir (default /tmp/mcwork) holds the MQLib checkout and the converted
# MQLib input files; nothing is written into ../suite/.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== step 0: build MQLib at the pinned commit =="
bash "$HERE/build/build_mqlib.sh" "${1:-/tmp/mcwork}"

exec bash "$HERE/tools/resume.sh" "$@"
