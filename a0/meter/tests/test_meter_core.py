"""Unit tests for the pure core: the frozen arithmetic, the three usage shapes, and the ledger.

These run without a socket, so they are the fast layer. The end-to-end behaviour (allowlist,
streaming, attribution, fail-closed) lives in `test_meter_e2e.py`.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from meter_core import (  # noqa: E402
    ROW_KEY_ORDER,
    Ledger,
    LedgerError,
    Usage,
    build_row,
    ceq,
    normalize_usage,
    parse_sse_events,
    usage_has_tokens,
    verify_row,
)


class TestCeqArithmetic:
    def test_zero(self):
        assert ceq(0, 0, 0) == 0

    def test_completion_weighs_four(self):
        assert ceq(0, 0, 7) == 28

    def test_hit_is_floored_at_two_percent(self):
        # 99 hits -> floor(99*2/100) = 1, not 1.98 and not 2.
        assert ceq(0, 99, 0) == 1
        assert ceq(0, 100, 0) == 2
        assert ceq(0, 1, 0) == 0

    def test_mixed(self):
        assert ceq(10240, 1280, 312) == 10240 + 25 + 1248

    def test_never_float(self):
        value = ceq(10240, 1280, 312)
        assert isinstance(value, int) and not isinstance(value, bool)

    @pytest.mark.parametrize("bad", [-1, -100])
    def test_negative_is_rejected(self, bad):
        with pytest.raises(ValueError):
            ceq(bad, 0, 0)

    def test_non_integer_is_rejected(self):
        with pytest.raises(TypeError):
            ceq(1.5, 0, 0)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            ceq(True, 0, 0)

    def test_usage_ceq_matches_free_function(self):
        usage = Usage(1280, 10240, 312)
        assert usage.ceq() == ceq(10240, 1280, 312)


class TestNormalization:
    def test_deepseek_native_chat_completions(self):
        out = normalize_usage({"prompt_cache_hit_tokens": 1280, "prompt_cache_miss_tokens": 10240,
                               "completion_tokens": 312, "prompt_tokens": 11520})
        assert out.usage == Usage(1280, 10240, 312)
        assert out.source == "openai_chat_native"
        assert out.unmetered_reason is None

    def test_completion_tokens_alone_is_not_the_native_shape(self):
        # `completion_tokens` is shared with the generic OpenAI shape, so it must not, by itself,
        # select the native branch -- otherwise a generic response would look like a partial
        # native one and be reported with the wrong reason.
        out = normalize_usage({"prompt_tokens": 1000, "completion_tokens": 10,
                               "prompt_tokens_details": {"cached_tokens": 400}})
        assert out.usage == Usage(400, 600, 10)
        assert out.source == "openai_generic"

    def test_anthropic_cache_read_is_the_hit_and_cache_write_is_a_miss(self):
        out = normalize_usage({"input_tokens": 120, "output_tokens": 55,
                               "cache_read_input_tokens": 2048,
                               "cache_creation_input_tokens": 64}, anthropic_route=True)
        assert out.usage == Usage(2048, 184, 55)
        assert out.source == "anthropic_messages"

    def test_anthropic_omitted_cache_fields_mean_zero_reads_on_that_route(self):
        out = normalize_usage({"input_tokens": 120, "output_tokens": 55}, anthropic_route=True)
        assert out.usage == Usage(0, 120, 55)

    def test_omitted_cache_fields_off_the_anthropic_route_is_a_gap(self):
        out = normalize_usage({"input_tokens": 120, "output_tokens": 55})
        assert out.usage is None
        assert out.unmetered_reason == "usage_present_without_cache_split"

    def test_openai_responses_uses_input_tokens_details(self):
        out = normalize_usage({"input_tokens": 4000, "output_tokens": 200,
                               "input_tokens_details": {"cached_tokens": 1500}})
        assert out.usage == Usage(1500, 2500, 200)
        assert out.source == "openai_responses"

    def test_missing_cache_split_is_unmetered_by_default(self):
        out = normalize_usage({"prompt_tokens": 1000, "completion_tokens": 10})
        assert out.usage is None
        assert out.unmetered_reason == "usage_present_without_cache_split"

    def test_missing_cache_split_can_be_charged_conservatively(self):
        out = normalize_usage({"prompt_tokens": 1000, "completion_tokens": 10},
                              on_missing_cache_split="conservative-miss")
        assert out.usage == Usage(0, 1000, 10)

    def test_empty_usage_is_a_named_gap(self):
        out = normalize_usage({})
        assert out.usage is None
        assert out.unmetered_reason == "no_recognizable_usage_fields"

    def test_negative_field_is_rejected_rather_than_credited(self):
        out = normalize_usage({"prompt_cache_hit_tokens": -1, "prompt_cache_miss_tokens": 5,
                               "completion_tokens": 1})
        assert out.usage is None
        assert out.unmetered_reason == "inconsistent_usage_negative_field"

    def test_usage_has_tokens_distinguishes_null_from_real(self):
        assert not usage_has_tokens({})
        assert not usage_has_tokens({"prompt_tokens": None})
        assert usage_has_tokens({"prompt_tokens": 0})


class TestSSEParsing:
    def test_splits_events_and_marks_the_terminator(self):
        buf = bytearray(b'data: {"a":1}\n\ndata: [DONE]\n\n')
        events, pos = parse_sse_events(buf, 0)
        assert len(events) == 2
        assert events[0].data == b'{"a":1}'
        assert events[1].is_terminator
        assert pos == len(buf)

    def test_crlf_events_and_named_terminators(self):
        buf = bytearray(b'event: message_stop\r\ndata: {"type":"message_stop"}\r\n\r\n')
        events, _ = parse_sse_events(buf, 0)
        assert events[0].name == "message_stop"
        assert events[0].is_terminator

    def test_response_completed_is_a_terminator_for_the_responses_api(self):
        buf = bytearray(b'event: response.completed\ndata: {"type":"response.completed"}\n\n')
        events, _ = parse_sse_events(buf, 0)
        assert events[0].is_terminator

    def test_incomplete_trailing_event_is_left_for_the_next_call(self):
        buf = bytearray(b'data: {"a":1}\n\ndata: {"b":')
        events, pos = parse_sse_events(buf, 0)
        assert len(events) == 1
        assert pos == len(b'data: {"a":1}\n\n')
        buf += b'2}\n\n'
        events2, pos2 = parse_sse_events(buf, pos)
        assert [e.data for e in events2] == [b'{"b":2}']
        assert pos2 == len(buf)


class TestRowShape:
    def _row(self, outcome):
        return build_row(campaign_id="C", arm_id="A", endpoint="https://api.deepseek.com/v1/x",
                         model_requested="m", model_reported="m", provider_request_id="r",
                         stream=False, outcome=outcome, reason=outcome.unmetered_reason)

    def test_key_set_and_order_are_frozen(self):
        row = self._row(normalize_usage({"prompt_cache_hit_tokens": 1, "prompt_cache_miss_tokens": 2,
                                         "completion_tokens": 3}))
        assert list(row.keys()) == list(ROW_KEY_ORDER)
        assert row["schema"] == "a0.meter.call/v1"

    def test_metered_row_has_null_reason_even_if_a_reason_was_passed(self):
        outcome = normalize_usage({"prompt_cache_hit_tokens": 1, "prompt_cache_miss_tokens": 2,
                                   "completion_tokens": 3})
        row = build_row(campaign_id="C", arm_id="A", endpoint="e", model_requested=None,
                        model_reported=None, provider_request_id=None, stream=True,
                        outcome=outcome, reason="some annotation")
        assert row["reason"] is None
        assert row["ceq"] == 14  # ceq(2, 1, 3) = 2 + floor(1*2/100) + 12
        assert row["unmetered"] is False

    def test_unmetered_row_carries_null_ceq_and_usage(self):
        outcome = normalize_usage({})
        row = self._row(outcome)
        assert row["usage"] is None and row["ceq"] is None and row["unmetered"] is True
        assert row["reason"] == "no_recognizable_usage_fields"

    def test_verify_row_recomputes_ceq(self):
        row = self._row(normalize_usage({"prompt_cache_hit_tokens": 1280,
                                         "prompt_cache_miss_tokens": 10240,
                                         "completion_tokens": 312}))
        assert verify_row(row) == (True, "ceq=11513")
        row["ceq"] = 11514
        ok, detail = verify_row(row)
        assert not ok and "formula gives 11513" in detail

    def test_verify_row_rejects_a_metered_row_with_a_reason(self):
        row = self._row(normalize_usage({"prompt_cache_hit_tokens": 0,
                                         "prompt_cache_miss_tokens": 1, "completion_tokens": 0}))
        row["reason"] = "annotation"
        ok, detail = verify_row(row)
        assert not ok and "reason" in detail

    def test_verify_row_rejects_an_unmetered_row_that_scores(self):
        row = self._row(normalize_usage({}))
        row["ceq"] = 0
        ok, detail = verify_row(row)
        assert not ok and "non-null ceq" in detail

    def test_verify_row_rejects_an_extra_key(self):
        row = self._row(normalize_usage({}))
        row["note"] = "extra"
        ok, detail = verify_row(row)
        assert not ok and "missing=" in detail and "extra=" in detail


class TestInterfaceExampleRowIsInconsistent:
    """A fact about `INTERFACE.md`, pinned here so it cannot be forgotten.

    §8 shows a worked row -- `usage={hit:0, miss:20153, completion:312}`, `ceq: 21313` -- whose
    arithmetic does not follow from the formula in the same section:
    `0 + floor(0*2/100) + 4*312 = 1248`, and `20153 + 1248 = 21401`, not `21313`.
    The likely intent is `prompt_cache_miss_tokens: 20065` (20065 + 1248 = 21313).

    The implementation follows the **formula**, which the section states as the definition and
    which is the only thing that can be recomputed from a row's own data. A checker that
    validates ledger rows by recomputing `ceq` will therefore flag any row copied from the
    example, and that is the correct behaviour -- a self-reported number is exactly what this
    component exists to eliminate.
    """

    EXAMPLE = {
        "schema": "a0.meter.call/v1", "campaign_id": "C", "arm_id": "A",
        "ts": "2026-01-01T00:00:00+00:00", "provider": "deepseek",
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "model_requested": "deepseek-flash", "model_reported": "deepseek-flash",
        "provider_request_id": "x", "stream": True,
        "usage": {"prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 20153,
                  "completion_tokens": 312},
        "ceq": 21313, "unmetered": False, "reason": None,
    }

    def test_formula_rejects_the_example_number(self):
        assert ceq(20153, 0, 312) == 21401
        assert ceq(20153, 0, 312) != 21313

    def test_example_becomes_consistent_with_miss_20065(self):
        assert ceq(20065, 0, 312) == 21313

    def test_the_row_from_the_interface_does_not_verify(self):
        ok, detail = verify_row(dict(self.EXAMPLE))
        assert not ok
        assert "21313" in detail and "21401" in detail


class TestLedger:
    def test_append_is_durable_and_readable(self, tmp_path):
        path = str(tmp_path / "ledger.jsonl")
        ledger = Ledger(path)
        ledger.preflight()
        row = build_row(campaign_id="C", arm_id="A", endpoint="e", model_requested=None,
                        model_reported=None, provider_request_id=None, stream=False,
                        outcome=normalize_usage({"prompt_cache_hit_tokens": 0,
                                                 "prompt_cache_miss_tokens": 10,
                                                 "completion_tokens": 1}), reason=None)
        line = ledger.append(row)
        assert line == json.dumps(row, ensure_ascii=True, separators=(",", ":"))
        with open(path, encoding="utf-8") as handle:
            assert json.loads(handle.readline()) == row

    def test_row_is_written_on_one_line(self, tmp_path):
        path = str(tmp_path / "ledger.jsonl")
        row = build_row(campaign_id="C", arm_id="A", endpoint="e", model_requested=None,
                        model_reported=None, provider_request_id=None, stream=False,
                        outcome=normalize_usage({}), reason="gap")
        Ledger(path).append(row)
        with open(path, encoding="utf-8") as handle:
            assert len(handle.readlines()) == 1

    def test_preflight_fails_on_a_read_only_file(self, tmp_path):
        path = tmp_path / "ledger.jsonl"
        path.write_text("")
        os.chmod(path, 0o444)
        try:
            with pytest.raises(LedgerError):
                Ledger(str(path)).preflight()
        finally:
            os.chmod(path, 0o644)

    def test_append_fails_loudly_when_the_file_is_not_writable(self, tmp_path):
        path = tmp_path / "ledger.jsonl"
        path.write_text("")
        os.chmod(path, 0o444)
        row = build_row(campaign_id="C", arm_id="A", endpoint="e", model_requested=None,
                        model_reported=None, provider_request_id=None, stream=False,
                        outcome=normalize_usage({}), reason="gap")
        try:
            with pytest.raises(LedgerError):
                Ledger(str(path)).append(row)
        finally:
            os.chmod(path, 0o644)

    def test_a_bad_row_is_rejected_before_it_reaches_the_file(self, tmp_path):
        path = str(tmp_path / "ledger.jsonl")
        ledger = Ledger(path)
        with pytest.raises(LedgerError):
            ledger.append({"schema": "a0.meter.call/v1", "campaign_id": "C"})
        assert not os.path.exists(path)

    def test_concurrent_appends_do_not_interleave(self, tmp_path):
        import threading

        path = str(tmp_path / "ledger.jsonl")
        ledger = Ledger(path)
        row = build_row(campaign_id="C", arm_id="A", endpoint="e", model_requested=None,
                        model_reported=None, provider_request_id=None, stream=False,
                        outcome=normalize_usage({"prompt_cache_hit_tokens": 0,
                                                 "prompt_cache_miss_tokens": 1,
                                                 "completion_tokens": 0}), reason=None)

        def worker():
            for _ in range(25):
                ledger.append(row)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        with open(path, encoding="utf-8") as handle:
            lines = [line for line in handle if line.strip()]
        assert len(lines) == 100
        assert all(json.loads(line) == row for line in lines)

    def test_sidecar_writes_elsewhere_by_default(self, tmp_path):
        # Guards the bug this test was written for: diagnostic records must never land in the
        # ledger the budget is summed from.
        ledger_path = tmp_path / "ledger.jsonl"
        sidecar = tmp_path / "events.jsonl"
        ledger = Ledger(str(ledger_path))
        ledger.append_best_effort({"kind": "note"}, str(sidecar))
        assert not ledger_path.exists()
        assert sidecar.exists()
