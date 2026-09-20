#!/usr/bin/env bash
# EvE evaluation step for the A0 circle-packing adapter.
#
# Generated from steps/eve_evaluator_step.sh.tmpl by a0_adapter.runtime.render_step_script;
# every value substituted below is frozen at generation time and recorded in the run's
# adapter.md together with the sha256 of the generated file.
#
# Contract: a0/contract/adapter_contract.md §4. EvE invokes this as `bash <script>` with
# cwd = the eval workspace and these variables injected (workflow/evaluation.py:290-318):
#   EVE_WORKSPACE_ROOT, EVE_SOLVER_ROOT, EVE_EVAL_LOG_ROOT, PYTHONDONTWRITEBYTECODE
# This script writes the score to $EVE_EVAL_LOG_ROOT/score.yaml.
#
# Hard constraint 1 (plan:544): neither E* nor this script depends on PATH or cwd. Every
# executable is referenced by absolute path and the candidate is addressed through the
# injected $EVE_SOLVER_ROOT.

set -uo pipefail

E_STAR_PYTHON='/home/ebt/rsi-dev/a0/tasks/circle-packing/.venv/bin/python'
E_STAR_SCRIPT='/home/ebt/rsi-dev/a0/tasks/circle-packing/e_star.py'
E_STAR_STATE_DIR='/home/ebt/rsi-dev/a0/runtimes/eve/out/run005/e-star-state'
SEED='1337'
FIDELITY='full'
FRACTION='1.0'
N_CIRCLES='26'
RUNS='5'
TIMEOUT_S='120.0'
RUNTIME_BUDGET_MS='250.0'
PRIMARY_FIELD='sum_radii'
EID_STAR='664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
PINS_SHA256='1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0'

MKDIR=/usr/bin/mkdir
RM=/usr/bin/rm
TAIL=/usr/bin/tail

log_root="${EVE_EVAL_LOG_ROOT:?EVE_EVAL_LOG_ROOT is not set}"
solver_root="${EVE_SOLVER_ROOT:?EVE_SOLVER_ROOT is not set}"
work="$log_root/e_star"

"$MKDIR" -p "$work"

outcome="$work/outcome.json"
resources="$work/resources.json"
stdout_f="$work/e_star.stdout.txt"
stderr_f="$work/e_star.stderr.txt"
"$RM" -f "$outcome" "$resources" "$stdout_f" "$stderr_f"

# --- the frozen evaluator, invoked exactly as the contract specifies -------------------
"$E_STAR_PYTHON" "$E_STAR_SCRIPT" evaluate \
  --candidate "$solver_root" \
  --seed "$SEED" \
  --fidelity "$FIDELITY" \
  --fraction "$FRACTION" \
  --n "$N_CIRCLES" \
  --runs "$RUNS" \
  --runtime-budget-ms "$RUNTIME_BUDGET_MS" \
  --timeout-s "$TIMEOUT_S" \
  --out "$outcome" \
  --state-dir "$E_STAR_STATE_DIR" \
  --emit-resources "$resources" \
  >"$stdout_f" 2>"$stderr_f"
rc=$?

# --- turn the canonical Outcome into EvE's score.yaml ----------------------------------
# The score is read from the canonical outcome JSON (fields.<PRIMARY_FIELD>), never from
# E*'s human-readable rendering and never from a runtime summary (adapter_contract.md §4.6).
"$E_STAR_PYTHON" - "$outcome" "$log_root/score.yaml" "$log_root/error.txt" \
  "$rc" "$PRIMARY_FIELD" "$EID_STAR" "$PINS_SHA256" "$stdout_f" "$stderr_f" <<'PY'
import json
import os
import sys

outcome_p, score_p, error_p, rc, primary_field, eid_star, pins_sha, stdout_p, stderr_p = sys.argv[1:10]
rc = int(rc)
note_p = os.path.join(os.path.dirname(score_p), "e_star", "step_note.txt")


def write(path, text):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def tail(path, limit=4000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()[-limit:]
    except OSError:
        return ""


outcome, parse_error = None, None
if os.path.exists(outcome_p):
    try:
        with open(outcome_p, "r", encoding="utf-8") as handle:
            outcome = json.load(handle)
    except Exception as exc:  # noqa: BLE001
        parse_error = f"outcome JSON unreadable: {exc!r}"
else:
    parse_error = "evaluator did not write an outcome JSON"

if outcome is not None:
    status = outcome.get("status")
    fields = outcome.get("fields") or {}
else:
    status, fields = None, {}

value = fields.get(primary_field)
measured = (
    rc == 0
    and status == "ok"
    and isinstance(value, (int, float))
    and not isinstance(value, bool)
)

if measured:
    # EvE reads this file with yaml.safe_load (workflow/evaluation.py:917-921) and then
    # validates that the leaf named by evaluation.failure_score ("score") is numeric
    # (:924-935). The extra keys are provenance and are ignored by that check.
    lines = [
        f"score: {float(value)!r}",
        f"summary: 'E* status=ok {primary_field}={float(value)!r}'",
        f"e_star_status: {json.dumps(status)}",
        f"e_star_canonical_digest: {json.dumps(outcome.get('canonical_digest'))}",
        "e_star_candidate_source_sha256: "
        + json.dumps((outcome.get("candidate") or {}).get("source_sha256")),
        f"eid_star: {json.dumps(eid_star)}",
        "e_star_fields:",
    ]
    lines += [f"  {key}: {json.dumps(fields[key])}" for key in sorted(fields)]
    write(score_p, "\n".join(lines) + "\n")
    if os.path.exists(error_p):
        os.remove(error_p)
    write(
        note_p,
        "measured=1 rc=%d status=%s %s=%r source=%s pins_sha256=%s\n"
        % (rc, status, primary_field, value, outcome_p, pins_sha),
    )
    raise SystemExit(0)

# Not measured. Write the side channel FIRST (so it survives even if EvE discards the log
# tree), then exit non-zero. A non-zero exit is what makes EvE's own
# `except Exception -> evaluation_failure_score` branch observable instead of silent
# (workflow/evaluation.py:161-165 with configs/eve/evaluation/circle_packing.yaml:8-10).
detail = {
    "rc": rc,
    "status": status,
    "primary_field": primary_field,
    "primary_value": value,
    "parse_error": parse_error,
    "failure": None if outcome is None else outcome.get("failure"),
    "e_star_stdout_tail": tail(stdout_p),
    "e_star_stderr_tail": tail(stderr_p),
}
write(note_p, "measured=0 " + json.dumps(detail, sort_keys=True) + "\n")
write(error_p, "E* did not return a measurement: " + json.dumps(detail, sort_keys=True) + "\n")
if os.path.exists(score_p):
    os.remove(score_p)
raise SystemExit(rc if rc != 0 else 4)
PY
status=$?

# E*'s machine-readable one-line manifest is already captured in $stdout_f; leave it as
# evidence and do not parse it for the score.
"$TAIL" -n 1 "$stdout_f" 2>/dev/null || true

exit "$status"
