"""A-1 acceptance tests: the five component hashes and EID* are recomputable,
and any single input change yields a new EID*."""

import ast
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CONTRACT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTRACT_DIR))

import evalcontract as ec  # noqa: E402

FIXTURE = CONTRACT_DIR / "fixtures" / "sample"
SPEC = FIXTURE / "contract.json"

# Frozen golden value: pins the canonical serialization so that any accidental
# change to what is hashed breaks this test instead of silently redefining EID*.
GOLDEN_EID_STAR = "22c643f821b5bcb7553db636dae9466778d8153ba14f0c37e943e8833e8b22a3"


def test_fixture_eid_star_is_frozen():
    assert build()["eid_star"] == GOLDEN_EID_STAR


def build(spec_path=SPEC, base=None):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    return ec.build_contract(spec, Path(spec_path), base)


def copy_fixture(tmp_path, name="sample"):
    dst = tmp_path / name
    shutil.copytree(FIXTURE, dst)
    return dst


# --------------------------------------------------------------------------
# recomputability
# --------------------------------------------------------------------------


def test_components_and_eid_are_recomputable_from_recorded_inputs():
    doc = build()
    recomputed = ec.recompute_from_records(doc)
    assert recomputed["components"] == {c: doc["components"][c]["digest"] for c in ec.COMPONENTS}
    assert recomputed["eid_star"] == doc["eid_star"]


def test_recompute_needs_no_filesystem(tmp_path, monkeypatch):
    doc = build()
    monkeypatch.chdir(tmp_path)
    doc["components"]["EvaluatorSource"]["root"] = "nonexistent/tree"
    recomputed = ec.recompute_from_records(doc)
    assert recomputed["components"]["EvaluatorSource"] == \
        ec.component_digest("EvaluatorSource",
                            {"root": "nonexistent/tree",
                             "records": doc["components"]["EvaluatorSource"]["records"]})


def test_same_logical_input_same_digest_across_paths_and_times(tmp_path):
    original = build()
    other = copy_fixture(tmp_path, "some/other/place")
    for path in other.rglob("*"):
        if path.is_file():
            os.utime(path, (1_000_000, 1_000_000))
    clone = build(other / "contract.json")
    assert clone["eid_star"] == original["eid_star"]
    assert clone["components"]["EvaluatorSource"]["records"] == \
        original["components"]["EvaluatorSource"]["records"]
    assert str(tmp_path) not in clone["eid_star_derivation"]["payload_canonical"]


def test_document_contains_no_absolute_paths():
    doc = build()
    text = json.dumps(doc, sort_keys=True)
    assert "/home/" not in text
    assert str(CONTRACT_DIR) not in text


# --------------------------------------------------------------------------
# single-input sensitivity
# --------------------------------------------------------------------------

MUTATIONS = {
    "EvaluatorSource": ("evaluator/evaluator.py", lambda s: s.replace("packed = min(n", "packed = max(n")),
    "DependencyLock": ("requirements.txt", lambda s: s.replace("numpy==2.3.3", "numpy==2.3.4")),
    "DataManifest": ("data/candidates.json", lambda s: s.replace('"c1"', '"c1-renamed"')),
    "MetricDefinition": ("metric.json", lambda s: s.replace('"maximize"', '"minimize"')),
}


@pytest.mark.parametrize("component", list(MUTATIONS))
def test_single_file_input_changes_only_its_component(tmp_path, component):
    rel, mutate = MUTATIONS[component]
    root = copy_fixture(tmp_path, component)
    target = root / rel
    mutated = mutate(target.read_text(encoding="utf-8"))
    assert mutated != target.read_text(encoding="utf-8"), "mutation was a no-op"
    target.write_text(mutated, encoding="utf-8")

    before, after = build(), build(root / "contract.json")
    changed = {c for c in ec.COMPONENTS
               if before["components"][c]["digest"] != after["components"][c]["digest"]}
    assert changed == {component}, f"expected only {component} to change, got {changed}"
    assert before["eid_star"] != after["eid_star"]


