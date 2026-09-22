#!/usr/bin/env python3
"""Pure, side-effect-free core of the A1 metering proxy: token accounting and the ledger.

Everything in this module is a pure function of its inputs except `Ledger`, which owns one file.
It is separated from `meter_proxy.py` so that the two claims that matter most can be tested
without any socket:

* **the arithmetic is the frozen arithmetic** (`INTERFACE.md` §8):
  `ceq = miss + floor(hit*2/100) + 4*completion`, all integers, no float anywhere;
* **a missing usage is a gap, not a zero** — `UsageOutcome.usage is None` and
  `unmetered_reason` says exactly which field was missing, so a reader can tell "this call
  consumed no measured tokens" from "this call's consumption was not observable".

The three protocol faces the runtime may speak all normalise to the same triple
(`prompt_cache_hit_tokens`, `prompt_cache_miss_tokens`, `completion_tokens`):

| face | hit | miss | completion |
|---|---|---|---|
| OpenAI chat completions (DeepSeek native) | `prompt_cache_hit_tokens` | `prompt_cache_miss_tokens` | `completion_tokens` |
| OpenAI responses / generic | `input_tokens_details.cached_tokens` | `input_tokens - cached` | `output_tokens` |
| Anthropic messages | `cache_read_input_tokens` | `input_tokens + cache_creation_input_tokens` | `output_tokens` |

The last row is the one worth stating explicitly: Anthropic's `input_tokens` is the *uncached*
input, so everything not served from cache — fresh input plus cache writes — is billed at the
cache-miss rate and is counted as `miss`. Cache reads are the only thing DeepSeek discounts, and
they are the only thing that becomes `hit`.

Standard library only.
"""

from __future__ import annotations

import fcntl
import json
import os
import threading
from dataclasses import dataclass
from typing import Any, Iterable

SCHEMA_CALL = "a0.meter.call/v1"
SCHEMA_REGISTRY = "a0.meter.registry/v1"
SCHEMA_AID = "a0.meter.aid/v1"

PROVIDER = "deepseek"
DEFAULT_UPSTREAM_BASE = "https://api.deepseek.com"
DEFAULT_ALLOWLIST = ("api.deepseek.com",)
DEFAULT_MODE = "plaintext_base_url"

# Frozen verbatim from INTERFACE.md §8. Kept as a string so that the AID fragment can quote the
# formula it was built from and a third party can diff it against the interface without reading
# this file.
CEQ_FORMULA = "ceq = miss + floor(hit*2/100) + 4*completion"

ROW_KEY_ORDER = (
    "schema",
    "campaign_id",
    "arm_id",
    "ts",
    "provider",
    "endpoint",
    "model_requested",
    "model_reported",
    "provider_request_id",
    "stream",
    "usage",
    "ceq",
    "unmetered",
    "reason",
)

# The only per-call values a row may carry. Anything else in a row is a schema violation.
ALLOWED_ROW_KEYS = frozenset(ROW_KEY_ORDER)


