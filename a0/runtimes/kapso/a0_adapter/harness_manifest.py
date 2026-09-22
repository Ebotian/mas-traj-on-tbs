"""Landing a harness-authored Outcome as KAPSO's score of record, after the session.

`HARNESS-OWNED-EVAL.md` established *where* the score can land
(`node.score`, via the manifest-of-record line KAPSO already reads) and the three
conditions attached to landing it.  This module implements the conditions as code:

1. **The class triple comes from the runtime.**  `manifest_of_record`
   (`registered_evaluation.py:87-99`) compares the line's
   `fidelity`/`fraction`/`seed` against the *granted* triple and returns ``None``
   — silently, with only a print — when they differ.  Hardcoding
   ``full/1.0/1337`` therefore works exactly until the runtime's grant is not the
   default, and then the score vanishes with no error.  `class_triple(strategy)`
   reads `strategy.fidelity_decision.eval_fidelity`,
   `strategy.fidelity_decision.eval_fraction` and
   `strategy.registered_subsample_seed` instead, and `manifest_line()` refuses to
   build a line when any of the three cannot be read.  The item counts
   (``items``/``total_items``) are present and positive, because
   `parse_manifest_line` **raises** without them.

2. **The write happens after the session ends.**  KAPSO checks no signature,
   run id or process identity on a manifest line (there is no authentication — a
   candidate session can print the same line).  The only construction that makes
   the *harness* the sole author is ordering: the session's own output is already
   fixed by the time `_absorb_implementation` returns, and this module appends
   the harness's line afterwards, so the file's **last** manifest line is the
   harness's.  `install_post_session_manifest(…)` patches
   `GenericSearch._absorb_implementation` — an adapter-side monkeypatch, no
   upstream edit — and the hook runs after the original returns.

3. **Our artifacts say who authored the number.**  Every line carries
   ``harness_supplied: true`` and the harness's evaluation-ledger sequence, the
   response and the ledger row both record it, and the wiring report states the
   caveat plainly:

   > KAPSO's own ledger (`node.evaluation_attempts`, evidence tiers,
   > `get_deliverable_score`, the MCP experiment memory) will attribute this
   > number to the **registered evaluator** at the granted class.  KAPSO cannot
   > tell a harness outcome from its own measurement, so **A1 must not treat
   > KAPSO's ledger as evaluator-realisation evidence.**  The evaluator
   > realisation evidence is the harness's own ledger
   > (`a0/a1/eval_service.py`) plus the `a0/envelope` measurement token.
"""

from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

REQUEST_SCHEMA = "a0.a1.eval_request/v1"
RESPONSE_SCHEMA = "a0.a1.harness_outcome/v1"

MANIFEST_MARKER = "KAPSO_EVAL_MANIFEST"


class HarnessManifestError(RuntimeError):
    """The harness line cannot be built, or the runtime's grant cannot be read."""


# ---------------------------------------------------------------------------
# 1. the class triple, read from the runtime
# ---------------------------------------------------------------------------
def class_triple(strategy: Any) -> Dict[str, Any]:
    """The granted class, read from the runtime — never hardcoded.

    Returns ``{"fidelity", "fraction", "seed", "source"}``. ``source`` records
    which attributes were readable, so a reader can tell "the runtime granted
    this" from "the runtime could not be asked".
    """
    if strategy is None:
        raise HarnessManifestError("no strategy to read the granted class from")
    if not hasattr(strategy, "registered_subsample_seed"):
        raise HarnessManifestError(
            "the strategy exposes no `registered_subsample_seed`; KAPSO's "
            "manifest_of_record compares the line's seed against it, so a guessed seed "
            "would be silently discarded (registered_evaluation.py:87-99)"
        )
    decision = getattr(strategy, "fidelity_decision", None)
    if decision is None:
        raise HarnessManifestError(
            "the strategy has no `fidelity_decision`; the granted fidelity/fraction cannot "
            "be read and a hardcoded triple would be silently discarded"
        )
    fidelity = getattr(decision, "eval_fidelity", None)
    fraction = getattr(decision, "eval_fraction", None)
    if fidelity is None or fraction is None:
        raise HarnessManifestError(
            f"the strategy's fidelity decision carries no class: {decision!r}"
        )
    return {
        "fidelity": str(fidelity),
        "fraction": float(fraction),
        "seed": int(strategy.registered_subsample_seed),
        "source": {
            "fidelity": "strategy.fidelity_decision.eval_fidelity",
            "fraction": "strategy.fidelity_decision.eval_fraction",
            "seed": "strategy.registered_subsample_seed",
        },
    }


