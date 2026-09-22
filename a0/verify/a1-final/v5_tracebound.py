#!/usr/bin/env python3
"""Item 4a — the trace validator's new score bound, both directions.

    python3 a0/verify/a1-final/v5_tracebound.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CONTRACT = REPO / "a0/contract"
VALIDATOR = CONTRACT / "trace_validate.py"
OUT_OF_RANGE = CONTRACT / "fixtures/traces/out_of_range.jsonl"
GOOD = CONTRACT / "fixtures/traces/good.jsonl"
METRIC = CONTRACT / "fixtures/sample/metric.json"
PY = sys.executable

results: list[tuple[str, bool, str]] = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    return ok


def run(*args, validator: Path = VALIDATOR, cwd: Path = REPO):
    proc = subprocess.run([PY, str(validator), *args], cwd=str(cwd),
                          capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> int:
    fixture = json.loads(OUT_OF_RANGE.read_text(encoding="utf-8").splitlines()[0])

    # -- the fixture really is good.jsonl with every score at 9999 ----------
    scores = [json.loads(line) for line in OUT_OF_RANGE.read_text(encoding="utf-8").splitlines()
              if line.strip()]
    score_events = [e for e in scores if e.get("trace") == "score"]
    signal_values = {e.get("search_signal") for e in score_events}
    outcome_values = {e.get("outcome", {}).get("fields", {}).get("coverage") for e in score_events}
    check("the fixture's every score is 9999",
          signal_values == {9999} and outcome_values == {9999},
          f"search_signal={signal_values} outcome.fields.coverage={outcome_values}")

    # -- direction 1: no metric named -> no bound (backwards compatible) ----
    rc, out = run("validate", "--trace", str(OUT_OF_RANGE))
    check("direction 1: without --metric the fixture still validates (no invented bound)",
          rc == 0 and "valid" in out, out.strip().splitlines()[-1] if out.strip() else f"rc={rc}")

    # -- direction 2: a metric that declares a range rejects it -------------
    rc, out = run("validate", "--trace", str(OUT_OF_RANGE), "--metric", str(METRIC))
    check("direction 2: with the range-declaring metric the fixture is rejected", rc != 0,
          out.strip().splitlines()[-1] if out.strip() else f"rc={rc}")
    check("direction 2b: every violation is reported with value, range and metric",
          "9999" in out and "0.7853981633974483" in out and "coverage" in out,
          f"{out.count('9999')} mentions of 9999")

    # -- the good stream stays valid with the metric in force ---------------
    rc, out = run("validate", "--trace", str(GOOD), "--metric", str(METRIC))
    check("the good stream is still valid with the metric named", rc == 0,
          out.strip().splitlines()[-1] if out.strip() else f"rc={rc}")

    # -- a metric that declares no range is not given one -------------------
    with tempfile.TemporaryDirectory() as tmp:
        no_range = Path(tmp) / "metric_no_range.json"
        doc = json.loads(METRIC.read_text(encoding="utf-8"))
        del doc["metric"]["range"]
        no_range.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        rc, out = run("validate", "--trace", str(OUT_OF_RANGE), "--metric", str(no_range))
        check("a metric without a declared range is not bounded", rc == 0,
              out.strip().splitlines()[-1] if out.strip() else f"rc={rc}")

        # a metric for another task is not in force, even with a range
        other_task = Path(tmp) / "metric_other_task.json"
        doc["metric"]["task"] = "not-this-task"
        doc["task"] = "not-this-task"
        doc["metric"]["range"] = [0.0, 1.0]
        other_task.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        rc, out = run("validate", "--trace", str(OUT_OF_RANGE), "--metric", str(other_task))
        check("a definition declared for another task is not in force", rc == 0,
              out.strip().splitlines()[-1] if out.strip() else f"rc={rc}")

        # a *tighter* range than the fixture's declared one must still reject
        tight = Path(tmp) / "metric_tight.json"
        doc["task"] = "circle-packing"
        doc["metric"]["range"] = [0.0, 0.5]
        tight.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        rc, out = run("validate", "--trace", str(OUT_OF_RANGE), "--metric", str(tight))
        check("an independent range I chose (0.0, 0.5] also rejects", rc != 0,
              out.strip().splitlines()[-1] if out.strip() else f"rc={rc}")

        # the pre-fix module accepts the fixture (the regression claim)
        raw = subprocess.run(["git", "show", "10686854^:a0/contract/trace_validate.py"],
                             cwd=str(REPO), capture_output=True, text=True)
        if raw.returncode != 0:
            check("pre-fix module retrievable from git", False, raw.stderr.strip()[:120])
        else:
            # the module resolves trace_schema.json beside itself, so the pin
            # gets its own directory with the (byte-unchanged) schema next to it
            pre_dir = Path(tmp) / "prefix"
            pre_dir.mkdir()
            (pre_dir / "trace_validate.py").write_text(raw.stdout, encoding="utf-8")
            (pre_dir / "trace_schema.json").write_bytes(
                (CONTRACT / "trace_schema.json").read_bytes())
            pre = pre_dir / "trace_validate.py"
            rc_good, out_good = run("validate", "--trace", str(GOOD), validator=pre)
            rc_oor, out_oor = run("validate", "--trace", str(OUT_OF_RANGE), validator=pre)
            check("regression: the pre-fix module accepts both streams unchecked",
                  rc_oor == 0 and rc_good == 0,
                  f"out_of_range rc={rc_oor} ({out_oor.strip()[-60:]}), good rc={rc_good}")
            # and the *new* module still rejects the same file, same cwd/dir layout
            new_dir = Path(tmp) / "new"
            new_dir.mkdir()
            (new_dir / "trace_validate.py").write_bytes(VALIDATOR.read_bytes())
            (new_dir / "trace_schema.json").write_bytes(
                (CONTRACT / "trace_schema.json").read_bytes())
            rc_new, out_new = run("validate", "--trace", str(OUT_OF_RANGE), "--metric", str(METRIC),
                                  validator=new_dir / "trace_validate.py")
            check("the new module rejects it under the identical directory layout", rc_new != 0,
                  f"rc={rc_new} {out_new.strip().splitlines()[-1] if out_new.strip() else ''}")

        # -- the run-level entry point must thread the same definition -------
        run_dir = Path(tmp) / "run" / "traces"
        run_dir.mkdir(parents=True)
        (run_dir / "simpleloop.R1.all.jsonl").write_bytes(OUT_OF_RANGE.read_bytes())
        rc_run, out_run = run("validate-run", "--run-dir", str(Path(tmp) / "run"),
                              "--metric", str(METRIC))
        check("validate-run rejects the out-of-range run with the metric named", rc_run != 0,
              out_run.strip().splitlines()[-1] if out_run.strip() else f"rc={rc_run}")
        rc_run_free, out_run_free = run("validate-run", "--run-dir", str(Path(tmp) / "run"))
        check("validate-run without --metric leaves the run unchecked (D-C-1, opt-in)",
              rc_run_free == 0,
              out_run_free.strip().splitlines()[-1] if out_run_free.strip() else f"rc={rc_run_free}")

    bad = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(bad)}/{len(results)} checks pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
