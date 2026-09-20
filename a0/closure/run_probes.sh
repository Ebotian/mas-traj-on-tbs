#!/usr/bin/env bash
# =============================================================================
# run_probes.sh -- closure verification probes for all four A0 runtimes
#
# Protocol: open_world_plan_review.typ section 4.3, last paragraph (line 569):
# a runtime's closure must be proven BY PROBE, never by a config flag alone.
# Audit history: open_world_plan_independent_review.typ D15 (line 320).
#
# Every mechanism is measured twice, in the same command text:
#   POSITIVE CONTROL  the command runs unblocked and really reaches the network
#                     (otherwise a probe that only ever shows failure proves
#                     nothing -- the barrier might simply be broken networking)
#   NEGATIVE CASE     the identical command runs inside the barrier and fails
#
# Outputs land in ../evidence/ and are summarised in ../VERDICTS.md.
# Per-runtime closure records (adapter_contract.md section 7 shape) are written
# to ../closure.<runtime>.json.
#
# EXIT 0 iff every executed probe matched its label.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVID="$HERE/evidence"
PROBES="$HERE/probes"
EGRESS="$HERE/../env/checks/probe_egress.sh"
EVE_SRC="${EVE_SRC:-/tmp/eve/src}"
KAPSO_SRC="${KAPSO_SRC:-/home/ebt/kapso_ck/kapso/src}"
LORELEY_TREE="${LORELEY_TREE:-$HERE/../tasks/circle-packing/upstream/loreley}"
LORELEY_PY="${LORELEY_PY:-$HERE/../runtimes/loreley/checkout/.venv/bin/python}"
EVE_PY="${EVE_PY:-$HERE/../runtimes/eve/.venv/bin/python}"
SYS_PY="${SYS_PY:-/usr/bin/python3}"
CANARY="$PROBES/lane_net_probe.py"

mkdir -p "$EVID"
fails=0
STAMP="$(date -Is)"

echo "### a0 closure probes  started $STAMP"
echo "### evidence dir: $EVID"

# ---------------------------------------------------------------------------
# 0. self-test of the available isolation mechanisms (both controls each)
# ---------------------------------------------------------------------------
echo
echo "== [0] isolation mechanisms self-test =="
if [ -x "$EGRESS" ]; then
  ( cd "$(dirname "$EGRESS")" && ./probe_egress.sh self-test ) >"$EVID/00_self_test.log" 2>&1
  rc=$?
  tail -3 "$EVID/00_self_test.log"
  echo "   -> $EVID/00_self_test.log (rc=$rc)"
  [ "$rc" -eq 0 ] || fails=$((fails + 1))
else
  echo "   probe_egress.sh not found at $EGRESS -- skipped"
  fails=$((fails + 1))
fi

# ---------------------------------------------------------------------------
# 1. external network isolation: the same lane canary, open vs cut
# ---------------------------------------------------------------------------
echo
echo "== [1] external network isolation (host vs unshare -rn), same command =="
LANE_CMD="env -u http_proxy -u https_proxy $SYS_PY $CANARY"
external_case() {  # $1=mechanism $2=expectation(open|blocked)
  local mech="$1" expect="$2" out ev obs lane_line rc=0
  out="$( cd "$(dirname "$EGRESS")" && ./probe_egress.sh check --mechanism "$mech" \
      --timeout 60 --cmd "$LANE_CMD" 2>&1 )" || rc=$?
  printf '%s\n' "$out" >>"$EVID/01_external_isolation.log"
  ev="$(printf '%s\n' "$out" | grep -m1 '^EVIDENCE' || true)"
  # NB: probe_egress.sh's own classifier reads *all* `egress=` matches, and the
  # lane canary below also prints one, so its VERDICT is unreliable for
  # `--cmd` runs. The EVIDENCE line carries the mechanism canary's own
  # classification, which is what we read here.
  obs="$(printf '%s' "$ev" | grep -oE 'egress=(OPEN|BLOCKED)' | tail -1 | cut -d= -f2)"
  lane_line="$(printf '%s\n' "$out" | grep -m1 '^LANE_PROBE ' || true)"
  printf '  %-12s expect=egress_%-7s mechanism-canary=%s  lane-command: %s\n' \
    "$mech" "$expect" "${obs:-<none>}" "${lane_line:-<no LANE_PROBE line>}"
  if { [ "$expect" = open ] && [ "$obs" = OPEN ]; } || { [ "$expect" = blocked ] && [ "$obs" = BLOCKED ]; }; then
    printf '  VERDICT %s: CONFIRMED\n' "$mech"
  else
    printf '  VERDICT %s: MISMATCH (expected egress_%s, observed %s)\n' "$mech" "$expect" "${obs:-none}"
    fails=$((fails + 1))
  fi
}
if [ -x "$EGRESS" ]; then
  external_case host open
  external_case unshare-rn blocked
  echo "   -> $EVID/01_external_isolation.log"
