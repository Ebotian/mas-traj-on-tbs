#!/usr/bin/env python3
"""Build or verify T1's KAPSO registered evaluation tree.

    python3 a0/a1/kapso_t1/build_tree.py build     # write tree/ and tree_record.json
    python3 a0/a1/kapso_t1/build_tree.py check     # rebuild in memory; compare with the tree on disk

`build` is the only writer. `check` recomputes the locator from `T1-EID.json` +
C*(T1) + the frozen suite and compares the bytes and the fingerprint with what is
committed, so a hand-edited tree is detectable: `EID_r` is a function of those two
files' bytes, and an edit changes it (which is the whole point of fingerprinting it).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import tree as t1_tree  # noqa: E402  (also puts the KAPSO adapter dir on sys.path)
from a0_adapter.common import bootstrap_kapso  # noqa: E402
from t1_binding import (  # noqa: E402
    binding_record,
    baseline_candidate,
    load_candidates,
    load_config,
    load_eid,
    verify_eid,
)

TREE_DIR = HERE / "tree"
RECORD_PATH = HERE / "tree_record.json"
BINDING_PATH = HERE / "binding.json"


def build(write: bool) -> Dict[str, Any]:
    config = load_config()
    bootstrap_kapso(config)
    eid = load_eid(config)
    candidates = load_candidates(config)
    contract = verify_eid(config, eid)
    state_root = Path(config.state_root) / "registered-eval"

    record = t1_tree.install_t1_tree(config, eid, candidates, TREE_DIR, state_root)
    record["eid_mapping"] = t1_tree.mapping_document(record, eid)
    record["binding"] = binding_record(config, eid, candidates)
    record["baseline_candidate"] = baseline_candidate(candidates).candidate_id
    record["eid_contract_verification"] = {
        "verify_returncode": contract["verify"]["returncode"],
        "recompute_returncode": contract["recompute"]["returncode"],
        "verify_stdout": contract["verify"]["stdout"],
        "recompute_stdout": contract["recompute"]["stdout"],
        "spec": contract["spec"],
    }
    record["pass"] = (
        contract["verify"]["returncode"] == 0
        and contract["recompute"]["returncode"] == 0
        and len(candidates) == 21
        and record["files"] == {
            name: t1_tree.sha256_file(TREE_DIR / name) for name in t1_tree.TREE_FILES
        }
    )
    if write:
        RECORD_PATH.write_text(
            json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        BINDING_PATH.write_text(
            json.dumps(t1_tree.binding_document(record, eid, config, candidates),
                       indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return record


def check() -> Dict[str, Any]:
    """Rebuild the locator in memory and compare with the committed tree."""
    config = load_config()
    bootstrap_kapso(config)
    eid = load_eid(config)
    candidates = load_candidates(config)
    fresh = t1_tree.build_locator(config, eid, candidates,
                                  Path(config.state_root) / "registered-eval")
    on_disk_path = TREE_DIR / t1_tree.LOCATOR_NAME
    on_disk = json.loads(on_disk_path.read_text(encoding="utf-8")) if on_disk_path.is_file() else None
    wrapper_source = t1_tree.WRAPPER_SOURCE.read_bytes()
    wrapper_disk = (TREE_DIR / t1_tree.WRAPPER_NAME)
    manifest, fingerprint, fingerprint_source = t1_tree.verify_tree_fingerprint(TREE_DIR)
    record = json.loads(RECORD_PATH.read_text(encoding="utf-8")) if RECORD_PATH.is_file() else {}
    return {
        "schema": "a0.kapso_t1.tree_check/v1",
        "tree_dir": str(TREE_DIR),
        "locator_rebuild_matches_committed": (
            on_disk is not None
            and json.dumps(fresh, indent=2, sort_keys=True) + "\n"
            == on_disk_path.read_text(encoding="utf-8")
        ),
        "wrapper_matches_source": (
            wrapper_disk.is_file() and wrapper_disk.read_bytes() == wrapper_source
        ),
        "files": manifest,
        "manifest_fingerprint": fingerprint,
        "manifest_fingerprint_source": fingerprint_source,
        "recorded_manifest_fingerprint": record.get("manifest_fingerprint"),
        "fingerprint_matches_record": fingerprint == record.get("manifest_fingerprint"),
        "eid_star": eid.eid_star,
        "tree_files": list(t1_tree.TREE_FILES),
        "pass": (
            on_disk is not None
            and fingerprint == record.get("manifest_fingerprint")
            and wrapper_disk.is_file()
            and wrapper_disk.read_bytes() == wrapper_source
            and json.dumps(fresh, indent=2, sort_keys=True) + "\n"
            == on_disk_path.read_text(encoding="utf-8")
        ),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="a0.a1.kapso_t1.build_tree")
    parser.add_argument("command", choices=["build", "check"])
    parser.add_argument("--dry-run", action="store_true",
                        help="build without writing tree_record.json (still writes tree/)")
    args = parser.parse_args(argv)
    if args.command == "build":
        record = build(write=not args.dry_run)
        print(json.dumps({
            "schema": "a0.kapso_t1.tree_build/v1",
            "tree_dir": record["tree_dir"],
            "files": record["files"],
            "eid_star": record["eid_star"],
            "eid_r": record["eid_mapping"]["eid_r"],
            "eid_r_value": record["eid_mapping"]["eid_r_value"],
            "pass": record["pass"],
            "eid_contract_verification": {
                "verify_returncode": record["eid_contract_verification"]["verify_returncode"],
                "recompute_returncode": record["eid_contract_verification"]["recompute_returncode"],
            },
        }, indent=1, sort_keys=True))
        return 0 if record["pass"] else 5
    report = check()
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0 if report["pass"] else 5


if __name__ == "__main__":
    sys.exit(main())