def manifest_line(*, strategy: Any, score: float, items: int = 1,
                  total_items: int = 1, extra: Optional[dict] = None) -> str:
    """Compose the harness's `KAPSO_EVAL_MANIFEST` line.

    ``items``/``total_items`` are required by `parse_manifest_line`
    (`maintainer.py:70-79`) and must be positive, so they are validated here
    rather than discovered as an exception at feedback time.
    """
    triple = class_triple(strategy)
    if items <= 0 or total_items <= 0:
        raise HarnessManifestError(
            "item counts must be positive; parse_manifest_line raises otherwise "
            "(maintainer.py:70-79)"
        )
    payload = {
        "fidelity": triple["fidelity"],
        "fraction": repr(triple["fraction"]),
        "seed": triple["seed"],
        "items": int(items),
        "total_items": int(total_items),
        "score": float(score),
        "harness_supplied": True,
    }
    payload.update(extra or {})
    return MANIFEST_MARKER + " " + json.dumps(payload, sort_keys=True)


def amend_evaluation_output(node: Any, line: str) -> str:
    """Append the harness line and return the amended output.

    Appending (not prepending) is the whole mechanism: `manifest_of_record`
    keeps the **last** matching line (`registered_evaluation.py:72-78`).
    """
    existing = node.evaluation_output or ""
    node.evaluation_output = (existing.rstrip("\n") + "\n" + line + "\n") if existing else (line + "\n")
    return node.evaluation_output