fi

# ---------------------------------------------------------------------------
# 2. sharp edge: does the cut also sever a HOST-LOCAL model relay?
#    (codex on this machine is configured against http://127.0.0.1:15722/v1)
# ---------------------------------------------------------------------------
echo
echo "== [2] host-loopback sharp edge: model relay reachable inside the cut? =="
RELAY_PORT="${RELAY_PORT:-15722}"
{
  echo "### date=$STAMP relay=127.0.0.1:$RELAY_PORT"
  echo "--- on the host, no barrier ---"
  curl -s -o /dev/null -w 'HOST_RELAY_HTTP=%{http_code}\n' --noproxy '*' --max-time 5 \
    "http://127.0.0.1:$RELAY_PORT/v1/models" || echo "HOST_RELAY_HTTP=000"
  echo "--- inside unshare -rn, same URL ---"
  unshare -rn sh -c "curl -s -o /dev/null -w 'NETNS_RELAY_HTTP=%{http_code}\n' --noproxy '*' --max-time 5 http://127.0.0.1:$RELAY_PORT/v1/models" \
    2>&1 || echo "NETNS_RELAY_HTTP=000 (unreachable)"
  echo "--- inside an --internal docker network, reaching the host gateway ---"
  docker network inspect a0-egress-internal >/dev/null 2>&1 || docker network create --internal a0-egress-internal >/dev/null
  docker run --rm --network a0-egress-internal --add-host=host.docker.internal:host-gateway \
    --entrypoint sh alpine:3.21 -c \
    "wget -q -T 3 -O- http://host.docker.internal:$RELAY_PORT/v1/models >/dev/null 2>&1 && echo INTERNAL_HOSTGW_RELAY=ok || echo INTERNAL_HOSTGW_RELAY=fail; wget -q -T 5 -O- https://example.com >/dev/null 2>&1 && echo INTERNAL_EGRESS=open || echo INTERNAL_EGRESS=blocked" \
    2>&1 | tail -2
} >"$EVID/02_host_loopback_cut.log" 2>&1
tail -6 "$EVID/02_host_loopback_cut.log"
echo "   -> $EVID/02_host_loopback_cut.log"

# ---------------------------------------------------------------------------
# 3. the Codex CLI's own sandbox (the only mechanism that separates the model
#    lane from the tool lane)
# ---------------------------------------------------------------------------
echo
echo "== [3] codex CLI sandbox modes (workspace-write vs danger-full-access) =="
if "$PROBES/cli_sandbox_probe.sh" --json "$EVID/03_cli_sandbox.jsonl" \
     >"$EVID/03_cli_sandbox.log" 2>&1; then
  rc=0
else
  rc=$?
fi
grep -E '^(EVIDENCE|VERDICT|CLI-SANDBOX)' "$EVID/03_cli_sandbox.log"
[ "$rc" -eq 0 ] || fails=$((fails + 1))
echo "   -> $EVID/03_cli_sandbox.log"

# ---------------------------------------------------------------------------
# 4. per-runtime argv seams (real runtime code, no model call)
# ---------------------------------------------------------------------------
echo
echo "== [4] runtime argv seams =="
if [ -d "$EVE_SRC" ] && [ -x "$EVE_PY" ]; then
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$EVE_SRC" "$EVE_PY" "$PROBES/seam_eve_argv.py" >"$EVID/04_seam_eve.log" 2>&1
  echo "   eve seam rc=$? -> $EVID/04_seam_eve.log"
else
  echo "   eve seam SKIPPED (EVE_SRC=$EVE_SRC EVE_PY=$EVE_PY)" | tee "$EVID/04_seam_eve.log"
fi
if [ -d "$KAPSO_SRC" ] && [ -x "$HERE/.venv/bin/python" ]; then
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$KAPSO_SRC" "$HERE/.venv/bin/python" "$PROBES/seam_kapso_argv.py" \
    >"$EVID/04_seam_kapso.log" 2>&1
  echo "   kapso seam rc=$? -> $EVID/04_seam_kapso.log"
else
  echo "   kapso seam SKIPPED (KAPSO_SRC=$KAPSO_SRC venv=$HERE/.venv)" | tee "$EVID/04_seam_kapso.log"
