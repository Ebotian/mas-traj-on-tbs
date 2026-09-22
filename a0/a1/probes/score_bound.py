#!/usr/bin/env python3
"""The plausibility bound on a harness-supplied score, through the real ABI.

`INTERFACE.md` principle (ii) makes the harness the author of the number, and the
`--override` hook is how that authorship is *shown*: the runtime's selection must
follow a number `E*` could not have produced.  A number the task cannot produce is
still a number, though, and before this probe nothing objected:
`a0/a1/eval_service.py` published `9999` beside `true_value 132` for a graph with
`|E| = 265`, the trace contract accepted it, and no gate check noticed.

This probe runs five requests through `eval_service.py`'s own ABI — the service is
started as its own process, exactly as a campaign starts it — on one graph with a
known bound (`G_dev_0001`: `|E| = 265`, `c02_ok_low_baseline` scores `132`), and
records what the service published and what it booked:

| case | override | mode | what must happen |
|---|---|---|---|
| `honest` | none | — | `132` published, flagged `within_bound` |
| `in_bound_override` | `200` | `bounded` | published, flagged `within_bound` |
| `above_the_bound` | `9999` | `bounded` | **refused**: `value: null`, `failure.kind: implausible_override`, booked `override_rejected` |
| `below_the_bound` | `-5` | `bounded` | **refused** the same way (a negative cut is not a cut) |
| `labelled_lie` | `9999` | `labelled_implausible` | published **with the lie on its face**: `plausibility.within_bound: false` on the response, the handed Outcome and the ledger row |

The last case is the one that must keep working: the deliberate wrong-value probe
is the evidence that the runtime consumes rather than measures, so the mode that
allows it exists — it is simply not the default, and it cannot be silent.

    python3 a0/a1/probes/score_bound.py --out-dir /tmp/a1/score-bound
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
E_SERVICE = REPO_ROOT / "a0" / "a1" / "eval_service.py"
CANDIDATE = "c02_ok_low_baseline"
CANDIDATE_PATH = REPO_ROOT / "a0" / "tasks" / "maxcut" / "candidates" / CANDIDATE
GRAPH = REPO_ROOT / "a0" / "tasks" / "maxcut" / "suite" / "dev" / "G_dev_0001.json"

#: The Outcome's own numbers for this instance, re-derived below from the run and
#: not taken on faith: `edges_total` is the bound, `132` is what the baseline
#: candidate really scores.
EXPECTED_TOTAL = 265
EXPECTED_HONEST = 132

#: name -> (override value or None, override mode)
CASES = (
    ("honest", None, "bounded"),
    ("in_bound_override", 200, "bounded"),
    ("above_the_bound", 9999, "bounded"),
    ("below_the_bound", -5, "bounded"),
    ("labelled_lie", 9999, "labelled_implausible"),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Service:
    """`eval_service.py serve`, started the way a campaign starts it."""

    def __init__(self, *, root: Path, campaign_id: str, override: Optional[int],
                 override_mode: str):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.stop_file = root.parent / f"{root.name}.stop"
        self.command = [
            "python3", str(E_SERVICE), "serve", "--root", str(root),
            "--evaluator", "maxcut",
            "--campaign-id", campaign_id, "--arm-id", "A_probe",
            "--harness-run-id", f"bound-{root.parent.name}",
            "--override-mode", override_mode,
            "--stop-file", str(self.stop_file),
        ]
        if override is not None:
            override_path = root / "override.json"
            override_path.write_text(json.dumps({CANDIDATE: override}, indent=1, sort_keys=True) + "\n",
                                     encoding="utf-8")
            self.command += ["--override", str(override_path)]
        self.process: Optional[subprocess.Popen] = None

    def __enter__(self) -> "Service":
        self.process = subprocess.Popen(self.command, cwd=str(REPO_ROOT),
                                        stdout=(self.root / "service.log").open("wb"),
                                        stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if (self.root / "harness_identity.json").is_file():
                return self
            if self.process.poll() is not None:
                raise SystemExit(f"the harness service exited {self.process.returncode}")
            time.sleep(0.05)
        raise SystemExit("the harness service did not write its identity")

    def __exit__(self, *exc) -> None:
        self.stop_file.write_text("stop\n", encoding="utf-8")
        try:
            self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()

    def request(self, request_id: str, *, timeout_s: float = 180.0) -> dict:
        document = {
            "schema": "a0.a1.eval_request/v1",
            "request_id": request_id,
            "campaign_id": "C_bound",
            "arm_id": "A_probe",
            "iteration": 1,
            "candidate_id": CANDIDATE,
            "candidate_path": str(CANDIDATE_PATH),
            "graph_path": str(GRAPH),
            "seed": 1337,
            "timeout_s": 10.0,
        }
        (self.root / "requests").mkdir(parents=True, exist_ok=True)
        (self.root / "requests" / f"{request_id}.json").write_text(
            json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        target = self.root / "responses" / f"{request_id}.json"
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if target.is_file():
                return json.loads(target.read_text(encoding="utf-8"))
            time.sleep(0.05)
        raise SystemExit(f"no response for {request_id}")

    def ledger(self) -> List[dict]:
        path = self.root / "ledger.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _row_for(ledger: List[dict], request_id: str) -> Optional[dict]:
    return next((row for row in ledger if row.get("request_id") == request_id), None)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="score_bound")
    parser.add_argument("--out-dir", default="/tmp/a1/score-bound")
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir).resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    cases: Dict[str, dict] = {}
    for index, (name, override, mode) in enumerate(CASES, start=1):
        request_id = f"b{index:04d}"
        with Service(root=out_dir / name / "harness", campaign_id="C_bound",
                     override=override, override_mode=mode) as service:
            response = service.request(request_id)
            ledger = service.ledger()
        row = _row_for(ledger, request_id)
        cases[name] = {
            "override": override,
            "mode": mode,
            "request_id": request_id,
            "response_value": response.get("value"),
            "response_status": response.get("status"),
            "response_true_value": response.get("true_value"),
            "response_handed_value": response.get("handed_value"),
            "response_override_applied": response.get("override_applied"),
            "response_override_rejected": response.get("override_rejected"),
            "response_failure": response.get("failure"),
            "response_plausibility": response.get("plausibility"),
            "outcome_value": (response.get("outcome") or {}).get("cut_edges"),
            "outcome_is_harness_authored": (response.get("outcome") or {}).get("harness_authored"),
            "outcome_plausibility": (response.get("outcome") or {}).get("plausibility"),
            "ledger": row,
            "service_command": service.command,
        }

    report: Dict[str, object] = {
        "schema": "a0.a1.score_bound/v1",
        "graph": str(GRAPH.relative_to(REPO_ROOT)),
        "graph_sha256": sha256_file(GRAPH),
        "candidate_id": CANDIDATE,
        "expected_edges_total": EXPECTED_TOTAL,
        "expected_honest_value": EXPECTED_HONEST,
        "service": {"script": "a0/a1/eval_service.py", "sha256": sha256_file(E_SERVICE)},
        "cases": cases,
    }

    honest = cases["honest"]
    in_bound = cases["in_bound_override"]
    above = cases["above_the_bound"]
    below = cases["below_the_bound"]
    labelled = cases["labelled_lie"]
    above_row = above["ledger"] or {}
    labelled_row = labelled["ledger"] or {}
    report["checks"] = {
        # The bound is the evaluator's own |E|, read from the Outcome it wrote.
        "the_honest_value_is_inside_the_outcome_s_own_bound": (
            honest["response_value"] == EXPECTED_HONEST
            and honest["response_plausibility"]["bound"]["upper"] == EXPECTED_TOTAL
            and honest["response_plausibility"]["bound"]["rule"] == "0 <= cut_edges <= edges_total"
            and honest["response_plausibility"]["within_bound"] is True
        ),
        "an_override_inside_the_bound_is_published": (
            in_bound["response_value"] == 200
            and in_bound["response_override_applied"] is True
            and in_bound["response_plausibility"]["within_bound"] is True
        ),
        "an_override_above_the_bound_is_refused_not_published": (
            above["response_value"] is None
            and above["response_status"] == "error"
            and above["response_override_rejected"] is True
            and (above["response_failure"] or {}).get("kind") == "implausible_override"
            and above["response_plausibility"]["within_bound"] is False
            and above["response_plausibility"]["verdict"] == "refused_out_of_bound"
        ),
        "the_refusal_is_booked_with_the_true_value_and_no_handed_value": (
            above_row.get("true_value") == EXPECTED_HONEST
            and above_row.get("handed_value") is None
            and above_row.get("override_rejected") is True
            and above_row.get("status") == "error"
        ),
        "an_override_below_the_bound_is_refused_the_same_way": (
            below["response_value"] is None
            and below["response_status"] == "error"
            and (below["response_failure"] or {}).get("kind") == "implausible_override"
        ),
        "the_labelled_mode_publishes_the_lie_with_its_label": (
            labelled["response_value"] == 9999
            and labelled["response_override_applied"] is True
            and labelled["response_plausibility"]["within_bound"] is False
            and labelled["response_plausibility"]["verdict"] == "accepted_labelled_out_of_bound"
            and labelled["response_plausibility"]["mode"] == "labelled_implausible"
            and (labelled["outcome_plausibility"] or {}).get("within_bound") is False
            and labelled["outcome_is_harness_authored"] is True
            and labelled_row.get("handed_value") == 9999
            and (labelled_row.get("plausibility") or {}).get("within_bound") is False
        ),
        "the_label_cannot_be_forgotten_because_the_default_refuses": (
            above["response_value"] is None and labelled["response_value"] == 9999
        ),
    }
    report["verdict"] = "pass" if all(report["checks"].values()) else "fail"  # type: ignore[union-attr]
    (out_dir / "score_bound.json").write_text(
        json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "checks": report["checks"],
                      "out": str(out_dir / "score_bound.json")}, indent=1))
    return 0 if report["verdict"] == "pass" else 5


if __name__ == "__main__":
    sys.exit(main())
