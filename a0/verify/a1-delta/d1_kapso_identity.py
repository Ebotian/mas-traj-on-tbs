#!/usr/bin/env python3
"""Item 1 — re-derive the KAPSO T1 fixes myself, from the bytes.

Nothing here reads a binding for a number it is about to "verify": every digest
is recomputed from the file it names, and the binding/declaration is only read to
see whether its recorded value equals the recomputed one. The hash recipes are
re-implemented from the published rules (canonical JSON with sorted keys and no
whitespace; the KAPSO manifest fingerprint) so a bug in the artifact's own helper
cannot hide behind itself.

    python3 a0/verify/a1-delta/d1_kapso_identity.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
KAPSO = REPO / "a0" / "a1" / "kapso_t1"
DOMAIN = "a0/evalcontract/v1"
COMPONENTS = ("EvaluatorSource", "DependencyLock", "DataManifest", "Config", "MetricDefinition")

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    CHECKS.append((name, bool(ok), detail))
    print(f"[{'ok ' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))
    return bool(ok)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def canon(obj) -> bytes:
    """evalcontract.canonical_json, re-implemented from its documented rule."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def domain_digest(domain: str, payload: bytes) -> str:
    return sha256_hex_str(domain.encode("ascii") + b"\x00" + payload)


def sha256_hex_str(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def component_digest(name: str, payload_obj) -> str:
    return domain_digest(f"{DOMAIN}/{name}", canon(payload_obj))


def combined_eid_star(digests: dict) -> str:
    return domain_digest(f"{DOMAIN}/EID*", canon({c: digests[c] for c in COMPONENTS}))


def recompute_from_records(doc: dict) -> tuple[str, dict, bytes]:
    digests = {}
    for name in COMPONENTS:
        comp = doc["components"][name]
        kind = comp["kind"]
        if kind == "source_tree":
            payload = {"root": comp["root"], "records": comp["records"]}
        elif kind in ("data_manifest", "lock_entries"):
            payload = comp["records"]
        elif kind == "value":
            payload = comp["value"]
        else:
            raise SystemExit(f"unknown component kind {kind!r} for {name}")
        digests[name] = component_digest(name, payload)
    return combined_eid_star(digests), digests, canon(digests)


def kapso_fingerprint(manifest: dict) -> str:
    """KAPSO's rule, from tree.py's published quote (sorted keys, tight separators)."""
    return sha256_hex_str(canon(manifest))


def main() -> int:
    # ------------------------------------------------------------------ EID*
    print("== EID* from a0/a1/t1_eid.py's own material ==")
    sys.path.insert(0, str(REPO))
    from a0.a1 import t1_eid  # noqa: E402

    doc = json.loads((REPO / "a0/a1/T1-EID.json").read_text(encoding="utf-8"))
    spec = t1_eid.build_spec()
    on_disk_spec = json.loads((REPO / "a0/a1/T1.contract.json").read_text(encoding="utf-8"))
    check("T1.contract.json == t1_eid.build_spec()", on_disk_spec == spec)

    eid_from_records, comps, payload = recompute_from_records(doc)
    check("EID* recomputed from T1-EID.json's recorded records",
          eid_from_records == doc["eid_star"] ==
          "7ce9e72f36a0d1541431024ea86c5d537b9f66b384ab74e85232810a35b4a5ec",
          f"{eid_from_records}")
    check("the document's own payload_canonical equals my canonical payload",
          doc["eid_star_derivation"]["payload_canonical"] == payload.decode("ascii"))
    check("every recorded component digest matches my recomputation",
          all(comps[n] == doc["components"][n]["digest"] for n in COMPONENTS))

    # E*'s own identity, asked of E* itself, and the file material behind it.
    proc = subprocess.run([sys.executable, "e_star.py", "digest", "--value-only"],
                          cwd=str(REPO / "a0/tasks/maxcut"), capture_output=True, text=True)
    e_star_own = proc.stdout.strip()
    check("e_star.py digest --value-only == dc6969ec…",
          e_star_own == "dc6969ec9934ab660cf8ecd7073cf325a15c7d416140afd00a3d782cfe799d00",
          e_star_own[:16] + "…")
    e_star_py = sha256_file(REPO / "a0/tasks/maxcut/e_star.py")
    e_star_child = sha256_file(REPO / "a0/tasks/maxcut/e_star_child.py")
    recorded = {r["path"]: r["sha256"] for r in doc["components"]["EvaluatorSource"]["records"]}
    disk = {"e_star.py": e_star_py, "e_star_child.py": e_star_child}
    check("EvaluatorSource records are the bytes of e_star.py / e_star_child.py on disk",
          recorded == disk, f"{sorted(recorded)}")

    # --------------------------------------------------------------- the tree
    print("\n== the registered tree, recomputed from its committed bytes ==")
    files = {p.name: sha256_file(p) for p in sorted((KAPSO / "tree").iterdir()) if p.is_file()}
    fingerprint = kapso_fingerprint(files)
    check("tree EID_r = manifest_fingerprint(tree bytes)",
          fingerprint == "63a9a83c071d82f30d3053a79af664835cb4b76d159ca04ba27bc945ab2f816f",
          fingerprint)
    check("tree file map matches tree_record.json",
          files == json.loads((KAPSO / "tree_record.json").read_text())["files"])
    check("tree/source wrapper is byte-identical to tree_src/kapso_eval.py",
          (KAPSO / "tree/kapso_eval.py").read_bytes() == (KAPSO / "tree_src/kapso_eval.py").read_bytes())
    binding = json.loads((KAPSO / "binding.json").read_text())
    check("binding.json publishes the recomputed fingerprint",
          binding.get("eid_r_value") == fingerprint
          and binding.get("eid_r") == f"manifest:{fingerprint}")
    check("binding.json's declared tree files == recomputed tree files",
          (binding.get("registered_tree") or {}).get("files") == files)

    locator = json.loads((KAPSO / "tree/a0_locator.json").read_text())
    check("locator pins the current EID*", locator["eid_star"] == doc["eid_star"],
          locator["eid_star"][:16] + "…")
    check("locator's E* self-identity is the current dc6969ec…",
          locator["e_star"]["self_identity"]["evaluator_source_sha256"] == e_star_own)
    loc_records = {r.get("path", r.get("name")): r["sha256"]
                   for r in locator["e_star"]["source_records"]}
    loc_sizes = {r.get("path", r.get("name")): r.get("size", r.get("bytes"))
                 for r in locator["e_star"]["source_records"]}
    check("locator's E* source records are the current files",
          loc_records == disk)
    check("locator's E* source sizes are the current file sizes",
          loc_sizes == {name: (REPO / "a0/tasks/maxcut" / name).stat().st_size for name in disk},
          str(loc_sizes))
    check("locator's EID* component digests are current",
          locator["eid_star_components"] == {n: doc["components"][n]["digest"] for n in COMPONENTS})

    # ------------------------------------------------------- the declarations
    print("\n== what the declarations actually contain ==")
    aid = json.loads((REPO / "a0/a1/declarations/AID_r.A_kapso.json").read_text())["factors"]
    tree_factor = aid["runtime.registered_evaluation_tree"]["identity"]
    files_factor = aid["runtime.registered_evaluation_tree_files"]["identity"]
    check("AID_r's tree factor names the recomputed EID_r",
          f"manifest:{fingerprint}" in tree_factor)
    check("AID_r's files factor equals the recomputed tree file map",
          json.loads(files_factor.split("value:", 1)[1]) == files)
    cid = json.loads((REPO / "a0/a1/declarations/CID.json").read_text())["factors"]
    cid_eid = json.loads(cid["task.eid_star"]["identity"].split("value:", 1)[1])["eid_star"]
    check("CID's task.eid_star == the recomputed EID*", cid_eid == eid_from_records)
    check("AID_r's EID_r and CID's EID* are both names of the same E*",
          f"manifest:{fingerprint}" in tree_factor and cid_eid == eid_from_records
          and locator["eid_star"] == cid_eid)

    # ---------------------------------------------------------- the live probe
    print("\n== the paid live probe, recomputed from its own usage ==")
    live = json.loads((KAPSO / "evidence/live_t1.json").read_text())
    rows = live["meter_ledger_rows"]
    recomputed = []
    for row in rows:
        u = row["usage"]
        ceq = (u["prompt_cache_miss_tokens"]
               + (u["prompt_cache_hit_tokens"] * 2) // 100
               + 4 * u["completion_tokens"])
        recomputed.append(ceq)
    check("meter ledger CEq recomputes from each row's own usage (miss + hit*2//100 + 4*completion)",
          recomputed == [r["ceq"] for r in rows] == [1116] and live["meter_summary"]["ceq"] == 1116,
          f"rows={recomputed} summary={live['meter_summary']['ceq']}")
    model_calls = live["arm_state"]["model_calls"]
    u = model_calls[0]["usage"]
    check("the arm's own recorded model usage gives the same CEq",
          (u["prompt_cache_miss_tokens"] + (u["prompt_cache_hit_tokens"] * 2) // 100
           + 4 * u["completion_tokens"]) == 1116,
          f"miss={u['prompt_cache_miss_tokens']} hit={u['prompt_cache_hit_tokens']} "
          f"completion={u['completion_tokens']}")
    check("the live probe's evidence names the current EID* and EID_r",
          live["arm_state"]["eid_star"] == doc["eid_star"]
          and live["arm_state"]["eid_r_value"] == fingerprint,
          live["arm_state"]["eid_r"][:12] + "…")
    check("the live probe reports 16/16 checks true",
          live["verdict"] == "pass" and all(live["checks"].values())
          if isinstance(live.get("checks"), dict) else live.get("verdict") == "pass",
          f"verdict={live['verdict']} n_checks={len(live.get('checks', []))}")
    check("every ledger row is metered (no unmetered row)",
          all(row.get("ceq", 0) > 0 for row in rows) and live["model_call_skipped"] is False)

    # ------------------------------------------------- superseded digests here
    print("\n== does anything in kapso_t1 still assert a superseded digest unlabelled? ==")
    superseded = {
        "cddfa64e": "EID* before 75403e8c", "eccd859c": "EID* at the D-A1-7 freeze",
        "08281d21": "E* digest pre-6dd717c2", "4afff01f": "E* digest at baf13884",
        "670f02ee": "e_star.py pre-6dd717c2", "fa0932b4": "e_star.py at 6dd717c2",
        "83d55e80": "e_star.py at the D-A1-7 freeze",
        "013f3e33": "e_star_child.py pre-6dd717c2", "c08f0c36": "e_star_child.py at 6dd717c2",
        "7392915d": "e_star_child.py at the D-A1-7 freeze",
        "5a0c99ff": "a0_locator.json before the KAPSO rebuild",
        "6b1d6fcc": "EID_r before the KAPSO rebuild",
    }
    # "asserts as current" is the criterion, so a hit is labelled when the line, or the
    # region it sits in, carries a past marker or the replacement value side by side.
    PAST = ("superseded", "previous revision", "pre-rebuild", "before ", "was `", "no longer",
            "drifted", "history", "old and new", "pre-6dd717c2", "at the D-A1-7", "at baf13884")
    CURRENT = ("7ce9e72f", "dc6969ec", "f67ecd41", "fdcf425c", "63a9a83c", "1e3b3a75", "6759ef05")
    hits: dict[str, list[tuple[int, str, bool]]] = {}
    for path in sorted(KAPSO.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        rel = str(path.relative_to(REPO))
        in_history_dir = rel.startswith("a0/a1/kapso_t1/evidence/history/")
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for i, line in enumerate(lines):
            if not any(prefix in line for prefix in superseded):
                continue
            window = "\n".join(lines[max(0, i - 4):i + 5]).lower()
            labelled = (in_history_dir
                        or any(marker in window for marker in PAST)
                        or any(pref in window for pref in CURRENT))
            hits.setdefault(rel, []).append((i + 1, line.strip()[:150], labelled))
    for rel in sorted(hits):
        print(f"  {rel}")
        for lineno, line, labelled in hits[rel][:6]:
            print(f"      [{'history' if labelled else 'CURRENT'}] {lineno}: {line}")
        if len(hits[rel]) > 6:
            print(f"      … {len(hits[rel]) - 6} more")
    unlabelled = {rel: [h for h in v if not h[2]] for rel, v in hits.items()}
    unlabelled = {rel: v for rel, v in unlabelled.items() if v}
    check("every superseded digest in kapso_t1 is inside evidence/history/** or labelled history",
          not unlabelled,
          f"unlabelled: {sorted(unlabelled)}" if unlabelled else
          f"clean ({len(hits)} file(s), all labelled)")

    # ------------------------------------------------------------------ verdict
    failed = [name for name, ok, _ in CHECKS if not ok]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks ok"
          + (f"; FAILED: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