def test_config_value_change_changes_only_config():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    before = ec.build_contract(spec, SPEC)
    mutated = copy.deepcopy(spec)
    mutated["components"]["Config"]["value"]["theta_E_defaults"]["seed"] = 1338
    after = ec.build_contract(mutated, SPEC)
    changed = {c for c in ec.COMPONENTS
               if before["components"][c]["digest"] != after["components"][c]["digest"]}
    assert changed == {"Config"}
    assert before["eid_star"] != after["eid_star"]


def test_eid_star_covers_all_five_positions():
    doc = build()
    digests = {c: doc["components"][c]["digest"] for c in ec.COMPONENTS}
    base = ec.combined_eid_star(digests)
    assert base == doc["eid_star"]
    for a in ec.COMPONENTS:
        for b in ec.COMPONENTS:
            if a >= b:
                continue
            swapped = dict(digests)
            swapped[a], swapped[b] = swapped[b], swapped[a]
            assert ec.combined_eid_star(swapped) != base, f"{a}/{b} not distinguished"


# --------------------------------------------------------------------------
# rejection of non-portable or malformed input
# --------------------------------------------------------------------------


def test_absolute_path_in_config_rejected():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    spec["components"]["Config"]["value"]["evaluator_root"] = "/home/ebt/evaluator"
    with pytest.raises(ec.ContractError, match="absolute path"):
        ec.build_contract(spec, SPEC)


def test_absolute_symlink_rejected(tmp_path):
    root = copy_fixture(tmp_path, "sym")
    os.symlink("/etc/hostname", root / "evaluator" / "escape.py")
    with pytest.raises(ec.ContractError, match="symlink escapes"):
        build(root / "contract.json")


def test_missing_declared_input_rejected(tmp_path):
    root = copy_fixture(tmp_path, "gap")
    (root / "data" / "candidates.json").unlink()
    with pytest.raises(ec.ContractError, match="DataManifest file missing"):
        build(root / "contract.json")


def test_missing_component_rejected():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    del spec["components"]["MetricDefinition"]
    with pytest.raises(ec.ContractError, match="omits components"):
        ec.build_contract(spec, SPEC)


