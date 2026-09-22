"""The three traces must reject malformed events and count failures correctly."""

import copy
import json
import sys
from pathlib import Path

import pytest

CONTRACT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTRACT_DIR))

import trace_validate as tv  # noqa: E402

GOOD = CONTRACT_DIR / "fixtures" / "traces" / "good.jsonl"
OUT_OF_RANGE = CONTRACT_DIR / "fixtures" / "traces" / "out_of_range.jsonl"
METRIC = CONTRACT_DIR / "fixtures" / "sample" / "metric.json"
DECLARED_RANGE = "[0.0, 0.7853981633974483]"


def load_good():
    return [json.loads(line) for line in GOOD.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_stream(tmp_path, events, name="stream.jsonl"):
    path = tmp_path / name
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    return path


def errors_for(events, tmp_path):
    return tv.validate_stream(write_stream(tmp_path, events))[0]


def find(events, event_id):
    return next(e for e in events if e["event_id"] == event_id)


# --------------------------------------------------------------------------
# the good stream
# --------------------------------------------------------------------------


def test_good_stream_is_valid():
    assert tv.validate_stream(GOOD) == (tv.validate_stream(GOOD)[0], tv.validate_stream(GOOD)[1])
    errors, events = tv.validate_stream(GOOD)
    assert errors == []
    assert len(events) == 11
    assert {e["trace"] for e in events} == {"score", "selection", "resource"}
    assert {e["runtime"] for e in events} == {"simpleloop", "kapso", "eve", "loreley"}


def test_failure_stage_counters_count_units_not_lines():
    _, events = tv.validate_stream(GOOD)
    counts = tv.count_failure_stages(events)
    assert counts["resolve_failed"] == 1
    assert counts["comprehension_failed"] == 1
    assert counts["mechanism_mismatch"] == 0
    assert counts["search_failed"] == 0
    assert counts["none"] == 7
    # 11 lines collapse to 9 (run, iteration, candidate) units: the resource
    # line and the score line of the same unit carry the same stage.
    assert sum(counts.values()) == 9


def test_cli_validate_and_stats(tmp_path, capsys):
    assert tv.main(["validate", "--trace", str(GOOD)]) == 0
    assert "valid: 11 event(s)" in capsys.readouterr().out
    assert tv.main(["stats", "--trace", str(GOOD)]) == 0
    out = capsys.readouterr().out
    assert "resolve_failed         1" in out
    assert tv.main(["validate", "--trace", str(tmp_path / "absent.jsonl")]) == 2


# --------------------------------------------------------------------------
# rejection
# --------------------------------------------------------------------------

def _cases():
    score = find(load_good(), "sl-run001-s-i0-c1")
    sel = find(load_good(), "sl-run001-sel-i1")
    res = find(load_good(), "sl-run001-res-i0")
    cases = {}

    def case(name, event, *path, value, drop=False):
        mutated = copy.deepcopy(event)
        node = mutated
        for key in path[:-1]:
            node = node[key]
        if drop:
            del node[path[-1]]
        else:
            node[path[-1]] = value
        cases[name] = mutated

    case("missing_eid_star", score, "eid_star", value=None, drop=True)
    case("bad_eid_star_hex", score, "eid_star", value="not-a-digest")
    case("eid_r_not_derived_from_eid_star", score,
         "eid_r", "derives_from_eid_star", value="0" * 64)
    case("undeclared_theta_default", score, "theta_E", "seed", value=None)
    case("outcome_scalarized_by_e_star", score, "outcome", "fields", "scalar", value=0.56)
    case("synthesized_failure_without_detail", score,
         "evaluator_evidence", value={"status": "synthesized_failure"})
    case("cache_hit_without_source", score, "evaluator_evidence", "status", value="cache_hit")
    case("failure_without_detail", score, "failure_stage", value="resolve_failed")
    case("unknown_failure_stage", score, "failure_stage", value="went_wrong")
    case("unknown_runtime", score, "runtime", value="autogpt")
    case("selection_chooses_unconsidered_candidate", sel,
         "selection", "chosen_candidate_id", value="c9")
    case("concurrency_over_cap", res, "concurrency", "observed_max", value=4)
    case("negative_evaluator_calls", res, "N_evaluatorCalls", value=-1)
    case("unknown_extra_field", score, "notes", value="hello")
    return cases


CASES = _cases()


@pytest.mark.parametrize("name", sorted(CASES))
def test_malformed_event_rejected(name, tmp_path):
    errors = errors_for([CASES[name]], tmp_path)
    assert errors, f"{name} was accepted but should be rejected"


def test_expected_error_kind_per_case(tmp_path):
    expectations = {
        "eid_r_not_derived_from_eid_star": "does not match eid_star",
        "undeclared_theta_default": "defaults_applied",
        "outcome_scalarized_by_e_star": "scalarization is F_r's job",
        "synthesized_failure_without_detail": "requires detail",
        "cache_hit_without_source": "requires cached_from_run_id",
        "selection_chooses_unconsidered_candidate": "not among considered",
        "unknown_failure_stage": "not in the frozen enum",
        "concurrency_over_cap": "exceeds cap",
    }
    by_name = {}
    for name in expectations:
        by_name[name] = " ".join(errors_for([CASES[name]], tmp_path))
    for name, needle in expectations.items():
        assert needle in by_name[name], f"{name}: {by_name[name]!r} does not mention {needle!r}"


# --------------------------------------------------------------------------
# stream-level invariants
# --------------------------------------------------------------------------


def test_malformed_json_line_reported(tmp_path):
    path = tmp_path / "broken.jsonl"
    path.write_text('{"trace":"score"}\n{"trace": \n', encoding="utf-8")
    errors, events = tv.validate_stream(path)
    assert any("not valid JSON" in e and "line 2" in e for e in errors)
    assert len(events) == 1


def test_truncated_last_line_without_newline_flagged(tmp_path):
    path = tmp_path / "truncated.jsonl"
    first = json.dumps(load_good()[0])
    path.write_text(first, encoding="utf-8")
    errors, _ = tv.validate_stream(path)
    assert any("does not end with a newline" in e for e in errors)


def test_duplicate_event_id_rejected(tmp_path):
    events = load_good()
    dup = copy.deepcopy(events[1])
    events.insert(2, dup)
    errors = errors_for(events, tmp_path)
    assert any("duplicate event_id" in e for e in errors)


def test_selection_pointing_at_missing_score_event_rejected(tmp_path):
    events = load_good()
    find(events, "sl-run001-sel-i1")["selection"]["source_score_event_id"] = "nope"
    errors = errors_for(events, tmp_path)
    assert any("has no score event" in e for e in errors)


def test_run_with_two_eid_star_values_rejected(tmp_path):
    events = load_good()
    find(events, "sl-run001-s-i0-c2")["eid_star"] = "b" * 64
    errors = errors_for(events, tmp_path)
    assert any("EID* must be frozen" in e for e in errors)


# --------------------------------------------------------------------------
# the run, not the file, is the validation unit (README section 8)
# --------------------------------------------------------------------------


def split_run(tmp_path, events, run_id="sl-run001"):
    """Write the good fixture out as a real run directory, one file per kind."""
    traces = tmp_path / "run" / "traces"
    traces.mkdir(parents=True)
    for kind in ("score", "selection", "resource"):
        kind_events = [e for e in events if e["trace"] == kind]
        stream = "\n".join(json.dumps(e) for e in kind_events) + "\n"
        (traces / f"simpleloop.{run_id}.{kind}.jsonl").write_text(stream, encoding="utf-8")
    return traces.parent


def test_selection_reference_is_unresolvable_in_a_per_kind_file(tmp_path):
    events = [e for e in load_good() if e["trace"] != "resource"]
    run_dir = split_run(tmp_path, events)
    selection = run_dir / "traces" / "simpleloop.sl-run001.selection.jsonl"
    errors, _ = tv.validate_stream(selection)
    assert any("has no score event in this stream" in e for e in errors)
    assert any("validate-run --run-dir" in e for e in errors)


def test_validate_run_composes_per_kind_files_into_one_stream(tmp_path):
    run_dir = split_run(tmp_path, load_good())
    errors, events = tv.validate_composed(
        [run_dir / "traces" / f"simpleloop.sl-run001.{k}.jsonl"
         for k in ("score", "selection", "resource")])
    assert errors == []
    assert [e["event_seq"] for e in events] == sorted(e["event_seq"] for e in events)
    assert len(events) == 11


def test_validate_run_prefers_the_merged_stream(tmp_path):
    run_dir = split_run(tmp_path, load_good())
    merged = run_dir / "traces" / "simpleloop.sl-run001.all.jsonl"
    merged.write_text("\n".join(json.dumps(e) for e in load_good()) + "\n", encoding="utf-8")
    assert tv.validate_run_dir(run_dir) == 0


def test_validate_run_passes_on_split_files_without_the_merged_stream(tmp_path, capsys):
    run_dir = split_run(tmp_path, load_good())
    assert not (run_dir / "traces" / "simpleloop.sl-run001.all.jsonl").exists()
    assert tv.validate_run_dir(run_dir) == 0
    out = capsys.readouterr().out
    assert "composed from" in out
    assert "[ok ] simpleloop.sl-run001" in out


def test_per_kind_file_carrying_another_kind_is_rejected(tmp_path):
    run_dir = split_run(tmp_path, load_good())
    score = run_dir / "traces" / "simpleloop.sl-run001.score.jsonl"
    selection = run_dir / "traces" / "simpleloop.sl-run001.selection.jsonl"
    selection.write_text(selection.read_text(encoding="utf-8") + score.read_text(encoding="utf-8"),
                         encoding="utf-8")
    assert tv.validate_run_dir(run_dir) == 1
    errors, _ = tv.validate_events_only(selection, expected_kind="selection")
    assert any("must partition the run" in e for e in errors)


def test_duplicate_event_id_across_kind_files_is_rejected_once_merged(tmp_path):
    events = load_good()
    duplicated = copy.deepcopy(find(events, "sl-run001-s-i0-c2"))
    run_dir = split_run(tmp_path, events + [duplicated])
    errors, _ = tv.validate_composed(
        [run_dir / "traces" / f"simpleloop.sl-run001.{k}.jsonl"
         for k in ("score", "selection", "resource")])
    assert any("duplicate event_id" in e for e in errors)


def test_validate_run_dir_reports_no_traces(tmp_path, capsys):
    (tmp_path / "empty").mkdir()
    assert tv.validate_run_dir(tmp_path / "empty") == 2
    assert "no <runtime>.<run_id>.<kind>.jsonl traces" in capsys.readouterr().err


def test_run_components_groups_by_runtime_and_run_id(tmp_path):
    run_dir = split_run(tmp_path, load_good(), run_id="a.b-c1")
    groups = tv.run_components(run_dir / "traces")
    assert list(groups) == [("simpleloop", "a.b-c1")]
    assert set(groups[("simpleloop", "a.b-c1")]) == {"score", "selection", "resource"}


def test_schema_file_is_the_one_under_version_control():
    schema = tv.load_schema()
    assert schema["$id"] == "a0.contract/trace_schema/v1"
    assert schema["$schema"].endswith("2020-12/schema")
    assert set(schema["$defs"]["failureStage"]["enum"]) == set(tv.FAILURE_STAGES)
    assert tv.COUNTED_FAILURES == ("search_failed", "resolve_failed",
                                   "comprehension_failed", "mechanism_mismatch")


# --------------------------------------------------------------------------
# the score is bounded by the metric's declared range (finding D-A1-10)
# --------------------------------------------------------------------------


def metric_definitions(*paths):
    return tv.load_metric_definitions([str(p) for p in paths])


def test_out_of_range_stream_is_rejected_when_the_metric_is_named():
    errors, events = tv.validate_stream(OUT_OF_RANGE, metric_definitions(METRIC))
    assert len(events) == 11
    assert any(f"search_signal 9999 is outside the range {DECLARED_RANGE} "
               f"declared by metric 'coverage'" in e for e in errors)
    assert any("outcome.fields.coverage 9999 is outside the range" in e for e in errors)
    # one message per offence, on each of the seven score lines
    assert sum("search_signal" in e for e in errors) == 7


def test_out_of_range_stream_went_unnoticed_before_the_metric_was_named():
    """The bound is opt-in: without the definition in force nothing can be bounded."""
    errors, _ = tv.validate_stream(OUT_OF_RANGE)
    assert errors == []


def test_the_same_stream_passes_when_its_scores_are_in_range():
    errors, _ = tv.validate_stream(GOOD, metric_definitions(METRIC))
    assert errors == []


def test_a_metric_that_declares_no_range_is_not_given_an_invented_bound(tmp_path, capsys):
    unbounded = tmp_path / "unbounded-metric.json"
    unbounded.write_text(json.dumps({"task": "circle-packing",
                                     "metric": {"name": "coverage", "direction": "maximize"}}),
                         encoding="utf-8")
    assert metric_definitions(unbounded)[0]["range"] is None
    errors, _ = tv.validate_stream(OUT_OF_RANGE, metric_definitions(unbounded))
    assert errors == []
    assert tv.main(["validate", "--trace", str(OUT_OF_RANGE),
                    "--metric", str(unbounded)]) == 0
    assert "valid: 11 event(s)" in capsys.readouterr().out


def test_a_metric_declared_for_another_task_does_not_bind(tmp_path):
    other = tmp_path / "other-task-metric.json"
    other.write_text(json.dumps({"task": "maxcut",
                                 "metric": {"name": "cut_fraction", "direction": "maximize",
                                            "range": [0.0, 1.0]}}), encoding="utf-8")
    errors, _ = tv.validate_stream(OUT_OF_RANGE, metric_definitions(other))
    assert errors == []
    assert metric_definitions(other)[0]["task"] == "maxcut"


def test_a_non_scalar_search_signal_is_not_a_bounded_score():
    """Loreley's multiobjective signal is an archive descriptor, not a score."""
    events = load_good()
    definitions = metric_definitions(METRIC)
    loreley = find(events, "lor-run004-s-i0-c1")
    assert isinstance(loreley["search_signal"], dict)
    assert tv.semantic_errors(loreley, definitions) == []


def test_metric_range_check_survives_the_cli_and_the_run_directory(tmp_path, capsys):
    assert tv.main(["validate", "--trace", str(OUT_OF_RANGE),
                    "--metric", str(METRIC)]) == 1
    out = capsys.readouterr().out
    assert f"search_signal 9999 is outside the range {DECLARED_RANGE}" in out
    assert "14 error(s) in 11 event(s)" in out

    run_dir = split_run(tmp_path, [json.loads(line) for line in
                                   OUT_OF_RANGE.read_text(encoding="utf-8").splitlines()])
    assert tv.validate_run_dir(run_dir, metric_definitions(METRIC)) == 1
    assert "is outside the range" in capsys.readouterr().out
    assert tv.validate_run_dir(run_dir) == 0


def test_malformed_metric_definition_is_refused(tmp_path, capsys):
    missing = tmp_path / "absent.json"
    assert tv.main(["validate", "--trace", str(GOOD), "--metric", str(missing)]) == 2
    assert "no such metric definition file" in capsys.readouterr().err

    broken = tmp_path / "broken-metric.json"
    broken.write_text(json.dumps({"metric": {"name": "coverage", "direction": "maximize",
                                             "range": [1.0, 0.0]}}), encoding="utf-8")
    with pytest.raises(ValueError, match="low > high"):
        metric_definitions(broken)

    unreadable = tmp_path / "not-a-metric.json"
    unreadable.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
    with pytest.raises(ValueError, match="no metric definition"):
        metric_definitions(unreadable)

    assert tv.main(["validate-run", "--run-dir", str(tmp_path / "nothing"),
                    "--metric", str(unreadable)]) == 2
    assert "cannot read metric definition" in capsys.readouterr().err


def test_load_metric_definitions_reads_the_contracts_file():
    (definition,) = metric_definitions(METRIC)
    assert definition["name"] == "coverage"
    assert definition["task"] == "circle-packing"
    assert definition["range"] == (0.0, 0.7853981633974483)
    assert definition["source"] == str(METRIC)
    assert metric_definitions() == []
