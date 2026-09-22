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
import hashlib
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
    # `harness.meter_body_repair` was a CID factor between 9e836f36 and this
    # revision: a compensating hop for a0/meter's missing request framing
    # (DEVIATIONS.md D-A1-3). a0/meter commit 86987235 fixed the framing on the
    # proxy's own upstream leg, so the hop was deleted and the factor with it.
    # An audit of a campaign run in that window must expect one more CID factor
    # than this file produces.
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
            # The counterpart of the KAPSO arm's registered tree. This arm has no
            # registration mechanism at all (`native_scheme = none`,
            # `mapping_mode = adapter_declared_injection`): its `EID_r` is derived
            # from `EID*` plus the frozen policy, not from a tree. Declaring the
            # absence explicitly is what makes the factor arm-*varying* rather than
            # KAPSO-only, so a reader comparing the two arms sees the mechanism
            # difference instead of an asymmetry in the paperwork.
            aid.add(Factor("runtime.registered_evaluation_tree", "aid_r",
                           value={"mechanism": "none",
                                  "why": "SimpleLoop has no registered-evaluation surface; "
                                         "the adapter declares EID_r by injection"},
                           note="the object this arm does not have (see the KAPSO arm)"))
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
            # The registered evaluation tree. Adopted from a0/a1/kapso_t1's
            # D-KT1-7: the tree *is* part of P(Y|r) — it is KAPSO's registered
            # evaluator, it is what the session's manifest line comes from, and a
            # campaign that ran a different tree ran a different measurement. So it
            # must be inside AID_r, at full resolution rather than as a coarse
            # label: the identity below is recomputed from the tree's bytes here,
            # and `runtime.registered_evaluation_tree_files` carries the exact
            # per-file map so a rebuild can be checked without running the tree.
            tree = registered_tree()
            aid.add(Factor("runtime.registered_evaluation_tree", "aid_r",
                           value=tree["identity"],
                           note="KAPSO's registered evaluator for T1; EID_r = "
                                "manifest_fingerprint(tree). Recomputed from "
                                "a0/a1/kapso_t1/tree/ by declaration.py, and cross-checked "
                                "against a0/a1/kapso_t1/binding.json."))
            aid.add(Factor("runtime.registered_evaluation_tree_files", "aid_r",
                           value=tree["files"],
                           note="the fingerprint's inputs (KAPSO's own rule: sha256 over "
                                "json.dumps(manifest, sort_keys=True, separators=(',',':'))). "
                                "One byte in either file changes this factor."))
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


#: Where the T1 registered evaluation tree lives, and the binding that publishes
#: how its identity is computed. Both are another workstream's artifacts inside
#: this directory; they are read, never written.
KAPSO_T1_DIR = REPO_ROOT / "a0" / "a1" / "kapso_t1"
KAPSO_T1_TREE = KAPSO_T1_DIR / "tree"
KAPSO_T1_BINDING = KAPSO_T1_DIR / "binding.json"
#: KAPSO's own fingerprint rule, quoted from
#: `kapso/execution/evaluation_integrity.py:112-119` (and from the binding).
TREE_FINGERPRINT_RULE = (
    "KAPSO's own: sha256(json.dumps(manifest, sort_keys=True, separators=(',',':'))) "
    "- execution/evaluation_integrity.py:112-119"
)


def registered_tree() -> dict:
    """Recompute the T1 registered evaluation tree's identity from its bytes.

    Deliberately *derived*, not copied from `binding.json`: the audit's job is to
    notice when a declaration has gone stale, and a declaration that quotes
    another file's claim cannot do that. The recomputation is the fingerprint
    rule the binding publishes, so a third party can redo it with `sha256` and
    `json.dumps` alone.
    """
    files = {
        path.name: _sha(path)
        for path in sorted(KAPSO_T1_TREE.iterdir())
        if path.is_file()
    } if KAPSO_T1_TREE.is_dir() else {}
    fingerprint = hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest() if files else None
    return {
        "files": files,
        "fingerprint": fingerprint,
        "identity": {
            "eid_r": f"manifest:{fingerprint}" if fingerprint else None,
            "native_scheme": "manifest_fingerprint",
            "fingerprint_rule": TREE_FINGERPRINT_RULE,
            "tree": _rel(KAPSO_T1_TREE),
            "binding": _rel(KAPSO_T1_BINDING),
        },
    }


def _rel(path: Path) -> str:
    """Repo-relative when possible, absolute otherwise.

    The declaration is frozen and must not carry host paths, but a caller may
    point the module at a tree outside the repository (the unit tests do, to
    build the disagreement case); the fallback keeps that path reportable
    instead of raising.
    """
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(Path(path).resolve())


def registered_tree_checks() -> list:
    """The tree on disk must agree with what `binding.json` publishes.

    A disagreement is a cross-workstream inconsistency, not a declaration
    problem, so it is reported as an audit problem against the arm that consumes
    the tree and it fails the verdict.
    """
    checks = []
    if not KAPSO_T1_BINDING.is_file():
        return [{"ok": False, "detail": f"the T1 registered tree binding is missing: "
                                        f"{KAPSO_T1_BINDING}"}]
    binding = json.loads(KAPSO_T1_BINDING.read_text(encoding="utf-8"))
    tree = registered_tree()
    declared_files = (binding.get("registered_tree") or {}).get("files") or {}
    declared_value = binding.get("eid_r_value")
    checks.append({
        "ok": tree["files"] == declared_files,
        "detail": "a0/a1/kapso_t1/tree vs binding.json:registered_tree.files "
                  + ("agree" if tree["files"] == declared_files else
                     f"differ — disk {tree['files']} declared {declared_files}"),
    })
    checks.append({
        "ok": tree["fingerprint"] == declared_value,
        "detail": "recomputed manifest_fingerprint "
                  f"{tree['fingerprint']} vs binding.json:eid_r_value {declared_value}",
    })
    checks.append({
        "ok": tree["identity"]["eid_r"] == binding.get("eid_r"),
        "detail": f"AID_r factor identity {tree['identity']['eid_r']} vs binding {binding.get('eid_r')}",
    })
    return checks


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
    for check in registered_tree_checks():
        if not check["ok"]:
            result["problems"].append({
                "kind": "registered_tree_disagreement",
                "factor": "runtime.registered_evaluation_tree",
                "detail": check["detail"],
            })
    if result["problems"]:
        result["verdict"] = "fail"
    result["registered_tree"] = registered_tree()
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
