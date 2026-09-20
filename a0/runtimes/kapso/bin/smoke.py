"""Smoke test: does the KAPSO workspace, registration and both channels work?

Not part of the deliverable's evidence chain; it exists to fail fast while
building the adapter.  Run:

    .venv/bin/python bin/smoke.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from a0_adapter.common import (  # noqa: E402
    AdapterConfig, check_candidate_integrity, load_candidate_set, load_eid_star,
    verify_eid_star,
)
from a0_adapter.runtime import KapsoRuntime  # noqa: E402
from a0_adapter.channels import run_reference_e_star  # noqa: E402


def main() -> int:
    config = AdapterConfig.load()
    eid = load_eid_star(config.eid_star_file)
    candidates = load_candidate_set(config.candidate_set)
    check_candidate_integrity(candidates)
    print("EID*", eid.eid_star, "candidates", len(candidates))
    print(json.dumps(verify_eid_star(config, eid), indent=1))

    run_dir = Path("/home/ebt/rsi-dev/a0/runtimes/kapso/runs/smoke")
    state_root = Path("/home/ebt/rsi-dev/a0/runtimes/kapso/state/smoke")
    runtime = KapsoRuntime(
        config=config, eid=eid, candidates=candidates, run_dir=run_dir,
        state_root=state_root,
    )
    baseline = [c for c in candidates if c.candidate_id == "c02_baseline_upstream"][0]
    runtime.prepare(baseline)
    print("registration:", json.dumps(runtime.registration.__dict__, indent=1))

    theta = {
        "seed": 1337, "fidelity": "full", "fraction": 1.0,
    }
    for candidate_id in ("c01_good_hex", "c06_empty", "c09_malformed_import"):
        candidate = [c for c in candidates if c.candidate_id == candidate_id][0]
        branch = runtime.create_candidate_branch(candidate)
        ref = run_reference_e_star(config, eid, candidate_id, candidate.path,
                                   theta, state_root)
        reg = runtime.registered_channel_for_branch(candidate_id, branch, theta)
        print(f"--- {candidate_id}")
        print("  reference:", ref.exit_code, ref.status, ref.objective)
        print("  registered:", reg.exit_code, reg.status, reg.score,
              (reg.manifest or {}).get("items"),
              (reg.manifest or {}).get("candidate_identity"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
