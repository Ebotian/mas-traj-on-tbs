#!/usr/bin/env bash
# =============================================================================
# cli_sandbox_probe.sh -- probe the Codex CLI's OWN sandbox, without a model
#
# WHY THIS EXISTS
#   Protocol section 4.3 leans on one CLI-level guarantee: Codex CLI's
#   `workspace-write` sandbox defaults to `network_access: false`. On this
#   machine `codex exec` cannot complete a model call (its provider relay has
#   no working upstream), so the model lane cannot be exercised end to end.
#   `codex sandbox` is the CLI's own subcommand that applies the *same*
#   sandbox policy to an arbitrary command, with no model involved:
#
#       codex sandbox --help
#         > Run commands within a Codex-provided sandbox
#
#   That is the documented seam used here: real CLI code, real sandbox policy
#   resolution, real network cut -- only the model turn is absent.
#
# WHAT IS PROVEN
#   - negative case: the canary inside `sandbox_mode="workspace-write"` is
#     BLOCKED, while the same canary on the host is OPEN.
#   - positive control: the canary inside `sandbox_mode="danger-full-access"`
#     is OPEN, so the barrier is not "everything is broken".
#
# USAGE
#   ./cli_sandbox_probe.sh [--json FILE] [--workspace DIR] [--quiet]
#
# EXIT 0 iff every mode behaved as labelled.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANARY="$HERE/lane_net_probe.py"
PY="${PROBE_PYTHON:-/usr/bin/python3}"
WORKSPACE="${PROBE_WORKSPACE:-$HERE/../evidence/_sandbox_workspace}"
JSON_OUT=""
CODEX_BIN="${CODEX_BIN:-codex}"

while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON_OUT="$2"; shift 2 ;;
    --workspace) WORKSPACE="$2"; shift 2 ;;
    --quiet) shift ;;
    *) echo "cli_sandbox_probe: unknown arg '$1'" >&2; exit 2 ;;
  esac
done

command -v "$CODEX_BIN" >/dev/null || { echo "cli_sandbox_probe: '$CODEX_BIN' not found" >&2; exit 2; }
[ -f "$CANARY" ] || { echo "cli_sandbox_probe: canary missing: $CANARY" >&2; exit 2; }
mkdir -p "$WORKSPACE"

fails=0

run_case() {  # $1=label $2=expectation(open|blocked) $3..=codex args
  local label="$1" expect="$2"; shift 2
  local raw line observed verdict
  # NB: no `-C` here. `codex sandbox -C <dir>` switches the CLI into a
  # permissions-profile resolution mode that demands --permission-profile and
  # refuses to run otherwise (verified: exit 2). The working directory is
  # selected with `cd` instead, which is equivalent for this probe.
  raw="$(cd "$WORKSPACE" && timeout 90 "$CODEX_BIN" "$@" 2>&1)"
  line="$(printf '%s\n' "$raw" | grep -m1 '^LANE_PROBE ' || true)"
  if [ -z "$line" ]; then
    printf 'EVIDENCE case=%s rc=? %s\nVERDICT %s: MISMATCH (no canary output)\n' \
      "$label" "dns=? tcp=? tcpvia=none https=? local=? egress=BLOCKED" "$label"
    fails=$((fails + 1))
    return 0
  fi
  observed="$(printf '%s' "$line" | grep -oE 'egress=(OPEN|BLOCKED)' | cut -d= -f2)"
  if [ "$expect" = open ] && [ "$observed" = OPEN ]; then verdict="CONFIRMED"; else
    if [ "$expect" = blocked ] && [ "$observed" = BLOCKED ]; then verdict="CONFIRMED"; else
      verdict="MISMATCH"
      fails=$((fails + 1))
    fi
  fi
  printf 'EVIDENCE case=%s codex-args=[%s] %s\n' "$label" "$*" "${line#LANE_PROBE }"
  printf 'VERDICT %s: %s (expected egress_%s, observed egress_%s)\n' "$label" "$verdict" "$expect" "$observed"
  if [ -n "$JSON_OUT" ]; then
    printf '{"case":"%s","expect":"%s","observed":"%s","args":"%s"}\n' \
      "$label" "$expect" "$observed" "$*" >> "$JSON_OUT"
  fi
}

echo "### codex CLI sandbox probe  date=$(date -Is)"
echo "### codex=$($CODEX_BIN --version 2>&1)  canary=$CANARY  workspace=$WORKSPACE"
echo
echo "--- control 1: no sandbox at all (host) ---"
CANARY_HOST="$CANARY"
host_raw="$(timeout 60 "$PY" "$CANARY_HOST" 2>&1)"
host_line="$(printf '%s\n' "$host_raw" | grep -m1 '^LANE_PROBE ' || true)"
host_observed="$(printf '%s' "$host_line" | grep -oE 'egress=(OPEN|BLOCKED)' | cut -d= -f2)"
printf 'EVIDENCE case=host-no-sandbox mode=positive-control %s\n' "${host_line#LANE_PROBE }"
if [ "$host_observed" = OPEN ]; then
  echo "VERDICT host-no-sandbox: CONFIRMED (expected egress_open, observed egress_OPEN)"
else
  echo "VERDICT host-no-sandbox: MISMATCH (expected egress_open, observed egress_${host_observed:-unknown})"
  fails=$((fails + 1))
fi
echo

echo "--- codex sandbox modes (same canary, CLI sandbox applied) ---"
run_case "codex-sandbox-workspace-write" blocked \
  sandbox -c 'sandbox_mode="workspace-write"' -- "$PY" "$CANARY"
echo
run_case "codex-sandbox-danger-full-access" open \
  sandbox -c 'sandbox_mode="danger-full-access"' -- "$PY" "$CANARY"
echo
echo "--- the network_access knob inside workspace-write (why config alone is not proof) ---"
run_case "codex-sandbox-workspace-write+network_access=true" open \
  sandbox -c 'sandbox_mode="workspace-write"' \
  -c 'sandbox_workspace_write.network_access=true' -- "$PY" "$CANARY"
echo
if [ "$fails" -eq 0 ]; then
  echo "CLI-SANDBOX-PROBE: PASS"
else
  echo "CLI-SANDBOX-PROBE: FAIL ($fails case(s) did not match)"
fi
exit $((fails > 0))
