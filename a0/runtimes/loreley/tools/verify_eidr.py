#!/usr/bin/env python3
"""Independent reconstruction of Loreley's ``EID_r`` from ``EID*``.

The auditor reconstructed EvE's identity by hand and found it was a hash of a
*generated script* rather than structurally derived from ``EID*``.  This tool is
the Loreley answer at the same standard, and it is written to be runnable by
someone who does not trust this adapter:

* it **does not import the adapter** (``a0_adapter``) at all.  The only code it
  reuses is the contract owner's ``a0/contract/evalcontract.py``, which is the
  authority on how an ``EID*`` is formed;
* it recomputes the five component digests and ``EID*`` from the recorded inputs
  alone (``recompute_from_records``, filesystem-free);
* it hashes the plugin source file and the rendered campaign program **as bytes on
  disk** - it does not re-render either - so the two hash inputs are measured, not
  taken on trust;
* it reconstructs ``EID_r.value`` from the native scheme's declared string shape
  and recomputes ``eidr_derivation``;
* it checks the **structural** property directly: every one of the five component
  digests must appear verbatim in the campaign program's bytes.  That is what makes
  ``EID_r`` a function of all five ``EID*`` inputs rather than of whichever ones the
  program's prose happened to mention.

Usage::

    python3 tools/verify_eidr.py \\
        --eid  <EID*.json> \\
        --program <loreley.program.md> \\
        --plugin-source <loreley_a0_plugin.py> \\
        --plugin-ref loreley_a0_plugin:plugin \\
        [--mapping <eidr.mapping.json>] [--json]

Exit 0 when the reconstruction matches, 1 when it does not, 2 on usage/IO error.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

NATIVE_SCHEME = "evaluator_name_version_campaign_program_hash"
EIDR_TEMPLATE = "loreley:v1:{plugin_ref}@source-sha256:{plugin_source}#{program}"
A0 = Path("/home/ebt/rsi-dev/a0")
EVALCONTRACT = A0 / "contract" / "evalcontract.py"


def load_evalcontract():
    spec = importlib.util.spec_from_file_location("a0_evalcontract", EVALCONTRACT)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise SystemExit(f"cannot load {EVALCONTRACT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def reconstruct(eid_path: Path, program_path: Path, plugin_source: Path,
                plugin_ref: str) -> dict:
    evaluator = load_evalcontract()
    document = json.loads(eid_path.read_text(encoding="utf-8"))

    # 1. the five inputs -> component digests -> EID*, by the authority's own scheme
    recomputed = evaluator.recompute_from_records(document)
    recorded = {
        name: document["components"][name]["digest"] for name in evaluator.COMPONENTS
    }
    digests_match = recomputed["components"] == recorded
    eid_star_matches = recomputed["eid_star"] == document["eid_star"]

    # 2. the two hash inputs, measured as bytes on disk
    plugin_digest = file_sha256(plugin_source)
    program_bytes = program_path.read_bytes()
    program_digest = hashlib.sha256(program_bytes).hexdigest()

    # 3. the native scheme's declared string shape
    value = EIDR_TEMPLATE.format(
        plugin_ref=plugin_ref, plugin_source=plugin_digest, program=program_digest
    )

    # 4. the derivation digest the adapter records, recomputed from first principles
    derivation = hashlib.sha256(
        canonical_json(
            {
                "eid_star": document["eid_star"],
                "plugin_source_sha256": plugin_digest,
                "campaign_program_sha256": program_digest,
                "native_scheme": NATIVE_SCHEME,
            }
        ).encode("utf-8")
    ).hexdigest()

    # 5. the structural check: does every component digest reach the hashed bytes?
    program_text = program_bytes.decode("utf-8", "replace")
    containment = {
        name: digest in program_text for name, digest in recomputed["components"].items()
    }
    eid_star_in_program = document["eid_star"] in program_text

    return {
        "schema": "a0.loreley.eidr_reconstruction/v1",
        "runtime": "loreley",
        "inputs": {
            "eid": str(eid_path),
            "campaign_program": str(program_path),
            "plugin_source": str(plugin_source),
            "plugin_ref": plugin_ref,
        },
        "eid_star_recorded": document["eid_star"],
        "eid_star_recomputed": recomputed["eid_star"],
        "eid_star_matches": eid_star_matches,
        "component_digests_recomputed": recomputed["components"],
        "component_digests_recorded": recorded,
        "component_digests_match": digests_match,
        "plugin_source_sha256": plugin_digest,
        "campaign_program_sha256": program_digest,
        "value": value,
        "eid_r_value_reconstructed": value,
        "eidr_derivation": derivation,
        "structural_containment": containment,
        "structural_containment_all_true": all(containment.values()),
        "eid_star_in_program": eid_star_in_program,
        "note": (
            "the two hash inputs are (a) the plugin source file, i.e. the code that will run, and "
            "(b) the rendered campaign program, whose bytes contain all five EID* component digests "
            "- so EID_r changes whenever any of the five changes (measured in "
            "`a0-loreley eidr`, mutation_test.components)"
        ),
        "checks": {
            "component_digests_match_record": digests_match,
            "eid_star_matches": eid_star_matches,
            "every_component_digest_reaches_the_hashed_program": all(containment.values()),
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="verify_eidr", description=__doc__.splitlines()[0])
    parser.add_argument("--eid", required=True)
    parser.add_argument("--program", required=True)
    parser.add_argument("--plugin-source", required=True)
    parser.add_argument("--plugin-ref", default="loreley_a0_plugin:plugin")
    parser.add_argument("--mapping", default=None,
                        help="the adapter's eidr.mapping.json to compare against")
    parser.add_argument("--json", action="store_true", help="print the full reconstruction")
    args = parser.parse_args(argv)

    eid_path, program_path, plugin_source = (Path(args.eid), Path(args.program),
                                             Path(args.plugin_source))
    for path in (eid_path, program_path, plugin_source):
        if not path.is_file():
            print(f"verify_eidr: {path} does not exist", file=sys.stderr)
            return 2

    result = reconstruct(eid_path, program_path, plugin_source, args.plugin_ref)

    declared_value = None
    declared_derivation = None
    if args.mapping:
        mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
        declared_value = (mapping.get("eid_r") or {}).get("value")
        declared_derivation = mapping.get("eidr_derivation")
    result["declared_eid_r_value"] = declared_value
    result["declared_eidr_derivation"] = declared_derivation
    result["value_matches_declared"] = (
        None if declared_value is None else declared_value == result["value"]
    )
    result["derivation_matches_declared"] = (
        None if declared_derivation is None
        else declared_derivation == result["eidr_derivation"]
    )

    ok = (
        all(result["checks"].values())
        and result["value_matches_declared"] in (True, None)
        and result["derivation_matches_declared"] in (True, None)
        and result["eid_star_in_program"]
    )
    result["reconstruction_ok"] = ok

    # The conformance runner parses stdout and reads `value`; everything else is
    # extra context, so one line of JSON keeps both readers happy.
    print(json.dumps(result if args.json else {
        "value": result["value"],
        "eid_star": result["eid_star_recomputed"],
        "eidr_derivation": result["eidr_derivation"],
        "checks": result["checks"],
        "value_matches_declared": result["value_matches_declared"],
        "derivation_matches_declared": result["derivation_matches_declared"],
        "reconstruction_ok": ok,
    }, sort_keys=not args.json))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
