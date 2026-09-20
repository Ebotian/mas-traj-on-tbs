"""Smoke check: drive one candidate through the real Loreley Evaluator."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from a0_adapter import runtime  # noqa: E402
from a0_adapter.contracts import ThetaE, load_candidate_set  # noqa: E402

RUN_DIR = Path(__file__).resolve().parents[1] / "out" / "smoke"
CANDIDATE_SET = runtime.A0_ROOT / "tasks" / "circle-packing" / "C_STAR" / "manifest.json"


def main() -> int:
    theta = ThetaE.parse("seed=1337,fidelity=full,fraction=1.0")
    env = runtime.FrozenEnvironment(run_dir=RUN_DIR, theta=theta)
    runtime.reset_workspace(env)

    program = RUN_DIR / "loreley.program.md"
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    program.write_text("# smoke program\n\n## Primary metric\n\n- name: sum_radii\n- direction: max\n",
                       encoding="utf-8")
    env.campaign_program_hash = __import__("hashlib").sha256(program.read_bytes()).hexdigest()
    env.apply()

    candidates = load_candidate_set(CANDIDATE_SET)
    for candidate in candidates.candidates:
        if candidate.candidate_id not in {"c01_good_hex", "c05_overlapping", "c09_malformed_import"}:
            continue
        result = runtime.run_through_loreley(env, candidate, iteration=0)
        print(json.dumps({
            "candidate": candidate.candidate_id,
            "outcome_kind": result.outcome_kind,
            "evaluator_name": result.evaluator_name,
            "evaluator_version": result.evaluator_version,
            "protocol": result.protocol,
            "reuse_kind": result.reuse_kind,
            "metrics": [m["name"] for m in result.metrics],
            "n_metrics": len(result.metrics),
            "evidence_status": (result.evidence or {}).get("status"),
            "failure": result.failure_summary,
            "elapsed_s": round(result.elapsed_s, 3),
        }, indent=1))
    print("PROGRAM", program)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
