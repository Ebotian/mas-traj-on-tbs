#!/usr/bin/env python3
"""Item 2 — `CID` vs `AID_r` agreement, and whether the agreement is *enforced*.

Three questions, in order:

1. Do the two factors of `a0/a1/declaration.py::registered_tree()` recompute to what
   `AID_r.A_kapso.json` and `CID.json` actually contain? (recomputed from bytes)
2. Does `declaration.py build` reproduce the committed declarations byte for byte,
   and does the causal audit pass? (written into a scratch dir, never into the tree)
3. What would have to move for `CID` and `AID_r` to disagree again, and would anything
   catch it? The pre-rebuild tree is extracted from git and offered to the audit as if
   it were the registered tree, with a binding re-stamped to match it, so the tree and
   the binding agree with each other and only the *evaluator identity* differs.

    python3 a0/verify/a1-delta/d2_declaration.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
KAPSO = REPO / "a0" / "a1" / "kapso_t1"
DECL = REPO / "a0/a1/declarations"
PRE_REBUILD_REV = "7bf8a14b"

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    CHECKS.append((name, bool(ok), detail))
    print(f"[{'ok ' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))
    return bool(ok)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def main() -> int:
    sys.path.insert(0, str(REPO))
    from a0.a1 import declaration  # noqa: E402

    # ------------------------------------------------------- (1) the two factors
    print("== the two registered-tree factors, recomputed from the tree bytes ==")
    tree = declaration.registered_tree()
    files = {p.name: sha256_file(p) for p in sorted((KAPSO / "tree").iterdir()) if p.is_file()}
    fingerprint = hashlib.sha256(canon(files)).hexdigest()
    check("registered_tree()'s file map == my recomputation", tree["files"] == files, str(files))
    check("registered_tree()'s fingerprint == sha256(canonical file map)",
          tree["fingerprint"] == fingerprint,
          fingerprint[:16] + "…")
    check("registered_tree()'s eid_r is 'manifest:<fingerprint>'",
          tree["identity"]["eid_r"] == f"manifest:{fingerprint}")

    aid = json.loads((DECL / "AID_r.A_kapso.json").read_text())["factors"]
    rid = json.loads(aid["runtime.registered_evaluation_tree"]["identity"].split("value:", 1)[1])
    rfiles = json.loads(aid["runtime.registered_evaluation_tree_files"]["identity"]
                        .split("value:", 1)[1])
    check("AID_r's tree factor == the recomputed identity",
          rid == tree["identity"], json.dumps(rid)[:120])
    check("AID_r's files factor == the recomputed file map", rfiles == files)

    cid = json.loads((DECL / "CID.json").read_text())["factors"]
    cid_eid = json.loads(cid["task.eid_star"]["identity"].split("value:", 1)[1])["eid_star"]
    cid_e_star = cid["task.e_star_script"]["identity"].split(":", 1)[1]
    cid_e_child = cid["task.e_star_child"]["identity"].split(":", 1)[1]
    check("CID's task.eid_star == T1-EID.json's recomputed EID*",
          cid_eid == json.loads((REPO / "a0/a1/T1-EID.json").read_text())["eid_star"])
    check("CID's E* script digests == the bytes on disk",
          cid_e_star == sha256_file(REPO / "a0/tasks/maxcut/e_star.py")
          and cid_e_child == sha256_file(REPO / "a0/tasks/maxcut/e_star_child.py"))

    # The cross-check the audit does NOT make, made by hand: the tree's own locator
    # pins an EID*; is it the one CID names?
    locator = json.loads((KAPSO / "tree/a0_locator.json").read_text())
    check("the tree's locator pins the same EID* as CID (the cross-check the audit skips)",
          locator["eid_star"] == cid_eid, locator["eid_star"][:16] + "…")
    check("the tree's locator pins the same E* source files as CID",
          {r["path"]: r["sha256"] for r in locator["e_star"]["source_records"]}
          == {"e_star.py": cid_e_star, "e_star_child.py": cid_e_child})

    # ------------------------------------------------ (2) rebuild + audit + diff
    print("\n== rebuilding the declarations into a scratch dir, then diffing ==")
    with tempfile.TemporaryDirectory(prefix="a1delta-decl-") as tmp:
        tmp = Path(tmp)
        # `write` is what `a0/a1/verify.py`'s `declarations` step runs, but pointed
        # away from the committed directory so this probe cannot rewrite it.
        result = declaration.write(tmp)
        check("the causal audit verdict is pass", result["verdict"] == "pass",
              f"problems={result['problems']}")
        check("registered_tree_checks() are all ok",
              all(c["ok"] for c in declaration.registered_tree_checks()))
        same = {name: (tmp / name).read_bytes() == (DECL / name).read_bytes()
                for name in ("CID.json", "AID_r.A_kapso.json", "AID_r.A_simpleloop.json",
                             "causal_audit.json")}
        check("a fresh build reproduces the committed declarations byte for byte",
              all(same.values()), str(same))
        committed_audit = json.loads((DECL / "causal_audit.json").read_text())
        check("the committed causal_audit.json says pass with no problems",
              committed_audit["verdict"] == "pass" and committed_audit["problems"] == [])

    # ------------------------------------ (3) constructing a recurrence of the defect
    print("\n== can CID and AID_r disagree again without the audit noticing? ==")
    print(f"   (offering the registered tree as of {PRE_REBUILD_REV} — the pre-rebuild")
    print("    bytes, whose locator pins the superseded EID* — with a binding re-stamped")
    print("    to those bytes, so tree and binding agree with each other)")
    with tempfile.TemporaryDirectory(prefix="a1delta-stale-") as tmp:
        tmp = Path(tmp)
        stale_tree = tmp / "tree"
        stale_tree.mkdir()
        for name in ("kapso_eval.py", "a0_locator.json"):
            blob = subprocess.run(["git", "-C", str(REPO), "show",
                                   f"{PRE_REBUILD_REV}:a0/a1/kapso_t1/tree/{name}"],
                                  capture_output=True, check=True).stdout
            (stale_tree / name).write_bytes(blob)
        stale_locator = json.loads((stale_tree / "a0_locator.json").read_text())
        stale_files = {p.name: sha256_file(p) for p in sorted(stale_tree.iterdir())}
        stale_fp = hashlib.sha256(canon(stale_files)).hexdigest()
        # the binding must agree with the stale tree, exactly as the rebuild's own
        # binding agreed with the rebuilt one
        binding = json.loads((KAPSO / "binding.json").read_text())
        binding["registered_tree"]["files"] = stale_files
        binding["eid_r_value"] = stale_fp
        binding["eid_r"] = f"manifest:{stale_fp}"
        stale_binding = tmp / "binding.json"
        stale_binding.write_text(json.dumps(binding, indent=1, sort_keys=True) + "\n")

        original_tree, original_binding = declaration.KAPSO_T1_TREE, declaration.KAPSO_T1_BINDING
        declaration.KAPSO_T1_TREE, declaration.KAPSO_T1_BINDING = stale_tree, stale_binding
        try:
            out = tmp / "out"
            result = declaration.write(out)
            built_aid = json.loads((out / "AID_r.A_kapso.json").read_text())["factors"]
            built_fp = json.loads(
                built_aid["runtime.registered_evaluation_tree_files"]["identity"]
                .split("value:", 1)[1])
            built_eid = json.loads(
                built_aid["runtime.registered_evaluation_tree"]["identity"]
                .split("value:", 1)[1])["eid_r"]
            built_cid = json.loads((out / "CID.json").read_text())["factors"]
            built_cid_eid = json.loads(
                built_cid["task.eid_star"]["identity"].split("value:", 1)[1])["eid_star"]
            print(f"    stale tree locator pins EID* {stale_locator['eid_star'][:16]}…")
            print(f"    AID_r names EID_r {built_eid[:34]}…")
            print(f"    CID   names EID* {built_cid_eid[:16]}…")
            caught = result["verdict"] == "fail"
            check("the declaration audit CATCHES a tree built from a superseded EID*",
                  caught,
                  f"verdict={result['verdict']} problems={result['problems']}")
            check("...and the two declarations really do disagree in that state",
                  stale_locator["eid_star"] != built_cid_eid
                  and built_eid == f"manifest:{stale_fp}",
                  f"tree pins {stale_locator['eid_star'][:8]}… vs CID {built_cid_eid[:8]}…")

            # (3b) the controls: what DOES catch it.
            fresh = declaration.registered_tree()
            print("\n    what catches it instead:")
            print("      build_tree.py check — rebuilds the locator from T1-EID.json and")
            print("      compares the bytes with the committed tree:")
            res = subprocess.run(
                [sys.executable, "-c",
                 "import sys; sys.path.insert(0, 'a0/a1/kapso_t1'); sys.path.insert(0, '.');"
                 "import json; import build_tree, tree as t1_tree;"
                 f"build_tree.TREE_DIR = __import__('pathlib').Path({str(stale_tree)!r});"
                 "r = build_tree.check();"
                 "print(json.dumps({'locator_rebuild_matches_committed':"
                 " r['locator_rebuild_matches_committed'], 'pass': r['pass']}))"],
                cwd=str(REPO), capture_output=True, text=True)
            print(f"        {res.stdout.strip() or res.stderr.strip()[:200]}")
            consistent = res.returncode != 0 or '"locator_rebuild_matches_committed": false' in res.stdout
            check("build_tree.py check refuses the stale tree (locator bytes do not rebuild)",
                  consistent)
            print("      the registered stub — re-hashes E* on every invocation:")
            stub = subprocess.run(
                [sys.executable, str(stale_tree / "kapso_eval.py"),
                 "--fidelity", "full", "--fraction", "1.0", "--seed", "1337"],
                capture_output=True, text=True, timeout=180)
            print(f"        exit {stub.returncode}; stderr: {stub.stderr.strip().splitlines()[-1][:160] if stub.stderr.strip() else ''}")
            check("the stale stub exits 3 without a manifest line",
                  stub.returncode == 3 and "KAPSO_EVAL_MANIFEST" not in stub.stdout)
        finally:
            declaration.KAPSO_T1_TREE, declaration.KAPSO_T1_BINDING = original_tree, original_binding

    failed = [name for name, ok, _ in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks ok"
          + (f"; FAILED: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
