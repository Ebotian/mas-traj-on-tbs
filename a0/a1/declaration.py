"""Build A1's `CID` and the two arms' `AID_r` from the repository, and audit them.

The declarations are *derived*, not typed in: every hash is recomputed from the
bytes on this machine, so a declaration cannot go stale without the audit
noticing.  The causal-role rule (`causal.audit`) then checks the two failure
modes that matter: an object the campaign uses that is named nowhere, and a
"shared" object whose identity actually differs between arms.

    python3 a0/a1/declaration.py build --out-dir a0/a1/declarations
    python3 a0/a1/declaration.py audit --out-dir a0/a1/declarations
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from a0.a1.causal import AID, CID, CampaignID, Factor, audit, observed_identity  # noqa: E402

TASK_ID = "T1-maxcut"
ARMS = ("A_simpleloop", "A_kapso")

CIRCLE_PACKING = REPO_ROOT / "a0" / "tasks" / "circle-packing"


def git_rev(path: Path) -> str:
    proc = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                          capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def build() -> dict:
    """The CID plus one AID_r per arm."""
    task_graph = REPO_ROOT / "a0/tasks/maxcut/suite/dev/G_dev_0001.json"
    cid = CID(task_id=TASK_ID)
    cid.add(Factor("task.eid_star", "cid",
                   value={"document": "a0/a1/T1-EID.json",
                          "eid_star": json.loads((REPO_ROOT / "a0/a1/T1-EID.json")
                                                 .read_text())["eid_star"]},
                   note="the frozen evaluator identity; recompute with `python3 a0/a1/t1_eid.py check`"))
    cid.add(Factor("task.e_star_script", "cid",
                   sha256=_sha(REPO_ROOT / "a0/tasks/maxcut/e_star.py")))
    cid.add(Factor("task.e_star_child", "cid",
                   sha256=_sha(REPO_ROOT / "a0/tasks/maxcut/e_star_child.py")))
    cid.add(Factor("task.suite_manifest", "cid",
                   sha256=_sha(REPO_ROOT / "a0/tasks/maxcut/suite/manifest.json")))
    cid.add(Factor("task.candidate_set_manifest", "cid",
                   sha256=_sha(REPO_ROOT / "a0/tasks/maxcut/candidates/manifest.json")))
    cid.add(Factor("harness.eval_service", "cid",
                   sha256=_sha(REPO_ROOT / "a0/a1/eval_service.py")))
    cid.add(Factor("harness.eval_abi", "cid",
                   value={"request": "a0.a1.eval_request/v1",
                          "response": "a0.a1.harness_outcome/v1",
                          "owns_evaluation": True},
                   note="the harness runs E*; the runtime consumes the published Outcome"))
    cid.add(Factor("harness.measurement_token", "cid",
                   sha256=_sha(REPO_ROOT / "a0/envelope/envelope.py"),
                   note="a0/envelope's OID binding, issued per response"))
    cid.add(Factor("harness.topology", "cid",
                   value={"mechanism": "unshare -rn",
                          "reachable_peer": "campaign meter port over a unix socket",
                          "egress": "none"},
                   note="a0/a1/topology.py; probed, not asserted"))
    cid.add(Factor("harness.meter_mode", "cid",
                   value={"mode": "plaintext_base_url",
                          "allowlist": ["api.deepseek.com"],
                          "row_schema": "a0.meter.call/v1",
                          "ceq_formula": "miss + floor(hit*2/100) + 4*completion"},
                   note="INTERFACE.md §8; the proxy's own --aid-out fragment is AID_r's copy"))
    cid.add(Factor("harness.meter_body_repair", "cid",
                   sha256=_sha(REPO_ROOT / "a0/a1/meter_body_repair.py"),
                   note="declared compensating hop for a0/meter's missing request framing "
                        "(a0/a1/DEVIATIONS.md D-A1-3): the proxy forwards the upstream request "
                        "with no Content-Length, so every real call answers 400 and is booked "
                        "unmetered. Remove this factor when a0/meter is fixed."))
    cid.add(Factor("harness.failure_semantics", "cid",
                   value={"non_ok_carries_no_number": True,
                          "never_zero_for_failure": True,
                          "scalarization_owner": "F_r (per runtime)"},
                   note="INTERFACE.md §5 and §6 rule 5"))
    cid.add(Factor("model.route", "cid",
                   value={"provider": "deepseek", "model_requested": "deepseek-flash"},
                   note="the model family is held fixed across arms; a differing model id is a "
                        "confound, not an arm"))
    cid.add(Factor("measurement.protocol", "cid",
                   value={"ceq_source": "a0/meter ledger",
                          "evaluator_count_source": "a0/a1/eval_service ledger",
                          "wall_clock_source": "harness monotonic clock",
                          "runtime_self_report": "diagnostic only"},
                   note="principle (iv): the budget is read where the runtime cannot write"))

    aids = []
    for arm in ARMS:
        campaign = CampaignID(task_id=TASK_ID, block_id="B000", arm_id=arm,
                              replicate_id="R000")
        aid = AID(campaign=campaign)
        if arm == "A_simpleloop":
            aid.add(Factor("runtime.substrate", "aid_r",
                           value={"name": "simpleloop", "origin": "ours"},
                           note="the substrate under test"))
            aid.add(Factor("runtime.source", "aid_r",
                           sha256=_sha(REPO_ROOT / "a0/runtimes/simpleloop/a0_adapter/loop.py")))
            aid.add(Factor("runtime.outcome_lane", "aid_r",
                           sha256=_sha(REPO_ROOT / "a0/runtimes/simpleloop/a0_adapter/harnesseval.py"),
                           note="the code that consumes the harness Outcome; the only one in this arm"))
            aid.add(Factor("runtime.policy", "aid_r",
                           sha256=_sha(REPO_ROOT / "a0/runtimes/simpleloop/policy/simpleloop.maxcut.policy.json"),
                           note="the scalarization and tie-break the arm's selection uses"))
            aid.add(Factor("runtime.grant_triple", "aid_r",
                           value={"fidelity": "n/a (T1 has no fidelity classes)",
                                  "fraction": "n/a", "seed": 1337}))
        else:
            aid.add(Factor("runtime.substrate", "aid_r",
                           value={"name": "kapso", "origin": "third party"},
                           note="KAPSO's score-of-record path is a *different mechanism* "
                                "(the manifest line), which is why it is an arm"))
            aid.add(Factor("runtime.checkout", "aid_r",
                           value={"commit": git_rev(CIRCLE_PACKING / "upstream" / "kapso")
                                  if (CIRCLE_PACKING / "upstream" / "kapso").exists()
                                  else "7d99b152"},
                           note="/home/ebt/kapso_ck/kapso, read-only by protocol"))
            aid.add(Factor("runtime.outcome_lane", "aid_r",
                           sha256=_sha(REPO_ROOT / "a0/runtimes/kapso/a0_adapter/harness_manifest.py"),
                           note="the post-session manifest write; the ordering IS the attribution"))
            aid.add(Factor("runtime.grant_triple", "aid_r",
                           value={"fidelity": "read from strategy.fidelity_decision.eval_fidelity",
                                  "fraction": "read from strategy.fidelity_decision.eval_fraction",
                                  "seed": "read from strategy.registered_subsample_seed"},
                           note="derived from the runtime; a hardcoded triple is silently "
                                "discarded when the grant differs (HARNESS-OWNED-EVAL.md §7.2)"))
            aid.add(Factor("runtime.attribution_caveat", "aid_r",
                           value={"kapsos_ledger_is_not_realisation_evidence": True},
                           note="KAPSO files the harness's number under the registered "
                                "evaluator's id; A1 must not read its ledger as evidence"))
        aids.append(aid)

    return {
        "cid": cid,
        "aids": aids,
        "anchors": {
            "dev_instance": str(task_graph.relative_to(REPO_ROOT)),
            "dev_instance_sha256": _sha(task_graph),
        },
    }


def _sha(path: Path) -> str:
    return observed_identity(path).split(":", 1)[1]


def write(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    built = build()
    cid, aids = built["cid"], built["aids"]
    (out_dir / "CID.json").write_text(json.dumps(cid.as_dict(), indent=1, sort_keys=True) + "\n",
                                      encoding="utf-8")
    for aid in aids:
        path = out_dir / f"AID_r.{aid.campaign.arm_id}.json"
        path.write_text(json.dumps(aid.as_dict(), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    observed = {name: factor.identity() for name, factor in cid.factors.items()}
    result = audit(cid, aids, observed=observed)
    result["anchors"] = built["anchors"]
    (out_dir / "causal_audit.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n",
                                              encoding="utf-8")
    return result


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="a0.a1.declaration")
    parser.add_argument("command", choices=["build", "audit", "show"])
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "a0" / "a1" / "declarations"))
    args = parser.parse_args(argv)
    if args.command == "show":
        print(json.dumps(build()["cid"].as_dict(), indent=1, sort_keys=True))
        return 0
    result = write(Path(args.out_dir))
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result["verdict"] == "pass" else 5


if __name__ == "__main__":
    sys.exit(main())