def test_nonfinite_number_rejected():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    spec["components"]["Config"]["value"]["epsilon"] = float("inf")
    with pytest.raises(ec.ContractError, match="not canonicalizable"):
        ec.build_contract(spec, SPEC)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def test_cli_compute_then_recompute_then_verify(tmp_path, capsys):
    root = copy_fixture(tmp_path, "cli")
    out = root / "EID.json"
    assert ec.main(["compute", "--spec", str(root / "contract.json"), "--out", str(out)]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["eid_star"] == build()["eid_star"]
    assert ec.main(["recompute", "--eid-file", str(out)]) == 0
    assert ec.main(["verify", "--eid-file", str(out)]) == 0
    capsys.readouterr()


def test_cli_verify_detects_drift(tmp_path, capsys):
    root = copy_fixture(tmp_path, "drift")
    out = root / "EID.json"
    assert ec.main(["compute", "--spec", str(root / "contract.json"), "--out", str(out)]) == 0
    (root / "evaluator" / "evaluator.py").write_text("# changed\n", encoding="utf-8")
    assert ec.main(["verify", "--eid-file", str(out)]) == 1
    captured = capsys.readouterr().out
    assert "DRIFT" in captured
    assert "content changed evaluator/evaluator.py" in captured


def test_cli_reports_contract_error_as_exit_2(tmp_path, capsys):
    assert ec.main(["compute", "--spec", str(tmp_path / "absent.json")]) == 2
    assert "contract error" in capsys.readouterr().err


def test_fr_declaration_hash_is_pinned():
    assert ec.canonical_file_digest(CONTRACT_DIR / "fr" / "scalar.json") == \
        "1fa6f941262ac52cc3aab5e5f17d055e9407d01bc558e2b83c409fea1af358d0"


def test_simpleloop_selection_declaration_hash_is_pinned():
    path = CONTRACT_DIR / "selection" / "simpleloop.selection.json"
    assert ec.canonical_file_digest(path) == \
        "ca995f95d41fbf6330289ca59dcf00cc242a419f1fc9f0fc27ad920c78c721cd"
    policy = json.loads(path.read_text(encoding="utf-8"))
    assert policy["status"] == "frozen-a0-contract"
    assert policy["selection"]["tie_break"].startswith("smallest candidate_id by byte-wise")
    assert "0.0 or to -inf" in policy["scalarization"]["null_is_not_zero"]
    assert policy["failure_stage_mapping"]["exit_2_invalid"] == "verify_failed"


# --------------------------------------------------------------------------
# the A0-wide selection blocks (adapter_contract.md section 5.3)
# --------------------------------------------------------------------------

SELECTION_DIR = CONTRACT_DIR / "selection"
SHARED_BLOCK_DIGESTS = {
    "scalarization": "d59f09309b61be515935c8faf72f77f5b66162f5c1375e2eb8ca16934c149b3c",
    "failure_stage_mapping": "201fed78b72587786fcafcc0a0caf9b2a1e65705b7f58e1cdd1c914436ef318f",
}
FROZEN_DECLARATIONS = {
    "simpleloop": "ca995f95d41fbf6330289ca59dcf00cc242a419f1fc9f0fc27ad920c78c721cd",
    "kapso": "c1a993650b4edc4e7a0a799d12d2f6f74e7927b364021dd454454b6e22fc4d6c",
    "eve": "1d4a30d546ba3224b4ff9dff61bfad1b60a4730669281ba07f4ad8a6207783a0",
    "loreley": "94d7139d726b2356d60ff6e32cdb5d8681047c9e84e4fb2a0cd7b2b827864aa1",
}

# The runtime-side originals the frozen copies are taken from. Deliberately not a
# glob: Loreley's lives in a policy/ directory, not a selection/ one.
RUNTIME_SIDE_ORIGINALS = {
    "kapso": "runtimes/kapso/contract/selection/kapso.selection.json",
    "eve": "runtimes/eve/selection/eve.selection.json",
    "loreley": "runtimes/loreley/policy/loreley.selection.json",
}


def _block_digest(block) -> str:
    """sha256(canonical_json(block)) -- the scheme the KAPSO adapter uses."""
    return hashlib.sha256(ec.canonical_json(block)).hexdigest()


@pytest.mark.parametrize("runtime", sorted(FROZEN_DECLARATIONS))
def test_frozen_selection_declaration_digest_is_pinned(runtime):
    path = SELECTION_DIR / f"{runtime}.selection.json"
    assert ec.canonical_file_digest(path) == FROZEN_DECLARATIONS[runtime]


@pytest.mark.parametrize("runtime", sorted(FROZEN_DECLARATIONS))
@pytest.mark.parametrize("block", sorted(SHARED_BLOCK_DIGESTS))
def test_shared_selection_blocks_are_byte_identical_across_frozen_declarations(runtime, block):
    doc = json.loads((SELECTION_DIR / f"{runtime}.selection.json").read_text(encoding="utf-8"))
    assert _block_digest(doc[block]) == SHARED_BLOCK_DIGESTS[block]


def test_kapso_copy_is_admitted_byte_for_byte():
    """The freeze is the recorded digest, so not one byte may be edited."""
    frozen = SELECTION_DIR / "kapso.selection.json"
    if not frozen.exists():
        pytest.skip("kapso declaration not frozen yet")
    origin = (CONTRACT_DIR.parent / "runtimes" / "kapso" / "contract" / "selection"
              / "kapso.selection.json")
    assert frozen.read_bytes() == origin.read_bytes()
    assert json.loads(frozen.read_text(encoding="utf-8"))["status"] == \
        "adopted-by-kapso-workstream"


@pytest.mark.parametrize("runtime", sorted(RUNTIME_SIDE_ORIGINALS))
def test_frozen_copy_is_byte_identical_to_its_runtime_side_original(runtime):
    """Including Loreley's, whose original is under policy/, not selection/."""
    frozen = SELECTION_DIR / f"{runtime}.selection.json"
    origin = CONTRACT_DIR.parent / RUNTIME_SIDE_ORIGINALS[runtime]
    assert origin.exists(), f"runtime-side original missing: {origin}"
    assert frozen.read_bytes() == origin.read_bytes()
    assert json.loads(frozen.read_text(encoding="utf-8"))["status"].startswith("adopted-by-")


def test_all_four_frozen_declarations_agree_on_shared_block_values():
    docs = {r: json.loads((SELECTION_DIR / f"{r}.selection.json").read_text(encoding="utf-8"))
            for r in FROZEN_DECLARATIONS}
    for block in SHARED_BLOCK_DIGESTS:
        forms = {ec.canonical_json(doc[block]) for doc in docs.values()}
        assert len(forms) == 1, f"{block} differs across runtimes"


def test_only_simpleloop_may_omit_a_runtime_specific_stage_block():
    """Every runtime declares its extension cases, even as an empty set (section 5.3.4 Rule 7)."""
    for runtime in ("kapso", "loreley"):
        doc = json.loads((SELECTION_DIR / f"{runtime}.selection.json").read_text(encoding="utf-8"))
        assert f"{runtime}_specific_stages" in doc, runtime
    eve = json.loads((SELECTION_DIR / "eve.selection.json").read_text(encoding="utf-8"))
    if "eve_specific_stages" not in eve:
        pytest.skip("EvE still owes its eve_specific_stages block (section 5.3.4)")


def test_kapso_declares_its_tie_break_divergence():
    frozen = SELECTION_DIR / "kapso.selection.json"
    if not frozen.exists():
        pytest.skip("kapso declaration not frozen yet")
    sel = json.loads(frozen.read_text(encoding="utf-8"))["selection"]
    assert "node_history" in sel["tie_break"]
    assert "MEASURED DIVERGENCE" in sel["tie_break_divergence"]
    # the divergence is demonstrated in both proposal orders, not just asserted
    evidence = sel["tie_break_divergence_evidence"]
    assert evidence["byte_wise_smallest_of_tie_pair"] == "c01_good_hex"
    assert set(evidence) == {"order_agreeing", "order_diverging", "probe",
                             "byte_wise_smallest_of_tie_pair"}
    simple = json.loads((SELECTION_DIR / "simpleloop.selection.json").read_text(encoding="utf-8"))
    assert sel["tie_break"] != simple["selection"]["tie_break"], \
        "the two runtimes' tie-breaks must not be conflated"


def test_kapso_declares_its_runtime_specific_stage():
    """adapter_contract.md section 5.3.3 depends on this being declared, not hard-coded."""
    frozen = SELECTION_DIR / "kapso.selection.json"
    if not frozen.exists():
        pytest.skip("kapso declaration not frozen yet")
    stages = json.loads(frozen.read_text(encoding="utf-8"))["kapso_specific_stages"]
    assert "boundary_violation" in stages
    assert "enforce_evaluation_integrity" in stages["boundary_violation"]
    # a runtime-specific stage must not also be one of the shared-map values
    assert "boundary_violation" not in set(
        json.loads(frozen.read_text(encoding="utf-8"))["failure_stage_mapping"].values())


def test_frozen_expected_stage_counts_over_cstar():
    """adapter_contract.md section 5.3.2 pins these counts; recompute them from E_STAR.json."""
    table = json.loads((CONTRACT_DIR.parent / "tasks" / "circle-packing"
                        / "E_STAR.json").read_text(encoding="utf-8"))
    frozen = json.loads((SELECTION_DIR / "kapso.selection.json").read_text(encoding="utf-8")
                        )["failure_stage_mapping"]
    counts: dict[str, int] = {}
    for candidate in table["candidates"]:
        if candidate["status"] == "ok":
            stage = frozen["exit_0_ok"]
        elif candidate["status"] == "invalid":
            stage = frozen["exit_2_invalid"]
        else:
            stage = frozen["exit_3_error_" + candidate["failure_kind"]]
        counts[stage] = counts.get(stage, 0) + 1
    assert counts == {"none": 5, "verify_failed": 5, "resolve_failed": 1,
                      "evaluator_failed": 2, "timeout": 1}
    assert sum(counts.values()) == 14 == table["candidate_count"]


def test_failure_stage_table_matches_the_frozen_reference_table():
    """adapter_contract.md section 4.5 tabulates nine non-ok rows; check them."""
    table = json.loads((CONTRACT_DIR.parent / "tasks" / "circle-packing"
                        / "E_STAR.json").read_text(encoding="utf-8"))
    frozen = json.loads((SELECTION_DIR / "kapso.selection.json").read_text(encoding="utf-8"))[
        "failure_stage_mapping"]
    for candidate in table["candidates"]:
        if candidate["status"] == "ok":
            continue
        if candidate["status"] == "invalid":
            assert candidate["failure_kind"] == "invalid_configuration"
            key = "exit_2_invalid"
        else:
            key = "exit_3_error_" + candidate["failure_kind"]
        assert key in frozen, f"{candidate['candidate_id']}: no frozen stage for {key}"
        assert key != "exit_3_error_other", f"{candidate['candidate_id']} falls through the table"
    kinds = {c["failure_kind"] for c in table["candidates"] if c["failure_kind"]}
    assert kinds == {"invalid_configuration", "candidate_import_failed", "candidate_call_raised",
                     "non_deterministic", "child_terminated_early", "runtime_budget_exceeded"}


# --------------------------------------------------------------------------
# the plumbing task's own identity (identity arbitration, README section 8)
# --------------------------------------------------------------------------

PLUMBING_SPEC = CONTRACT_DIR / "plumbing.contract.json"
PLUMBING_EID = CONTRACT_DIR / "out" / "plumbing.EID.json"
FROZEN_EID_STAR = "664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328"
FROZEN_COMPONENTS = {
    "EvaluatorSource": "a3d6534b4e3bc78f06587bf0281d44b5ddde6de938eb84d87b646dda995edc29",
    "DependencyLock": "7b02f1a71288335ff92fe68da8804349e416ba4ae9e95f8cd0c6a3b5bc372a75",
    "DataManifest": "b21c975a51ef24cdfb2078957f0e0e4b2fb194e7c55b3a8058febb019d214a21",
    "Config": "550ca3cdd8af04ec0895a2515bbee40a9627b805d5477611995f4cef0f4043ac",
    "MetricDefinition": "420ab0acf24e1c7325b089e2ec4bc6c3d074119c4f3ac8aac8ed3cfa1c45bfc0",
}


def test_plumbing_eid_star_is_pinned():
    """A silent re-freeze of EID* must break the build, not the study."""
    doc = json.loads(PLUMBING_EID.read_text(encoding="utf-8"))
    assert doc["eid_star"] == FROZEN_EID_STAR
    assert {c: doc["components"][c]["digest"] for c in ec.COMPONENTS} == FROZEN_COMPONENTS
    assert doc["task"] == "circle-packing-plumbing"


def test_plumbing_evaluator_source_is_the_frozen_evaluator_not_local_eval():
    doc = json.loads(PLUMBING_EID.read_text(encoding="utf-8"))
    src = doc["components"]["EvaluatorSource"]
    assert src["root"] == "tasks/circle-packing"
    assert sorted(r["path"] for r in src["records"]) == ["e_star.py", "e_star_child.py"]
    assert not any("local_eval" in r["path"] for r in src["records"])


def test_plumbing_config_makes_the_seed_a_genuine_evaluator_input():
    spec = json.loads(PLUMBING_SPEC.read_text(encoding="utf-8"))
    theta = spec["components"]["Config"]["value"]["theta_e_semantics"]
    assert "seed" in theta
    assert "subsample" in theta["seed"]
    canonical = spec["components"]["Config"]["value"]["theta_e_canonical"]
    assert canonical["seed"] == 1337
    assert canonical["fidelity"] == "full"
    assert canonical["fraction"] == 1.0


def test_plumbing_contract_paths_resolve_from_the_contract_directory():
    spec = json.loads(PLUMBING_SPEC.read_text(encoding="utf-8"))
    assert spec["base"] == ".."
    base = ec.resolve_base(spec, PLUMBING_SPEC, None)
    assert base == CONTRACT_DIR.parent
    assert (base / "tasks/circle-packing/C_STAR/manifest.json").exists()
    assert (base / "tasks/circle-packing/e_star.py").exists()


def test_plumbing_contract_recomputes_from_the_recorded_document():
    doc = json.loads(PLUMBING_EID.read_text(encoding="utf-8"))
    recomputed = ec.recompute_from_records(doc)
    assert recomputed["eid_star"] == FROZEN_EID_STAR
    assert recomputed["components"] == FROZEN_COMPONENTS


def test_cli_verify_and_recompute_pass_on_the_frozen_plumbing_document(capsys):
    """A-1 acceptance: the frozen document must survive both CLI checks."""
    rc = ec.main(["recompute", "--eid-file", str(PLUMBING_EID)])
    assert rc == 0
    assert "[BAD]" not in capsys.readouterr().out
    rc = ec.main(["verify", "--eid-file", str(PLUMBING_EID), "--spec", str(PLUMBING_SPEC)])
    assert rc == 0, capsys.readouterr().out
    assert "all recorded inputs match" in capsys.readouterr().out


def test_plumbing_document_matches_the_producing_workstreams_proposal():
    """The circle-packing workstream's independent computation must agree."""
    proposal = CONTRACT_DIR.parent / "tasks" / "circle-packing" / "plumbing.EID.proposed.json"
    if not proposal.exists():
        pytest.skip("producing workstream's proposal is not on disk")
    other = json.loads(proposal.read_text(encoding="utf-8"))
    assert other["eid_star"] == FROZEN_EID_STAR


def test_fr_hash_ignores_formatting_but_not_values(tmp_path):
    source = json.loads((CONTRACT_DIR / "fr" / "scalar.json").read_text(encoding="utf-8"))
    pinned = ec.canonical_file_digest(CONTRACT_DIR / "fr" / "scalar.json")
    reformatted = tmp_path / "reformatted.json"
    reformatted.write_text(json.dumps(source, indent=4, sort_keys=False), encoding="utf-8")
    assert ec.canonical_file_digest(reformatted) == pinned
    source["version"] = "v2"
    edited = tmp_path / "edited.json"
    edited.write_text(json.dumps(source), encoding="utf-8")
    assert ec.canonical_file_digest(edited) != pinned


# --------------------------------------------------------------------------
# runtime agnosticism
# --------------------------------------------------------------------------


def test_no_runtime_specific_imports():
    tree = ast.parse((CONTRACT_DIR / "evalcontract.py").read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    forbidden = {m for m in modules if m.lower() in {"kapso", "eve", "loreley", "kimi"}}
    assert not forbidden, forbidden
    third_party = modules - {"argparse", "functools", "hashlib", "json", "os", "re",
                             "stat", "sys", "tomllib", "pathlib", "__future__"}
    assert not third_party, third_party