def ceq(miss: int, hit: int, completion: int) -> int:
    """`CEq = miss + floor(hit*2/100) + 4*completion`, in integers only.

    `//` on non-negative integers is `floor`. The inputs are checked so that a negative
    "usage" (which would mean a broken provider response) can never silently reduce a budget.
    """
    for name, value in (("miss", miss), ("hit", hit), ("completion", completion)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("ceq: %s must be int, got %r" % (name, value))
        if value < 0:
            raise ValueError("ceq: %s must be >= 0, got %d" % (name, value))
    return miss + (hit * 2) // 100 + 4 * completion


@dataclass(frozen=True)
class Usage:
    prompt_cache_hit_tokens: int
    prompt_cache_miss_tokens: int
    completion_tokens: int

    def as_dict(self) -> dict:
        return {
            "prompt_cache_hit_tokens": self.prompt_cache_hit_tokens,
            "prompt_cache_miss_tokens": self.prompt_cache_miss_tokens,
            "completion_tokens": self.completion_tokens,
        }

    def ceq(self) -> int:
        return ceq(
            self.prompt_cache_miss_tokens,
            self.prompt_cache_hit_tokens,
            self.completion_tokens,
        )


@dataclass(frozen=True)
class UsageOutcome:
    """Either a complete triple, or an explicit statement of *which* part was unobservable."""

    usage: Usage | None
    source: str
    unmetered_reason: str | None
    raw: dict | None = None


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _details_cached(usage: dict) -> int | None:
    for key in ("prompt_tokens_details", "input_tokens_details", "completion_tokens_details"):
        block = usage.get(key)
        if isinstance(block, dict):
            cached = _int_or_none(block.get("cached_tokens"))
            if cached is not None:
                return cached
    return None


def normalize_usage(
    usage: dict,
    *,
    anthropic_route: bool = False,
    on_missing_cache_split: str = "unmetered",
) -> UsageOutcome:
    """Map one provider `usage` object onto the frozen triple.

    `on_missing_cache_split` decides what happens when a provider reports a prompt total but no
    cache split (`prompt_tokens` with no `*_details.cached_tokens`):

    * `"unmetered"` (default) — the cache split is genuinely unobservable, so the call is a gap;
    * `"conservative-miss"` — charge every prompt token at the miss rate, an upper bound on CEq.

    The default is `unmetered` because `INTERFACE.md` §8 forbids estimation, and because every
    DeepSeek face does report the split, so the strict branch costs nothing in production.
    """
    if not isinstance(usage, dict):
        return UsageOutcome(None, "none", "usage_not_an_object", None)
    if on_missing_cache_split not in ("unmetered", "conservative-miss"):
        raise ValueError("on_missing_cache_split must be 'unmetered' or 'conservative-miss'")

    hit = _int_or_none(usage.get("prompt_cache_hit_tokens"))
    miss = _int_or_none(usage.get("prompt_cache_miss_tokens"))
    completion = _int_or_none(usage.get("completion_tokens"))
    # The *cache* fields are what identify DeepSeek's native shape. `completion_tokens` alone
    # does not: OpenAI's generic shape uses the same name and no cache fields at all.
    if hit is not None or miss is not None:
        if hit is None or miss is None:
            return UsageOutcome(None, "openai_chat_native", "partial_native_usage_fields", dict(usage))
        if completion is None:
            return UsageOutcome(None, "openai_chat_native", "completion_tokens_absent", dict(usage))
        return _validated(Usage(hit, miss, completion), "openai_chat_native", dict(usage))

    # OpenAI semantics: `prompt_tokens` already counts the cached tokens.
    if "prompt_tokens" in usage:
        total = _int_or_none(usage.get("prompt_tokens"))
        out_tokens = _int_or_none(usage.get("completion_tokens"))
        if total is None:
            return UsageOutcome(None, "openai_generic", "prompt_tokens_not_an_integer", dict(usage))
        if out_tokens is None:
            return UsageOutcome(None, "openai_generic", "completion_tokens_absent", dict(usage))
        cached = _details_cached(usage)
        if cached is None:
            if on_missing_cache_split == "unmetered":
                return UsageOutcome(None, "openai_generic", "usage_present_without_cache_split", dict(usage))
            cached = 0
        return _validated(Usage(cached, total - cached, out_tokens), "openai_generic", dict(usage))

    # Anthropic / OpenAI-Responses semantics: the input figure excludes cache reads.
    if "input_tokens" in usage:
        fresh = _int_or_none(usage.get("input_tokens"))
        out_tokens = _int_or_none(usage.get("output_tokens"))
        if fresh is None:
            return UsageOutcome(None, "anthropic_or_responses", "input_tokens_not_an_integer", dict(usage))
        if out_tokens is None:
            return UsageOutcome(None, "anthropic_or_responses", "output_tokens_absent", dict(usage))
        cached_read = _int_or_none(usage.get("cache_read_input_tokens"))
        cache_write = _int_or_none(usage.get("cache_creation_input_tokens"))
        details_cached = _details_cached(usage)
        if cached_read is None and details_cached is None:
            if anthropic_route:
                # The Anthropic wire format omits zero-valued cache fields by spec, so on the
                # /v1/messages route "absent" is the documented encoding of "no cache read".
                cached_read = 0
            elif on_missing_cache_split == "unmetered":
                return UsageOutcome(None, "anthropic_or_responses", "usage_present_without_cache_split", dict(usage))
            else:
                cached_read = 0
        if cached_read is not None:
            hit_value = cached_read
            miss_value = fresh + (cache_write or 0)
            source = "anthropic_messages" if anthropic_route else "anthropic_or_responses"
        else:
            # OpenAI Responses semantics: `input_tokens` includes the cached tokens.
            hit_value = details_cached
            miss_value = fresh - details_cached
            source = "openai_responses"
        return _validated(Usage(hit_value, miss_value, out_tokens), source, dict(usage))

    return UsageOutcome(None, "none", "no_recognizable_usage_fields", dict(usage))


def _validated(usage: Usage, source: str, raw: dict) -> UsageOutcome:
    if usage.prompt_cache_hit_tokens < 0 or usage.prompt_cache_miss_tokens < 0 or usage.completion_tokens < 0:
        return UsageOutcome(None, source, "inconsistent_usage_negative_field", raw)
    return UsageOutcome(usage, source, None, raw)


# --------------------------------------------------------------------------------------------
# Usage extraction from the two response encodings
# --------------------------------------------------------------------------------------------

# Where a usage object can hide, in the shapes DeepSeek serves:
#   {"usage": ...}                          chat completions, Anthropic message_delta
#   {"message": {"usage": ...}}             Anthropic message_start
#   {"response": {"usage": ...}}            OpenAI responses response.completed
_USAGE_PATHS = (("usage",), ("message", "usage"), ("response", "usage"))


def iter_usage_dicts(obj: Any) -> Iterable[dict]:
    """Yield every `usage` object reachable at a known path inside one decoded JSON value."""
    if not isinstance(obj, dict):
        return
    for path in _USAGE_PATHS:
        node: Any = obj
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
        if isinstance(node, dict):
            yield node


_TOKEN_FIELD_NAMES = (
    "prompt_cache_hit_tokens",
    "prompt_cache_miss_tokens",
    "completion_tokens",
    "prompt_tokens",
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)


def usage_has_tokens(usage: dict) -> bool:
    """True when a `usage` object actually reports a token figure.

    Streaming protocols emit `"usage": null` on every ordinary chunk and the real object only at
    the end (OpenAI chat) or split across two events (Anthropic). This predicate is what decides
    whether an event is "the usage event" and therefore whether the tail may be released.
    """
    if not isinstance(usage, dict) or not usage:
        return False
    if any(usage.get(key) is not None for key in _TOKEN_FIELD_NAMES):
        return True
    return _details_cached(usage) is not None


def identify_fields(obj: Any) -> dict:
    """Provider-reported identity fields, from whichever shape the object is."""
    out = {"model": None, "request_id": None}
    if not isinstance(obj, dict):
        return out
    for path in ((), ("message",), ("response",)):
        node: Any = obj
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
        if not isinstance(node, dict):
            continue
        if out["model"] is None and isinstance(node.get("model"), str):
            out["model"] = node["model"]
        if out["request_id"] is None and isinstance(node.get("id"), str):
            out["request_id"] = node["id"]
    return out


def json_or_none(payload: bytes) -> Any:
    try:
        return json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


@dataclass
class SSEEvent:
    start: int
    end: int
    name: str | None
    data: bytes

    @property
    def is_terminator(self) -> bool:
        """The protocol's own end-of-stream marker.

        OpenAI chat completions ends with `data: [DONE]`; Anthropic messages with
        `event: message_stop`; the OpenAI Responses API with `event: response.completed`.
        Recognising all three is what lets "the stream ended" be distinguished from "the stream
        was cut", which is the difference between `stream_ended_without_usage` and
        `stream_truncated_before_usage` in a ledger row.
        """
        if self.name in ("message_stop", "response.completed"):
            return True
        return self.data.strip() == b"[DONE]"


def is_complete_usage(merged: dict) -> bool:
    """True when `merged` carries enough to normalise without guessing."""
    if not isinstance(merged, dict) or not merged:
        return False
    if all(_int_or_none(merged.get(k)) is not None for k in
           ("prompt_cache_hit_tokens", "prompt_cache_miss_tokens", "completion_tokens")):
        return True
    if _int_or_none(merged.get("prompt_tokens")) is not None \
            and _int_or_none(merged.get("completion_tokens")) is not None:
        return _details_cached(merged) is not None
    if _int_or_none(merged.get("input_tokens")) is not None \
            and _int_or_none(merged.get("output_tokens")) is not None:
        return True
    return False



def parse_sse_events(buf: bytearray, pos: int) -> tuple[list[SSEEvent], int]:
    """Parse every *complete* SSE event from `buf` at or after `pos`.

    Returns the events and the offset of the first byte not yet belonging to a complete event.
    Incomplete trailing bytes are left for the next call, so this is safe to drive incrementally.
    """
    events: list[SSEEvent] = []
    while True:
        i_lf = buf.find(b"\n\n", pos)
        i_crlf = buf.find(b"\r\n\r\n", pos)
        if i_lf < 0 and i_crlf < 0:
            return events, pos
        if i_crlf >= 0 and (i_lf < 0 or i_crlf < i_lf):
            end, advance = i_crlf, 4
        else:
            end, advance = i_lf, 2
        name: str | None = None
        data_lines: list[bytes] = []
        for line in bytes(buf[pos:end]).split(b"\n"):
            if line.endswith(b"\r"):
                line = line[:-1]
            if not line or line.startswith(b":"):
                continue
            field_name, _, value = line.partition(b":")
            value = value[1:] if value.startswith(b" ") else value
            if field_name == b"event":
                name = value.decode("utf-8", "replace")
            elif field_name == b"data":
                data_lines.append(value)
        events.append(SSEEvent(pos, end + advance, name, b"\n".join(data_lines)))
        pos = end + advance


# --------------------------------------------------------------------------------------------
# Ledger
# --------------------------------------------------------------------------------------------


class LedgerError(RuntimeError):
    """The ledger could not be made durable. A call that cannot be booked must not succeed."""


class Ledger:
    """Append-only jsonl ledger, one row per attempted upstream call.

    Durability contract: every append is a fresh `open(O_APPEND)` + `flock` + `write` + `fsync`.
    Re-opening per row (instead of holding one fd) is what makes `preflight()` meaningful: if the
    file or its directory stops being writable mid-campaign, the *next* call fails closed instead
    of the proxy silently buffering rows it can never flush.
    """

    def __init__(self, path: str, *, fsync: bool = True):
        self.path = path
        self.fsync = fsync
        self._lock = threading.Lock()
        self.write_failures = 0

    def preflight(self) -> None:
        """Prove the ledger is writable *before* spending anything upstream."""
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        except OSError as exc:
            raise LedgerError("ledger not writable: %s: %s" % (self.path, exc)) from exc
        os.close(fd)

    def dumps(self, row: dict) -> str:
        self._check_row(row)
        return json.dumps(row, ensure_ascii=True, separators=(",", ":"))

    @staticmethod
    def _check_row(row: dict) -> None:
        if set(row) != ALLOWED_ROW_KEYS:
            missing = sorted(ALLOWED_ROW_KEYS - set(row))
            extra = sorted(set(row) - ALLOWED_ROW_KEYS)
            raise LedgerError("ledger row does not match %s (missing=%s extra=%s)"
                              % (SCHEMA_CALL, missing, extra))
        if row["schema"] != SCHEMA_CALL:
            raise LedgerError("ledger row schema must be %s" % SCHEMA_CALL)

    def append(self, row: dict) -> str:
        line = self.dumps(row)
        payload = (line + "\n").encode("utf-8")
        with self._lock:
            try:
                fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
            except OSError as exc:
                self.write_failures += 1
                raise LedgerError("ledger open failed: %s: %s" % (self.path, exc)) from exc
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                written = os.write(fd, payload)
                if written != len(payload):
                    raise LedgerError("short ledger write: %d of %d bytes" % (written, len(payload)))
                if self.fsync:
                    os.fsync(fd)
            except OSError as exc:
                self.write_failures += 1
                raise LedgerError("ledger write failed: %s: %s" % (self.path, exc)) from exc
            finally:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except OSError:
                    pass
                os.close(fd)
        return line

    def append_best_effort(self, note: dict, path: str | None = None) -> None:
        """Diagnostics only. Never allowed to affect the call's outcome.

        `path` is required in practice: writing diagnostic records into the authoritative ledger
        would corrupt the file the budget is summed from. The default is only a convenience for
        callers that deliberately keep the two together.
        """
        target = path or self.path
        try:
            with self._lock:
                with open(target, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(note, ensure_ascii=True, separators=(",", ":")) + "\n")
        except OSError:
            pass


def now_iso() -> str:
    import datetime

    return datetime.datetime.now().astimezone().isoformat(timespec="microseconds")


def build_row(
    *,
    campaign_id: str,
    arm_id: str,
    endpoint: str,
    model_requested: str | None,
    model_reported: str | None,
    provider_request_id: str | None,
    stream: bool,
    outcome: UsageOutcome | None,
    reason: str | None,
    ts: str | None = None,
) -> dict:
    """Assemble one ledger row in exactly the key order of `INTERFACE.md` §8.

    `reason` is a property of the *unmetered* case only: a metered row carries `reason: null`
    and its `ceq` is authoritative. Anything a caller wants to say about a metered call that is
    not a number (a truncated tail, a conservative branch) belongs in the diagnostic sidecar,
    never in a row that a budget will be summed from.
    """
    if outcome is not None and outcome.usage is not None:
        usage = outcome.usage.as_dict()
        ceq_value: int | None = outcome.usage.ceq()
        unmetered = False
        final_reason = None
    else:
        usage = None
        ceq_value = None
        unmetered = True
        final_reason = reason or (outcome.unmetered_reason if outcome else "not_measured")
    row = {
        "schema": SCHEMA_CALL,
        "campaign_id": campaign_id,
        "arm_id": arm_id,
        "ts": ts or now_iso(),
        "provider": PROVIDER,
        "endpoint": endpoint,
        "model_requested": model_requested,
        "model_reported": model_reported,
        "provider_request_id": provider_request_id,
        "stream": bool(stream),
        "usage": usage,
        "ceq": ceq_value,
        "unmetered": unmetered,
        "reason": final_reason,
    }
    return row


def verify_row(row: dict) -> tuple[bool, str]:
    """Independent re-derivation of a row's claims. Used by `verify_ledger.py` and the tests."""
    if not isinstance(row, dict):
        return False, "row is not an object"
    try:
        Ledger._check_row(row)
    except LedgerError as exc:
        return False, str(exc)
    usage = row.get("usage")
    if row.get("unmetered"):
        if usage is not None:
            return False, "unmetered row carries a usage object"
        if row.get("ceq") is not None:
            return False, "unmetered row carries a non-null ceq"
        if not row.get("reason"):
            return False, "unmetered row has an empty reason"
        return True, "unmetered"
    if not isinstance(usage, dict):
        return False, "metered row has no usage object"
    need = {"prompt_cache_hit_tokens", "prompt_cache_miss_tokens", "completion_tokens"}
    if set(usage) != need:
        return False, "usage keys are %s, expected %s" % (sorted(usage), sorted(need))
    for key in need:
        if isinstance(usage[key], bool) or not isinstance(usage[key], int):
            return False, "usage.%s is not an int" % key
    try:
        expect = ceq(usage["prompt_cache_miss_tokens"], usage["prompt_cache_hit_tokens"],
                     usage["completion_tokens"])
    except (TypeError, ValueError) as exc:
        return False, "ceq not computable: %s" % exc
    if row.get("ceq") != expect:
        return False, "ceq=%r but formula gives %d" % (row.get("ceq"), expect)
    if row.get("reason") not in (None,):
        return False, "metered row carries reason=%r" % (row.get("reason"),)
    return True, "ceq=%d" % expect


def read_ledger(path: str) -> list[dict]:
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError as exc:
                raise LedgerError("truncated/corrupt ledger line %d: %s" % (lineno, exc)) from exc
    return rows
