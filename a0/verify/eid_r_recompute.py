#!/usr/bin/env python3
"""Independent recomputation of each runtime's EID_r, from the published artefact
and the frozen EID* document, without importing any adapter code.

For each runtime the script tries to *reproduce the declared identity itself* and
reports whether that is possible at all (some are only consistency checks).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

A0 = Path("/home/ebt/rsi-dev/a0")
EID_DOC = A0 / "contract/out/plumbing.EID.json"
EID_STAR = json.loads(EID_DOC.read_text())["eid_star"]
AD = A0 / "verify/confrun/out/adapters"


def sha_f(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def canon(obj, ascii_=True):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=ascii_)


def domain_digest(domain: str, payload: str) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + payload.encode("ascii")).hexdigest()


results = {}


def doc(rt):
    return json.loads((AD / f"{rt}.conformance.json").read_text())


# ---------------------------------------------------------------- simpleloop
sl = doc("simpleloop")["eid_r"]
der = sl["derivation"]
mine = domain_digest(der["domain"], canon(der["payload"]))
results["simpleloop"] = {
    "kind": "digest-of-published-canonical-payload",
    "declared": sl["value"], "recomputed": mine, "match": mine == sl["value"],
    "eid_star_in_payload": der["payload"].get("eid_star"),
    "depends_on_eid_star": der["payload"].get("eid_star") == EID_STAR,
    "recipe": f'sha256("{der["domain"]}" + 0x00 + canonical_json(payload))',
}

# ---------------------------------------------------------------- kapso
kp = doc("kapso")["eid_r"]
tree_doc = json.loads((A0 / "conformance/out/adapters/registered_tree.json").read_text())
tree = Path(tree_doc["tree_dir"])
files = tree_doc["files"]
# (a) do the recorded file hashes match the files on disk?
file_ok = {n: sha_f(tree / n) == h for n, h in files.items()}
# (b) can the fingerprint rule be reproduced from the recorded hashes?
cands = {
    "files-map": canon(files),
    "files-map-ascii-false": canon(files, ascii_=False),
    "sorted-vector": canon(sorted(files.values())),
}
found = [k for k, v in cands.items() if hashlib.sha256(v.encode()).hexdigest() == tree_doc["manifest_fingerprint"]]
# (c) fingerprint over the actual tree contents as KAPSO's own rule would see it
myfp = hashlib.sha256(canon({k: sha_f(tree / k) for k in sorted(files)}).encode()).hexdigest()
results["kapso"] = {
    "kind": "native-manifest-fingerprint (no recompute_cmd in the adapter output)",
    "declared": kp["value"],
    "registered_tree_files_match_disk": file_ok,
    "fingerprint_rule_reproduced": bool(found) or myfp == tree_doc["manifest_fingerprint"].replace("manifest:", ""),
    "reproduced_with": found or ("files-map-on-disk" if myfp == tree_doc["manifest_fingerprint"].replace("manifest:", "") else None),
    "my_fingerprint": myfp,
    "recorded_fingerprint": tree_doc["manifest_fingerprint"],
    "recompute_mode_in_runner": "cross_checked_against_attempts (runner did not recompute)",
}

# ---------------------------------------------------------------- eve
ev = doc("eve")["eid_r"]
step = Path("/home/ebt/rsi-dev/a0/runtimes/eve/out/conf-a0-eve-run001/evaluator/eve_evaluator_step.sh")
step_sha = sha_f(step)
step_text = step.read_text()
results["eve"] = {
    "kind": "sha256 of the adapter-generated evaluation step script",
    "declared": ev["value"],
    "recomputed": f"sha256:{step_sha}",
    "match": ev["value"] == f"sha256:{step_sha}",
    "step_script_contains_eid_star": EID_STAR in step_text,
    "eid_r_independent_of_EID_star_by_construction": True,
    "note": ("EvE's EID_r digests the script the adapter itself wrote. It is a self-consistency "
             "check on that artefact, not a recomputation of a derivation from EID*. The step "
             "script does embed EID_STAR, but nothing in the recompute proves it had to."),
}

# ---------------------------------------------------------------- loreley
lo = doc("loreley")["eid_r"]
nat = lo["native_components"]
plug = A0 / "runtimes/loreley/src/loreley_a0_plugin.py"
prog = A0 / "runtimes/loreley/out/conformance/loreley.program.md"
ps, cs = sha_f(plug), sha_f(prog)
value = f"loreley:v1:{nat['evaluator_name']}@source-sha256:{ps}#{cs}"
deriv = hashlib.sha256(canon({
    "eid_star": EID_STAR,
    "plugin_source_sha256": ps,
    "campaign_program_sha256": cs,
    "native_scheme": lo["native_scheme"],
}, ascii_=False).encode()).hexdigest()
results["loreley"] = {
    "kind": "native triple + published derivation recipe, recomputed by hand",
    "declared_value": lo["value"], "recomputed_value": value, "value_match": value == lo["value"],
    "declared_plugin_sha": nat["plugin_source_sha256"], "ondisk_plugin_sha": ps,
    "declared_program_sha": nat["campaign_program_sha256"], "ondisk_program_sha": cs,
    "declared_eidr_derivation": lo["eidr_derivation"], "recomputed_eidr_derivation": deriv,
    "derivation_match": deriv == lo["eidr_derivation"],
    "recipe_used": 'sha256(canonical_json({eid_star,plugin_source_sha256,campaign_program_sha256,native_scheme}, ensure_ascii=False))',
}

# ---------------------------------------------------------------- the mislabel probe
kp_theta = doc("kapso").get("theta_e") or {}
kpextra = (kp_theta.get("extra") or {})
results["kapso_theta_e_label_probe"] = {
    "theta_e.extra.evaluator_source_sha256": kpextra.get("evaluator_source_sha256"),
    "E*'s real evaluator_source_sha256": "5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532",
    "is_the_adapter_wrapper_kapso_eval_py_hash": kpextra.get("evaluator_source_sha256") == files.get("kapso_eval.py"),
    "verdict": ("MISLABEL" if kpextra.get("evaluator_source_sha256") !=
                "5ae97ad915dc5a806238c72cfb72a7220d2279a928e61ee20748292f2c975532"
                else "ok"),
}

print(json.dumps(results, indent=2))
(A0 / "verify/out/eid_r_recompute.json").write_text(json.dumps(results, indent=2))