# ---------------------------------------------------------------------------
# the harness client (same ABI as SimpleLoop's lane)
# ---------------------------------------------------------------------------
@dataclass
class HarnessEvalClient:
    """Ask the harness (running E*) for an Outcome over the ABI directory."""

    root: Path
    campaign_id: str
    arm_id: str
    seed: int = 1337
    timeout_s: float = 10.0
    request_timeout_s: float = 600.0
    poll_sec: float = 0.05
    _nonce: str = field(default_factory=lambda: secrets.token_hex(6))
    _seq: int = 0
    calls: int = 0
    exchanges: List[dict] = field(default_factory=list)

    def identity(self) -> dict:
        path = Path(self.root) / "harness_identity.json"
        if not path.is_file():
            raise HarnessManifestError(
                f"no harness identity at {path}: the harness evaluation service is not running"
            )
        return json.loads(path.read_text(encoding="utf-8"))

    def evaluate(self, *, candidate_id: str, candidate_path: Path,
                 graph_path: Optional[Path] = None) -> dict:
        self._seq += 1
        request_id = f"{self.arm_id}.{self._nonce}.{self._seq:04d}.{candidate_id}"
        request = {
            "schema": REQUEST_SCHEMA,
            "request_id": request_id,
            "campaign_id": self.campaign_id,
            "arm_id": self.arm_id,
            "candidate_id": candidate_id,
            "candidate_path": str(Path(candidate_path).resolve()),
            "seed": self.seed,
            "timeout_s": self.timeout_s,
        }
        if graph_path is not None:
            request["graph_path"] = str(Path(graph_path).resolve())
        requests_dir = Path(self.root) / "requests"
        responses_dir = Path(self.root) / "responses"
        requests_dir.mkdir(parents=True, exist_ok=True)
        tmp = requests_dir / f"{request_id}.json.partial"
        tmp.write_text(json.dumps(request, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(requests_dir / f"{request_id}.json")

        response_path = responses_dir / f"{request_id}.json"
        started = time.monotonic()
        deadline = started + self.request_timeout_s
        while time.monotonic() < deadline and not response_path.is_file():
            time.sleep(self.poll_sec)
        self.calls += 1
        if not response_path.is_file():
            exchange = {"request": request, "response": None,
                        "error": f"no answer within {self.request_timeout_s}s"}
            self.exchanges.append(exchange)
            raise HarnessManifestError(
                f"the harness did not answer {request_id}; the runtime does not evaluate, so "
                "there is no score to write"
            )
        response = json.loads(response_path.read_text(encoding="utf-8"))
        if response.get("schema") != RESPONSE_SCHEMA:
            raise HarnessManifestError(f"unexpected response schema {response.get('schema')!r}")
        self.exchanges.append({"request": request, "response": response})
        return response


# ---------------------------------------------------------------------------
# 2. the post-session hook
# ---------------------------------------------------------------------------
class PostSessionManifest:
    """Write the harness's line after the implementation session has finished.

    The hook is `GenericSearch._absorb_implementation` — the method that copies
    the session's tags into the node and returns.  The original runs first (so
    the session's own `KAPSO_EVAL_MANIFEST` line, if any, is already in
    `node.evaluation_output`), then this object appends the harness's line.  The
    patch is installed on the class KAPSO's own strategy code uses; no file under
    `/home/ebt/kapso_ck/` is touched.
    """

    def __init__(self, *, strategy: Any, client: HarnessEvalClient,
                 graph_path: Optional[Path] = None,
                 artifact_resolver=None, score_of=None, run_id: str = "") -> None:
        self.strategy = strategy
        self.client = client
        self.graph_path = Path(graph_path) if graph_path is not None else None
        self.artifact_resolver = artifact_resolver
        self.run_id = run_id or f"kapso-ho-{int(time.time())}"
        #: The fold from a harness Outcome to the number KAPSO stores. Default:
        #: the plumbing task's `sum_radii` (the same field the runtime's own
        #: selection uses, so the two agree on what a score is).
        self.score_of = score_of or _default_score_of
        self.events: List[dict] = []
        self.installed: Optional[str] = None

    # -- the hook ---------------------------------------------------------
    def amend(self, strategy_self: Any, node: Any) -> Optional[dict]:
        """Called after `_absorb_implementation`. Returns the recorded event."""
        if getattr(node, "suspended", False):
            return None
        artifact = self.artifact_resolver(node)
        if artifact is None:
            self.events.append({
                "node_id": getattr(node, "node_id", None),
                "status": "no_artifact",
                "note": "no candidate artifact to evaluate; the harness wrote no line",
            })
            return None
        before = node.evaluation_output or ""
        response = self.client.evaluate(
            candidate_id=f"node{getattr(node, 'node_id', 'x')}",
            candidate_path=artifact,
            graph_path=self.graph_path,
        )
        outcome = response.get("outcome") or {}
        score = self.score_of(outcome)
        if score is None:
            # A harness verdict that is not `ok` carries no number, and KAPSO
            # must not be handed one: writing nothing leaves the node's score to
            # the session's own line, which is honest — the harness refused it.
            self.events.append({
                "node_id": getattr(node, "node_id", None),
                "status": "harness_outcome_not_ok",
                "harness_status": outcome.get("status"),
                "harness_request_id": response.get("request_id"),
                "session_lines": _manifest_lines(before),
                "wrote": False,
            })
            return None
        triple = class_triple(strategy_self)
        line = manifest_line(
            strategy=strategy_self,
            score=score,
            extra={
                "harness_run_id": response.get("harness_run_id"),
                "harness_request_id": response.get("request_id"),
                "harness_ledger_seq": response.get("harness_ledger_seq"),
                "measurement_oid": (response.get("measurement") or {}).get("oid"),
                "override_applied": response.get("override_applied"),
                "true_value": response.get("true_cut_edges"),
                "written_by": "a0/runtimes/kapso/a0_adapter/harness_manifest.py",
                "written_after_session": True,
            },
        )
        session_lines = _manifest_lines(before)
        amend_evaluation_output(node, line)
        event = {
            "node_id": getattr(node, "node_id", None),
            "status": "written",
            "artifact": str(artifact),
            "granted_class": triple,
            "harness_score": score,
            "harness_status": outcome.get("status"),
            "harness_request_id": response.get("request_id"),
            "harness_ledger_seq": response.get("harness_ledger_seq"),
            "measurement_oid": (response.get("measurement") or {}).get("oid"),
            "override_applied": response.get("override_applied"),
            "session_manifest_lines": session_lines,
            "last_line_is_the_harness_s": (node.evaluation_output or "").strip().splitlines()[-1]
            == line,
            "score_before_amendment": _last_session_score(session_lines),
            "wrote": True,
        }
        self.events.append(event)
        return event

    # -- installation -----------------------------------------------------
    def install(self) -> str:
        from kapso.execution.search_strategies.generic import strategy as strategy_module

        cls = strategy_module.GenericSearch
        original = cls._absorb_implementation
        hook = self

        def patched(self, node, agent_output, recovered, suspended, lane_tag=""):
            original(self, node, agent_output, recovered, suspended, lane_tag)
            # AFTER the session's output has been absorbed: this is the ordering
            # that makes the harness the author of the last manifest line.
            hook.amend(self, node)

        cls._absorb_implementation = patched
        self.installed = (
            "a0_adapter/harness_manifest.py::PostSessionManifest.amend <- "
            "GenericSearch._absorb_implementation "
            "(kapso/execution/search_strategies/generic/strategy.py:606-662), called after "
            "the original returns"
        )
        return self.installed

    def as_dict(self) -> dict:
        return {
            "schema": "a0.kapso.post_session_manifest/v1",
            "run_id": self.run_id,
            "installed_at": self.installed,
            "harness_root": str(self.client.root),
            "campaign_id": self.client.campaign_id,
            "arm_id": self.client.arm_id,
            "harness_calls": self.client.calls,
            "events": self.events,
            "attribution_caveat": ATTRIBUTION_CAVEAT,
        }


ATTRIBUTION_CAVEAT = (
    "KAPSO records this score as a `full`-fidelity attempt under the *registered evaluator's* "
    "id (record_evaluation_attempt, registered_evaluation.py:124-159, never consults the "
    "manifest), so node.evaluation_attempts, evidence tiers, get_deliverable_score and the MCP "
    "experiment memory will attribute the harness's number to the registered evaluator. KAPSO "
    "cannot distinguish a harness outcome from its own measurement. A1 must therefore NOT treat "
    "KAPSO's ledger as evaluator-realisation evidence; the realisation evidence is the harness's "
    "own ledger (a0/a1/eval_service.py) and the a0/envelope measurement token."
)


def _manifest_lines(text: str) -> List[dict]:
    lines = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith(MANIFEST_MARKER):
            try:
                lines.append(json.loads(stripped[len(MANIFEST_MARKER):].strip()))
            except json.JSONDecodeError:
                lines.append({"unparseable": stripped[:200]})
    return lines


def _last_session_score(lines: List[dict]):
    for payload in reversed(lines):
        if isinstance(payload, dict) and "score" in payload:
            return payload["score"]
    return None


def _default_score_of(outcome: Dict[str, Any]):
    """Plumbing task: `fields.sum_radii` iff status == ok, else no number."""
    if outcome.get("status") != "ok":
        return None
    fields = outcome.get("fields") or {}
    value = fields.get("sum_radii")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def maxcut_score_of(outcome: Dict[str, Any]):
    """T1: the integer `cut_edges` iff status == ok (INTERFACE.md §5), else none."""
    if outcome.get("status") != "ok":
        return None
    value = outcome.get("cut_edges")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
