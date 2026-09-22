"""Unit invariants for the T1/KAPSO retarget. Standard library only.

    python3 -m pytest a0/a1/kapso_t1/tests -q

The end-to-end claims are the probes' (`probes/dryrun_t1.py`,
`probes/live_t1.py`); what is pinned here is the small number of properties that
would be expensive to notice breaking inside a probe: the tree is a deterministic
function of `T1-EID.json` + C*(T1), the dev materializer cannot smuggle in a
hold-out instance, and the registered stub echoes the class triple it is given and
refuses a tree whose recorded evaluator digest no longer matches the bytes.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO_ROOT = ROOT.parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import task as t1_task  # noqa: E402
import t1_binding  # noqa: E402
import tree as t1_tree  # noqa: E402

SUITE_ROOT = Path(t1_binding.load_config().e_star_dir) / "suite"
STUB = ROOT / "tree" / "kapso_eval.py"
LOCATOR = ROOT / "tree" / "a0_locator.json"


def test_the_locator_is_a_function_of_its_inputs():
    config = t1_binding.load_config()
    eid = t1_binding.load_eid(config)
    candidates = t1_binding.load_candidates(config)
    state_root = Path(config.state_root) / "registered-eval"
    first = t1_tree.build_locator(config, eid, candidates, state_root)
    second = t1_tree.build_locator(config, eid, candidates, state_root)
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_the_committed_tree_matches_its_own_fingerprint():
    manifest, fingerprint, _source = t1_tree.verify_tree_fingerprint(ROOT / "tree")
    record = json.loads((ROOT / "tree_record.json").read_text(encoding="utf-8"))
    assert manifest == record["files"]
    assert fingerprint == record["manifest_fingerprint"]


def test_the_binding_carries_t1_and_the_frozen_evaluator():
    config = t1_binding.load_config()
    eid = t1_binding.load_eid(config)
    candidates = t1_binding.load_candidates(config)
    record = t1_binding.binding_record(config, eid, candidates)
    assert record["task_id"] == "T1-maxcut"
    assert record["eid_star"] == (
        "7ce9e72f36a0d1541431024ea86c5d537b9f66b384ab74e85232810a35b4a5ec"
    )
    assert record["metric"]["name"] == "cut_edges"
    assert record["metric"]["direction"] == "maximize"
    assert record["theta_e_canonical"] == {"seed": 1337, "timeout_s": 10.0}
    assert record["candidate_set"]["candidate_count"] == 21
    assert t1_binding.baseline_candidate(candidates).candidate_id == "c02_ok_low_baseline"


def test_the_declared_abi_is_the_locators_abi():
    locator = json.loads(LOCATOR.read_text(encoding="utf-8"))
    assert locator["candidate_abi"] == t1_task.CANDIDATE_ABI
    assert locator["score_semantics"] == t1_task.SCORE_SEMANTICS
    assert locator["evaluation"]["runtime_measures"] is False


def test_the_dev_materializer_copies_only_dev_and_indexes_every_digest(tmp_path):
    record = t1_task.materialize_dev_graphs(tmp_path / "workspace", SUITE_ROOT)
    assert record["count"] == 24
    index = json.loads(Path(record["index"]).read_text(encoding="utf-8"))
    assert index["visible_to_the_agent"] is True
    assert index["role"] == "dev"
    dev_digests = {row["graph_sha256"] for row in t1_task.instances_by_role(SUITE_ROOT, "dev")}
    assert {member["sha256"] for member in index["members"]} == dev_digests
    assert not ({member["sha256"] for member in index["members"]}
                & set(t1_task.holdout_digests(SUITE_ROOT)))
    for member in index["members"]:
        path = Path(record["dest"]) / member["file"]
        assert t1_task.sha256_file(path) == member["sha256"]


def test_the_holdout_scan_finds_a_renamed_eval_instance(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    evals = t1_task.instances_by_role(SUITE_ROOT, "eval")
    shutil.copyfile(evals[0]["path"], workspace / "harmless_looking_name.json")
    hits = t1_task.scan_for_holdout_bytes(workspace, SUITE_ROOT)
    assert hits and hits[0]["instance"] == f"eval:{evals[0]['graph_id']}"


def test_the_dev_materializer_refuses_a_short_dev_set(tmp_path):
    """A dev role that is not 24 instances is a failure, not a smaller workspace."""
    suite = tmp_path / "suite"
    suite.mkdir()
    rows = t1_task.instances_by_role(SUITE_ROOT, "dev")
    suite.joinpath("manifest.json").write_text(json.dumps({
        "schema": "a0.maxcut.suite.manifest/v1",
        "graphs": [
            {"graph_id": row["graph_id"], "family": row["family"], "stratum": row["stratum"],
             "n": row["n"], "edges": row["edges"], "path": row["relative_path"],
             "graph_sha256": row["graph_sha256"], "role": "dev"}
            for row in rows[:-1]
        ],
    }, sort_keys=True) + "\n", encoding="utf-8")
    (tmp_path / "workspace").mkdir()
    with pytest.raises(RuntimeError):
        t1_task.materialize_dev_graphs(tmp_path / "workspace", suite)


def _run_stub(*args, cwd=None):
    return subprocess.run([sys.executable, str(STUB), *args], capture_output=True,
                          text=True, cwd=cwd, timeout=120)


def _manifest_of(stdout: str):
    for line in stdout.splitlines():
        if line.strip().startswith("KAPSO_EVAL_MANIFEST"):
            return json.loads(line.strip()[len("KAPSO_EVAL_MANIFEST"):])
    return None


def test_the_stub_echoes_the_grant_and_measures_nothing():
    candidate = t1_binding.load_config().candidate_set
    proc = _run_stub("--fidelity", "fast", "--fraction", "0.15", "--seed", "4242",
                     "--candidate", str(Path(candidate).parent / "c02_ok_low_baseline"))
    assert proc.returncode == 0
    manifest = _manifest_of(proc.stdout)
    assert manifest["fidelity"] == "fast"
    assert manifest["fraction"] == 0.15
    assert manifest["seed"] == 4242
    assert manifest["items"] == 1 and manifest["total_items"] == 1
    assert manifest["items_measured"] == 0
    assert manifest["measurement"] == "none"
    assert "score" not in manifest
    assert manifest["candidate_identity"]["in_frozen_set"] is True


def test_the_stub_refuses_a_locator_whose_digests_do_not_match_the_bytes(tmp_path):
    drift_tree = tmp_path / "tree"
    shutil.copytree(ROOT / "tree", drift_tree)
    locator_path = drift_tree / "a0_locator.json"
    locator = json.loads(locator_path.read_text(encoding="utf-8"))
    locator["e_star"]["source_records"][0]["sha256"] = "0" * 64
    locator_path.write_text(json.dumps(locator, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    proc = subprocess.run([sys.executable, str(drift_tree / "kapso_eval.py"),
                           "--fidelity", "full", "--fraction", "1.0", "--seed", "1337"],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 3
    assert "KAPSO_EVAL_MANIFEST" not in proc.stdout
    assert "drifted" in proc.stderr