fi
if [ -d "$LORELEY_TREE" ] && [ -x "$LORELEY_PY" ]; then
  ( cd /tmp && LOG_LEVEL=WARNING PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$LORELEY_TREE" \
      "$LORELEY_PY" "$PROBES/seam_loreley_argv.py" ) >"$EVID/04_seam_loreley.log" 2>&1
  echo "   loreley seam rc=$? -> $EVID/04_seam_loreley.log"
else
  echo "   loreley seam SKIPPED (tree=$LORELEY_TREE py=$LORELEY_PY)" | tee "$EVID/04_seam_loreley.log"
fi

# ---------------------------------------------------------------------------
# 5. surface beyond the shell sandbox: the CLI's own capability flags
# ---------------------------------------------------------------------------
echo
echo "== [5] codex capability surface (beyond the shell sandbox) =="
{
  echo "### date=$(date -Is)"
  echo "### codex $("$SYS_PY" -c 'pass' 2>/dev/null; codex --version 2>&1)"
  echo "--- feature flags relevant to external acquisition ---"
  codex features list 2>&1 | grep -iE "web|search|browser|computer|network|proxy|mcp|apps" || true
  echo "--- --search help text ---"
  codex --help 2>&1 | grep -A2 -- '--search' || true
  echo "--- exec bypass flag help text ---"
  codex exec --help 2>&1 | grep -A3 -- '--dangerously-bypass-approvals-and-sandbox' || true
} >"$EVID/05_codex_surface.log" 2>&1
tail -18 "$EVID/05_codex_surface.log"
echo "   -> $EVID/05_codex_surface.log"

echo
echo "== [6] SimpleLoop lane postures (inherited from its solver CLI) =="
for posture in codex-workspace-write codex-danger-full-access unsandboxed-shell; do
  if "$PROBES/simpleloop_lane_probe.sh" --posture "$posture" \
      >"$EVID/06_simpleloop_$posture.log" 2>&1; then
    rc=0
  else
    rc=$?
  fi
  printf '   posture=%-22s rc=%s  %s\n' "$posture" "$rc" \
    "$(grep -m1 '^VERDICT' "$EVID/06_simpleloop_$posture.log" | tail -1)"
  [ "$rc" -eq 0 ] || fails=$((fails + 1))
done
echo "   -> $EVID/06_simpleloop_*.log"

echo
echo "== [7] end-to-end lane probes: real model turn, per runtime and posture =="
# The lane argv is built by each runtime's own code (see probes/lane_e2e_probe.py):
# KAPSO's CodexCodingAgent._exec_command, SimpleLoop's CliSolver._command. The model
# is asked to run the shared canary through its shell tool and to persist the
# canary's stdout into the work dir, so the model's prose is never the evidence.
lane_case() {  # $1=runtime $2=posture $3=expect_verdict $4=outfile $5=pythonpath $6=python
  local runtime="$1" posture="$2" expect="$3" out="$4" pp="$5" py="$6" got
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$pp" "$py" "$PROBES/lane_e2e_probe.py" \
    --runtime "$runtime" --posture "$posture" --out "$EVID/$out" \
    >"$EVID/${out%.json}.log" 2>&1
  got="$("$py" -c "import json,sys;print(json.load(open('$EVID/$out'))['verdict'])" 2>/dev/null)"
  if [ "$got" = "$expect" ]; then
    printf '   %-10s %-6s -> %-15s CONFIRMED (expected %s)\n' "$runtime" "$posture" "${got:-none}" "$expect"
  else
    printf '   %-10s %-6s -> %-15s MISMATCH (expected %s)\n' "$runtime" "$posture" "${got:-none}" "$expect"
    fails=$((fails + 1))
  fi
}
lane_case kapso      closed closed          17_kapso_lane_closed.json      "$KAPSO_SRC" "$HERE/.venv/bin/python"
lane_case kapso      open   egress_detected 17_kapso_lane_open.json        "$KAPSO_SRC" "$HERE/.venv/bin/python"
lane_case simpleloop closed closed          17_simpleloop_lane_closed.json "$HERE/../runtimes/simpleloop" "$HERE/.venv/bin/python"
lane_case simpleloop open   egress_detected 17_simpleloop_lane_open.json   "$HERE/../runtimes/simpleloop" "$HERE/.venv/bin/python"
echo "   -> $EVID/17_*.json (+ .log)"

echo
if [ "$fails" -eq 0 ]; then
  echo "ALL EXECUTED PROBES MATCHED THEIR LABELS.  (fails=0)"
else
  echo "SOME PROBES DID NOT MATCH ($fails); see the evidence files above."
fi
exit $((fails > 0))