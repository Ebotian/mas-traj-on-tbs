"""Build A1's `CID` and the two arms' `AID_r` from the repository, and audit them.

The declarations are *derived*, not typed in: every hash is recomputed from the
bytes on this machine, so a declaration cannot go stale without the audit
noticing.  The causal-role rule (`causal.audit`) then checks the two failure
modes that matter: an object the campaign uses that is named nowhere, and a
"shared" object whose identity actually differs between arms.  On top of that,
`write` cross-checks the KAPSO arm's registered-evaluation tree against the tree
*itself*: the tree's locator must pin the `CID`'s `EID*`, and the factors the arm
declares must equal a fresh recomputation of the tree's bytes.  Without that a
registered tree built from a superseded `T1-EID.json`, with a binding re-derived
from *its* bytes so tree and binding agree, screens a different measurement than
the one `CID` declares and the audit still passes
(`a0/verify/a1-delta/REPORT.md` §2, finding 2c).

    python3 a0/a1/declaration.py build --out-dir a0/a1/declarations
    python3 a0/a1/declaration.py audit --out-dir a0/a1/declarations
    python3 a0/a1/declaration.py selftest      # falsify the cross-check, model-free
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

from a0.a1 import candidate_sandbox  # noqa: E402
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
    cid.add(Factor("harness.candidate_lane_isolation", "cid",
                   value={"mechanism": "unshare -rmnpf --mount-proc (user+mount+network+pid namespace)",
                          "hidden_roots": list(candidate_sandbox.DEFAULT_HIDDEN_ROOTS),
                          "candidate_allow_list": "the evaluator's files, the request's graph and "
                                                  "candidate, the invocation's state and out directory",
                          "net_isolate_flag": True,
                          "refuses_when_unavailable": True,
                          "override_above_the_bound": "refused unless --override-mode "
                                                      "labelled_implausible"},
                   sha256=_sha(REPO_ROOT / "a0/a1/candidate_sandbox.py"),
                   note="principle (iv) at the candidate lane: what a candidate can reach is part of "
                        "the measurement. Without it a candidate reads the stored reference "
                        "partitions or the provider key and the score is not a measurement "
                        "(a0/a1/probes/hostile_candidate.py). `none` is a labelled control mode "
                        "and is recorded as unsafe in harness_identity.json"))
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


def _identity_value(identity: str):
    """The decoded value of a `value:`-form factor identity, or `None`."""
    if not identity.startswith("value:"):
        return None
    try:
        return json.loads(identity.split("value:", 1)[1])
    except json.JSONDecodeError:
        return None


def registered_tree_checks(cid: Optional[CID] = None) -> list:
    """The tree on disk must agree with `binding.json` and, given a `cid`, with `CID`.

    Two of these are cross-workstream (the tree against the binding another
    workstream publishes).  The third is the check this audit exists for and does
    not otherwise make: the tree's own locator must pin the `EID*` `CID` names.
    Without it a registered tree built from a superseded `T1-EID.json` -- plus a
    binding re-derived from *its* bytes, so tree and binding agree -- screens a
    different measurement than the one `CID` declares, and the two declaration
    rules above say nothing (`a0/verify/a1-delta/REPORT.md` §2).

    A disagreement is a cross-workstream inconsistency, not a declaration
    problem, so it is reported as an audit problem against the arm that consumes
    the tree and it fails the verdict.  Every check carries a `kind`, so a failure
    has a name rather than a bare boolean.
    """
    checks = []
    if not KAPSO_T1_BINDING.is_file():
        return [{"ok": False, "kind": "registered_tree_disagreement",
                 "detail": f"the T1 registered tree binding is missing: {KAPSO_T1_BINDING}"}]
    binding = json.loads(KAPSO_T1_BINDING.read_text(encoding="utf-8"))
    tree = registered_tree()
    declared_files = (binding.get("registered_tree") or {}).get("files") or {}
    declared_value = binding.get("eid_r_value")
    checks.append({
        "ok": tree["files"] == declared_files,
        "kind": "registered_tree_disagreement",
        "detail": "a0/a1/kapso_t1/tree vs binding.json:registered_tree.files "
                  + ("agree" if tree["files"] == declared_files else
                     f"differ — disk {tree['files']} declared {declared_files}"),
    })
    checks.append({
        "ok": tree["fingerprint"] == declared_value,
        "kind": "registered_tree_disagreement",
        "detail": "recomputed manifest_fingerprint "
                  f"{tree['fingerprint']} vs binding.json:eid_r_value {declared_value}",
    })
    checks.append({
        "ok": tree["identity"]["eid_r"] == binding.get("eid_r"),
        "kind": "registered_tree_disagreement",
        "detail": f"AID_r factor identity {tree['identity']['eid_r']} vs binding {binding.get('eid_r')}",
    })
    if cid is not None:
        checks.extend(_locator_checks(cid))
    return checks


def _locator_checks(cid: CID) -> list:
    """The tree's locator must pin the `CID`'s `EID*` and the `CID`'s `E*` sources."""
    cid_eid = _identity_value(cid.factors["task.eid_star"].identity())["eid_star"]
    expected_sources = {
        "e_star.py": cid.factors["task.e_star_script"].sha256,
        "e_star_child.py": cid.factors["task.e_star_child"].sha256,
    }
    locator_path = KAPSO_T1_TREE / "a0_locator.json"
    try:
        locator = json.loads(locator_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [{"ok": False, "kind": "registered_tree_eid_mismatch",
                 "detail": f"the registered tree's locator {_rel(locator_path)} is missing or "
                           f"unreadable ({exc}), so the tree cannot be shown to pin the CID's "
                           f"EID* {cid_eid}"}]
    locator_eid = locator.get("eid_star")
    records = {record.get("path"): record.get("sha256")
               for record in ((locator.get("e_star") or {}).get("source_records") or [])}
    return [
        {"ok": locator_eid == cid_eid, "kind": "registered_tree_eid_mismatch",
         "detail": (f"the registered tree's locator {_rel(locator_path)} pins EID* "
                    f"{locator_eid}, but the CID names EID* {cid_eid}: the tree screens a "
                    "different evaluator than the declaration is about")
                   if locator_eid != cid_eid else
                   f"the registered tree's locator pins the CID's EID* {cid_eid}"},
        {"ok": records == expected_sources, "kind": "registered_tree_eid_mismatch",
         "detail": (f"the registered tree's locator E* source records {records} do not equal the "
                    f"CID's task.e_star_script/e_star_child digests {expected_sources}")
                   if records != expected_sources else
                   "the registered tree's locator pins the CID's E* source digests"},
    ]


def registered_tree_factor_checks(aid_documents: dict) -> list:
    """Every registered-tree factor an `AID_r` carries must equal the tree's bytes.

    `registered_tree_checks` compares the tree with the binding; this compares the
    *declaration as written* with a fresh recomputation of `registered_tree()`, so
    a hand-edited `AID_r`, or a tree rebuilt after it was written, fails instead of
    being taken at its word.
    """
    tree = registered_tree()
    checks = []
    for arm_id, document in sorted(aid_documents.items()):
        factors = document.get("factors") or {}
        declared = _identity_value(
            (factors.get("runtime.registered_evaluation_tree") or {}).get("identity", ""))
        if declared is None:
            continue  # not a value-form factor
        if declared.get("mechanism") == "none":
            continue  # the arm that declares this mechanism's absence
        checks.append({
            "ok": declared == tree["identity"],
            "kind": "registered_tree_factor_mismatch",
            "detail": f"AID_r.{arm_id}.runtime.registered_evaluation_tree names "
                      f"{declared.get('eid_r')}; the tree on disk hashes to "
                      f"{tree['identity']['eid_r']}",
        })
        declared_files = _identity_value(
            (factors.get("runtime.registered_evaluation_tree_files") or {}).get("identity", ""))
        if declared_files is not None:
            checks.append({
                "ok": declared_files == tree["files"],
                "kind": "registered_tree_factor_mismatch",
                "detail": f"AID_r.{arm_id}.runtime.registered_evaluation_tree_files "
                          + ("equals" if declared_files == tree["files"] else "differs from")
                          + " the tree's file map",
            })
    return checks


#: The revision whose registered tree was built against the superseded `EID*`
#: `cddfa64e…`; `selftest` offers it to the audit to falsify the locator cross-check.
PRE_REBUILD_REV = "7bf8a14b"


def selftest() -> int:
    """Falsify the locator cross-check with the recurrence the audit used to miss.

    A registered tree built from a superseded `T1-EID.json`, plus a `binding.json`
    re-derived from *its* bytes so the tree and the binding agree: the
    tree-vs-binding checks pass by construction and only the evaluator identity
    differs from `CID`.  The audit must fail on it and name the problem.  Everything
    happens in a temporary directory; the committed tree, binding and declarations
    are only read.
    """
    import tempfile

    failures = []
    with tempfile.TemporaryDirectory(prefix="declaration-selftest-honest-") as tmp:
        honest = write(Path(tmp) / "out")
        if honest["verdict"] == "pass":
            print("honest tree: audit pass")
        else:
            failures.append(f"the honest tree should pass: {honest['problems']}")

    with tempfile.TemporaryDirectory(prefix="declaration-selftest-stale-") as tmp:
        root = Path(tmp)
        tree = root / "tree"
        tree.mkdir()
        for name in ("kapso_eval.py", "a0_locator.json"):
            blob = subprocess.run(
                ["git", "-C", str(REPO_ROOT), "show",
                 f"{PRE_REBUILD_REV}:{_rel(KAPSO_T1_TREE)}/{name}"], capture_output=True)
            if blob.returncode != 0:
                print(f"cannot extract the pre-rebuild tree from {PRE_REBUILD_REV}: "
                      f"{blob.stderr.decode().strip()}", file=sys.stderr)
                return 2
            (tree / name).write_bytes(blob.stdout)
        files = {path.name: _sha(path) for path in sorted(tree.iterdir()) if path.is_file()}
        fingerprint = hashlib.sha256(
            json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        binding = json.loads(KAPSO_T1_BINDING.read_text(encoding="utf-8"))
        binding["registered_tree"]["files"] = files
        binding["eid_r_value"] = fingerprint
        binding["eid_r"] = f"manifest:{fingerprint}"
        stale_binding = root / "binding.json"
        stale_binding.write_text(json.dumps(binding, indent=1, sort_keys=True) + "\n",
                                 encoding="utf-8")
        locator_eid = json.loads((tree / "a0_locator.json").read_text(encoding="utf-8"))["eid_star"]

        original_tree, original_binding = KAPSO_T1_TREE, KAPSO_T1_BINDING
        globals()["KAPSO_T1_TREE"], globals()["KAPSO_T1_BINDING"] = tree, stale_binding
        try:
            stale = write(root / "out")
        finally:
            globals()["KAPSO_T1_TREE"], globals()["KAPSO_T1_BINDING"] = original_tree, original_binding

        kinds = sorted({problem["kind"] for problem in stale["problems"]})
        print(f"stale tree: locator pins EID* {locator_eid}")
        print(f"stale tree: audit verdict {stale['verdict']}, problem kinds {kinds}")
        if stale["verdict"] != "fail" or not stale["problems"]:
            failures.append("the stale registered tree passed the audit")
        if "registered_tree_eid_mismatch" not in kinds:
            failures.append(f"the stale tree failed without the named locator problem: {kinds}")

    for failure in failures:
        print(f"[FAIL] {failure}")
    print("selftest: " + ("pass" if not failures else "fail"))
    return 0 if not failures else 1


def write(out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    built = build()
    cid, aids = built["cid"], built["aids"]
    (out_dir / "CID.json").write_text(json.dumps(cid.as_dict(), indent=1, sort_keys=True) + "\n",
                                      encoding="utf-8")
    aid_documents = {}
    for aid in aids:
        path = out_dir / f"AID_r.{aid.campaign.arm_id}.json"
        text = json.dumps(aid.as_dict(), indent=1, sort_keys=True) + "\n"
        path.write_text(text, encoding="utf-8")
        aid_documents[aid.campaign.arm_id] = json.loads(text)
    observed = {name: factor.identity() for name, factor in cid.factors.items()}
    result = audit(cid, aids, observed=observed)
    # The audit's two rules say nothing about whether the registered tree's
    # *contents* are the evaluator `CID` names, so the tree is cross-checked here:
    # the tree's locator against CID's EID* and E* source digests, and the AID_r
    # factors against a fresh recomputation of the tree's bytes.  Both read back
    # what was just written rather than trusting the in-memory factors.
    for check in registered_tree_checks(cid) + registered_tree_factor_checks(aid_documents):
        if not check["ok"]:
            result["problems"].append({
                "kind": check.get("kind", "registered_tree_disagreement"),
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
    parser.add_argument("command", choices=["build", "audit", "show", "selftest"])
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "a0" / "a1" / "declarations"))
    args = parser.parse_args(argv)
    if args.command == "show":
        print(json.dumps(build()["cid"].as_dict(), indent=1, sort_keys=True))
        return 0
    if args.command == "selftest":
        return selftest()
    result = write(Path(args.out_dir))
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result["verdict"] == "pass" else 5


if __name__ == "__main__":
    sys.exit(main())
