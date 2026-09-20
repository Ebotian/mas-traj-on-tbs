"""Unit tests for C* integrity, the E* lane's wiring check, and trace emission."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from a0_adapter.candidates import CandidateSetError, load_candidate_set, sha256_file
from a0_adapter.estareval import EvaluatorWiringError, EStarEvaluator
from a0_adapter.policy import PolicyError, load_policy
from a0_adapter.traces import TraceWriter

WORK_ROOT = Path("/home/ebt/rsi-dev")
C_STAR = WORK_ROOT / "a0/tasks/circle-packing/C_STAR/manifest.json"
E_STAR = WORK_ROOT / "a0/tasks/circle-packing/e_star.py"
E_STAR_PYTHON = WORK_ROOT / "a0/tasks/circle-packing/.venv/bin/python"
EID = json.loads((WORK_ROOT / "a0/tasks/circle-packing/plumbing.EID.proposed.json").read_text())
EID_STAR = EID["eid_star"]
SOURCE_RECORDS = EID["components"]["EvaluatorSource"]["records"]

pytestmark = pytest.mark.skipif(not E_STAR.exists(), reason="E* not present")


def test_candidate_set_loads_and_verifies_every_member():
    cset = load_candidate_set(C_STAR)
    assert cset.set_id == "C*"
    assert len(cset.candidates) == 14
    for candidate in cset.candidates:
        assert sha256_file(candidate.path / "solution.py") == candidate.solution_sha256
    assert cset.baseline().candidate_id == "c02_baseline_upstream"


def test_tampered_candidate_aborts_before_evaluation(tmp_path):
    cset = load_candidate_set(C_STAR)
    copy = tmp_path / "C_STAR"
    shutil.copytree(C_STAR.parent, copy)
    victim = copy / "c01_good_hex" / "solution.py"
    victim.write_text(victim.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    with pytest.raises(CandidateSetError, match="sha256 mismatch"):
        load_candidate_set(copy / "manifest.json")


def test_evaluator_wiring_check_detects_source_drift(tmp_path):
    fake = tmp_path / "e_star.py"
    fake.write_text("# not the frozen evaluator\n", encoding="utf-8")
    evaluator = EStarEvaluator(
        python=E_STAR_PYTHON, script=fake, state_dir=tmp_path / "state", out_dir=tmp_path / "out",
        seed=1337, fidelity="full", fraction=1.0,
        expected_source_records=SOURCE_RECORDS,
    )
    with pytest.raises(EvaluatorWiringError):
        evaluator.verify_wiring()


def test_frozen_evaluator_passes_the_wiring_check(tmp_path):
    evaluator = EStarEvaluator(
        python=E_STAR_PYTHON, script=E_STAR, state_dir=tmp_path / "state", out_dir=tmp_path / "out",
        seed=1337, fidelity="full", fraction=1.0, expected_source_records=SOURCE_RECORDS,
    )
    identity = evaluator.verify_wiring()
    assert identity.source_verified is True
    assert identity.interpreter_version.startswith("3.12")


def test_e_star_verdicts_reach_the_lane_as_exit_codes_and_nulls(tmp_path):
    cset = load_candidate_set(C_STAR)
    evaluator = EStarEvaluator(
        python=E_STAR_PYTHON, script=E_STAR, state_dir=tmp_path / "state", out_dir=tmp_path / "out",
        seed=1337, fidelity="full", fraction=1.0, expected_source_records=SOURCE_RECORDS,
    )
    evaluator.verify_wiring()
    ok = evaluator.evaluate(cset.by_id("c01_good_hex"), iteration=0)
    invalid = evaluator.evaluate(cset.by_id("c05_overlapping"), iteration=1)
    error = evaluator.evaluate(cset.by_id("c09_malformed_import"), iteration=2)
    assert (ok.exit_code, ok.status) == (0, "ok")
    assert (invalid.exit_code, invalid.status) == (2, "invalid")
    assert (error.exit_code, error.status) == (3, "error")
    assert invalid.fields["sum_radii"] is None and error.fields["sum_radii"] is None
    assert invalid.failure_kind == "invalid_configuration"
    assert error.failure_kind == "candidate_import_failed"


def test_trace_writer_event_ids_are_unique_per_stream(tmp_path):
    from a0_adapter.policy import fr_for_events

    writer = TraceWriter(
        run_dir=tmp_path, runtime="simpleloop", run_id="t1", task="circle-packing",
        eid_star=EID_STAR,
        eid_r={"value": "sha256:x", "native_scheme": "none",
               "mapping_mode": "adapter_declared_injection",
               "derives_from_eid_star": EID_STAR, "declaration": "d", "recomputable": True},
        theta_E={"seed": 1337, "fidelity": "full", "fraction": 1.0, "defaults_applied": {}},
        policy=load_policy(),
    )
    ids = []
    for i in range(3):
        ids.append(writer.score(iteration=i, candidate_id="c1", parent_id=None,
                                outcome={"status": "ok", "fields": {"sum_radii": 1.0}},
                                fields={"sum_radii": 1.0}, search_signal=1.0,
                                evaluator_evidence={"status": "ok", "detail": None},
                                fr=fr_for_events(load_policy()), failure_stage="none"))
        ids.append(writer.resource(iteration=i, candidate_id="c1", parent_id=None,
                                   T_wall={"value_sec": 0.1, "clock": "monotonic", "scope": "iteration"},
                                   N_evaluatorCalls=i + 1, concurrency={"cap": 1, "observed_max": 1}))
    writer.close()
    assert len(ids) == len(set(ids))


def test_failure_stage_without_detail_is_refused(tmp_path):
    from a0_adapter.policy import fr_for_events

    writer = TraceWriter(
        run_dir=tmp_path, runtime="simpleloop", run_id="t2", task="circle-packing",
        eid_star=EID_STAR,
        eid_r={"value": "sha256:x", "native_scheme": "none",
               "mapping_mode": "adapter_declared_injection",
               "derives_from_eid_star": EID_STAR, "declaration": "d", "recomputable": True},
        theta_E={"seed": 1337, "fidelity": "full", "fraction": 1.0, "defaults_applied": {}},
        policy=load_policy(),
    )
    with pytest.raises(PolicyError):
        writer.score(iteration=0, candidate_id="c1", parent_id=None, outcome=None,
                     fields={"sum_radii": None}, search_signal=None,
                     evaluator_evidence={"status": "ok", "detail": None},
                     fr=fr_for_events(load_policy()), failure_stage="evaluator_failed")
    writer.close()


def test_eid_r_is_recomputable_without_the_adapter_module():
    """The `recomputable: true` claim, executed: sha256(domain || 0x00 || payload).

    A third party recomputes the value from the published (domain, payload_canonical)
    with their own sha256 and no code of ours. This pins the two ways that could
    silently rot: a declaration that outruns the implementation, and a display prefix
    that an independent recomputation cannot reproduce.
    """
    import hashlib

    from a0_adapter.eidmap import EID_R_DOMAIN, EidContext, eid_r_derivation
    from a0_adapter.policy import canonical_bytes, load_policy

    policy = load_policy()
    eid_r = {
        "value": "placeholder",
        "native_scheme": "none",
        "mapping_mode": "adapter_declared_injection",
        "derives_from_eid_star": EID_STAR,
        "declaration": "d",
        "recomputable": True,
    }
    del eid_r
    derivation = eid_r_derivation(eid_star=EID_STAR, source_records=SOURCE_RECORDS, policy=policy)
    recomputed = hashlib.sha256(
        derivation["domain"].encode("ascii") + b"\x00" + derivation["payload_canonical"].encode("ascii")
    ).hexdigest()
    assert derivation["domain"] == EID_R_DOMAIN
    assert canonical_bytes(derivation["payload"]).decode("ascii") == derivation["payload_canonical"]

    context = EidContext(
        document={}, eid_star=EID_STAR, document_path=Path("/dev/null"), spec_path=None,
        epsilon=1e-9, primary_field="sum_radii", source_records=SOURCE_RECORDS,
        evaluator_source_digest=None, verify_stdout="", verify_returncode=0,
        recompute_stdout="", recompute_returncode=0,
    )
    declared = context.eid_r(policy)
    assert declared["value"] == recomputed, "the declared value must be the recomputable digest"
    assert ":" not in declared["value"], "bare hex: an independent recomputation cannot guess a prefix"
    assert sorted(declared) == ["declaration", "derives_from_eid_star", "mapping_mode",
                               "native_scheme", "recomputable", "value"]


def test_codex_tokens_footer_is_parsed_but_never_forced_into_T_in():
    """`secondary` has four fixed keys; the CLI reports one total, so the total goes
    to run_meta and T_in/T_out stay null rather than mislabelling it."""
    from a0_adapter.solvers import _parse_tokens_used

    assert _parse_tokens_used("codex\nblah\ntokens used\n59,147\n") == 59147
    assert _parse_tokens_used("no footer here") is None
    assert _parse_tokens_used("tokens used\n") is None
