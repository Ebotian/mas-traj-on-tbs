#!/usr/bin/env bash
# =============================================================================
# simpleloop_lane_probe.sh -- closure posture of SimpleLoop's solver CLI
#
# SimpleLoop (plan:591-603) is R_S = (M, P, T, E, pi_S): model, tools, evaluator
# and ACCESS POLICY are meant to be the SAME as the complex runtimes', and only
# the search policy is simplified. Its closure posture is therefore not its
# own -- it is inherited from whatever CLI runs `c_{t+1} = Agent(c_t, H_t)`.
#
# This script makes that inheritance explicit and probeable per posture, so the
# moment the SimpleLoop driver fixes its solver CLI the verdict is one command
# away. It always runs both controls:
#
#   positive  the canary on the host reaches the network (so a blocked result
#             cannot be explained by generic broken networking)
#   negative  the canary inside the posture's barrier does not
#
# USAGE
#   ./simpleloop_lane_probe.sh --posture codex-workspace-write
#   ./simpleloop_lane_probe.sh --posture codex-danger-full-access
#   ./simpleloop_lane_probe.sh --posture unsandboxed-shell
#   ./simpleloop_lane_probe.sh --posture claude-skip-permissions
#
# Notes on the last two: `claude --dangerously-skip-permissions` offers no CLI
# sandbox, so the only available barrier is an external network cut
# (unshare -rn / docker --internal). That is exactly the barrier that also
# severs a HOST-LOCAL model relay (evidence/02_host_loopback_cut.log), so the
# model endpoint must be reachable from inside the barrier (a sibling
# container) or the lane cannot run closed on this machine.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVID="$HERE/../evidence"
EGRESS="$HERE/../../env/checks/probe_egress.sh"
CANARY="$HERE/lane_net_probe.py"
PY="${PROBE_PYTHON:-/usr/bin/python3}"
POSTURE=""
WORKSPACE="${PROBE_WORKSPACE:-$EVID/_sandbox_workspace}"

while [ $# -gt 0 ]; do
  case "$1" in
    --posture) POSTURE="$2"; shift 2 ;;
    --workspace) WORKSPACE="$2"; shift 2 ;;
    *) echo "simpleloop_lane_probe: unknown arg '$1'" >&2; exit 2 ;;
  esac
done
[ -n "$POSTURE" ] || { echo "simpleloop_lane_probe: --posture is required" >&2; exit 2; }
mkdir -p "$WORKSPACE"
mkdir -p "$EVID"

fails=0
lane_cmd="env -u http_proxy -u https_proxy $PY $CANARY"

classify() {  # $1=raw output -> prints EVIDENCE line, sets OBS
  local line
  line="$(printf '%s\n' "$1" | grep -m1 '^LANE_PROBE ' || true)"
  OBS="$(printf '%s' "$line" | grep -oE 'egress=(OPEN|BLOCKED)' | cut -d= -f2)"
  printf '%s\n' "$line"
}

check() {  # $1=case $2=expect
  local case_name="$1" expect="$2" obs="$OBS"
  if { [ "$expect" = open ] && [ "$obs" = OPEN ]; } || { [ "$expect" = blocked ] && [ "$obs" = BLOCKED ]; }; then
    printf 'VERDICT %s: CONFIRMED (expected egress_%s, observed egress_%s)\n' "$case_name" "$expect" "$obs"
  else
    printf 'VERDICT %s: MISMATCH (expected egress_%s, observed egress_%s)\n' "$case_name" "$expect" "${obs:-none}"
    fails=$((fails + 1))
  fi
}

echo "### SimpleLoop lane posture probe  posture=$POSTURE  date=$(date -Is)"
echo "### lane command under test: $lane_cmd"

echo
echo "--- positive control: same command, no barrier ---"
raw="$($lane_cmd 2>&1)"; classify "$raw"; check "host-no-barrier" open

case "$POSTURE" in
  codex-workspace-write|codex-danger-full-access)
    mode="${POSTURE#codex-}"
    echo
    echo "--- negative case: same command under the Codex CLI sandbox ($mode) ---"
    raw="$( cd "$WORKSPACE" && timeout 90 codex sandbox -c "sandbox_mode=\"$mode\"" -- "$PY" "$CANARY" 2>&1 )"
    classify "$raw"
    if [ "$mode" = workspace-write ]; then check "codex-sandbox-$mode" blocked; else check "codex-sandbox-$mode" open; fi
    echo
    echo "### mechanism = codex_cli_sandbox (workspace-write defaults to network_access=false)"
    ;;
  unsandboxed-shell|claude-skip-permissions)
    echo
    echo "--- negative case: same command inside an external network cut (unshare -rn) ---"
    raw="$(unshare -rn sh -c "$lane_cmd" 2>&1)"; classify "$raw"; check "unshare-rn" blocked
    echo
    echo "--- does that same cut still reach a HOST-LOCAL model relay? ---"
    raw="$(unshare -rn sh -c "curl -s -o /dev/null -w 'NETNS_RELAY_HTTP=%{http_code}' --noproxy '*' --max-time 5 http://127.0.0.1:${RELAY_PORT:-15722}/v1/models" 2>&1)"
    printf '%s\n' "$raw"
    echo "### mechanism = external_network_isolation (the orchestrator must stay OUTSIDE the barrier)"
    ;;
  *)
    echo "simpleloop_lane_probe: unknown posture '$POSTURE'" >&2
    exit 2
    ;;
esac

echo
if [ "$fails" -eq 0 ]; then echo "SIMPLELOOP-LANE-PROBE($POSTURE): PASS"; else echo "SIMPLELOOP-LANE-PROBE($POSTURE): FAIL ($fails)"; fi
exit $((fails > 0))
