"""Compare E*'s verdicts with upstream's own evaluator on every member of C*.

For each candidate this runs `tools/upstream_oracle.py` (upstream's plugin, in a
subprocess so that a candidate which kills its interpreter cannot take this
harness with it) and compares the result with the frozen `E_STAR.json`:

  * upstream returned   <->  E* status == ok
  * upstream raised     <->  E* status in {invalid, error}
  * sum_radii           <->  E* objective.value, compared with `==` (binary64)
  * packing_density     <->  E* structure.packing_density, compared with `==`
  * num_circles         <->  E* structure.num_circles

    .venv/bin/python tools/crosscheck_upstream.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TABLE = ROOT / "E_STAR.json"
ORACLE = HERE / "upstream_oracle.py"
ORACLE_PYTHON = ROOT / ".venv-tools" / "bin" / "python"


def run_oracle(candidate_dir: Path, timeout: float) -> dict[str, Any]:
    # PYTHONDONTWRITEBYTECODE: upstream's plugin imports <candidate>/solution.py
    # in-process, which would otherwise leave a __pycache__ inside the candidate
    # directory.  E* itself cannot do that (it imports a private copy below its
    # own state root); this oracle is a tool and has to be told.
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [str(ORACLE_PYTHON), str(ORACLE), "--candidate", str(candidate_dir)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    for line in completed.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    return {
        "verdict": "no_report",
        "returncode": completed.returncode,
        "stderr_tail": completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, default=TABLE)
    args = parser.parse_args()

    table = json.loads(args.table.read_text(encoding="utf-8"))
    rows = []
    failures = []
    for entry in table["candidates"]:
        candidate_dir = ROOT / entry["dir"]
        oracle = run_oracle(candidate_dir, timeout=180.0)
        outcome = entry["outcome"]
        status = outcome["status"]
        objective = (outcome.get("objective") or {}).get("value")
        structure = outcome.get("structure") or {}

        problems = []
        if oracle["verdict"] == "returned":
            if status != "ok":
                problems.append(f"upstream returned but E* says {status}")
            if oracle.get("sum_radii") != objective:
                problems.append(f"sum_radii {oracle.get('sum_radii')!r} != E* {objective!r}")
            if oracle.get("packing_density") != structure.get("packing_density"):
                problems.append(
                    f"packing_density {oracle.get('packing_density')!r} != E* {structure.get('packing_density')!r}"
                )
            if oracle.get("num_circles") != structure.get("num_circles"):
                problems.append(f"num_circles {oracle.get('num_circles')!r} != E* {structure.get('num_circles')!r}")
        elif oracle["verdict"] == "raised":
            if status not in {"invalid", "error"}:
                problems.append(f"upstream raised but E* says {status}")
        elif (
            oracle["verdict"] == "no_report"
            and oracle.get("returncode") == 0
            and status == "error"
            and (outcome.get("failure") or {}).get("kind") == "child_terminated_early"
        ):
            # Expected, documented difference: upstream's plugin is called
            # in-process, so a candidate that kills its interpreter leaves its
            # caller a clean exit 0 and no verdict at all.  E* detects the
            # missing artifact instead (kind=child_terminated_early).
            pass
        elif oracle["verdict"] == "no_report":
            problems.append(f"unexpected oracle exit: rc={oracle.get('returncode')}")

        rows.append((entry["candidate_id"], status, objective, oracle, problems))
        if problems:
            failures.append((entry["candidate_id"], problems))

    width = max(len(row[0]) for row in rows)
    print(f"{'candidate':<{width}}  {'E* status':>9}  {'E* objective':>22}  upstream")
    for candidate_id, status, objective, oracle, problems in rows:
        if oracle["verdict"] == "raised":
            upstream = f"raised {oracle['error'].split(':', 1)[0]}"
        elif oracle["verdict"] == "returned":
            upstream = f"returned sum_radii={oracle['sum_radii']!r}"
        else:
            upstream = f"{oracle['verdict']} rc={oracle.get('returncode')}"
        flag = "" if not problems else "   <-- " + "; ".join(problems)
        shown = f"{objective:.12f}" if isinstance(objective, float) else "null"
        print(f"{candidate_id:<{width}}  {status:>9}  {shown:>22}  {upstream}{flag}")

    print()
    if failures:
        print(f"{len(failures)} candidate(s) disagree with upstream:")
        for candidate_id, problems in failures:
            print(f"  {candidate_id}: {'; '.join(problems)}")
        return 1
    print(f"all {len(rows)} candidates agree with upstream's evaluator")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
