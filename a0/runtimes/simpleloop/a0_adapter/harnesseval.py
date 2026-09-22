"""The harness-outcome lane: SimpleLoop **consumes** a score, it does not measure one.

In A0 the adapter was the evaluator lane — ``estareval.py`` invoked ``E*`` as a
subprocess and read the Outcome it wrote.  That made the runtime the authority on
what a candidate scored, which is the thing A1 removes (``INTERFACE.md`` §12:
"用候选自报的分数" is forbidden, and principle (ii) puts the *realisation* of the
evaluator in the harness's hands).

This module is the replacement.  It has **no path that runs an evaluator**: it
writes a request into the harness's ABI directory and reads the response the
harness published.  Three consequences, each deliberate:

* the bytes it evaluates are the bytes the harness measured, bound together by
  the harness's ``a0/envelope`` measurement token, which the score event records;
* the number the search consumes is the harness's number even when the harness's
  number is a lie (that is the run this lane exists to make possible);
* with no harness service listening, ``evaluate`` times out and the candidate is
  recorded unscored — never silently scored locally.  Fail-closed, not
  fail-over.

The class presents ``EStarEvaluator``'s interface (``evaluate(candidate,
iteration=, tag=)`` returning an ``EStarResult``), so ``loop.py``, the traces and
the selection semantics are untouched.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

from .estareval import EXIT_ERROR, EXIT_INVALID, EXIT_OK, EStarIdentity, EStarResult, sha256_file

REQUEST_SCHEMA = "a0.a1.eval_request/v1"
RESPONSE_SCHEMA = "a0.a1.harness_outcome/v1"
IDENTITY_SCHEMA = "a0.a1.harness_identity/v1"


class HarnessEvalError(RuntimeError):
    """The harness lane is not wired: no identity, no ABI directory, no answer."""


@dataclass
class HarnessIdentity:
    """The harness's own statement of which evaluator it will run."""

    document: dict
    identity_path: Path
    script_sha256_recomputed: str
    source_verified: bool

    def as_dict(self) -> dict:
        return {
            "harness_identity_path": str(self.identity_path),
            "harness_run_id": self.document.get("harness_run_id"),
            "nonce": self.document.get("nonce"),
            "eid_star": self.document.get("eid_star"),
            "evaluator_source_sha256": self.document.get("evaluator_source_sha256"),
            "script_sha256_recomputed": self.script_sha256_recomputed,
            "source_verified": self.source_verified,
            "owns_evaluation": self.document.get("owns_evaluation"),
            "runtime_may_evaluate": self.document.get("runtime_may_evaluate"),
            "theta_e": self.document.get("theta_e"),
            "override": self.document.get("override"),
        }


class HarnessEvaluator:
    """Consume harness-authored Outcomes over the ABI directory.

    ``EStarEvaluator``-compatible: the loop does not know which lane it has.
    """

    def __init__(
        self,
        *,
        root: Path,
        campaign_id: str,
        arm_id: str,
        graph_path: Path,
        seed: int = 1337,
        timeout_s: float = 10.0,
        request_timeout_s: float = 600.0,
        expected_source_records: list[dict] | None = None,
        recorded_source_digest: str | None = None,
        poll_sec: float = 0.05,
        out_dir: Path | None = None,
        state_dir: Path | None = None,
        **_legacy,
    ) -> None:
        self.root = Path(root).resolve()
        self.campaign_id = campaign_id
        self.arm_id = arm_id
        self.graph_path = Path(graph_path).resolve()
        self.seed = seed
        self.timeout_s = timeout_s
        self.request_timeout_s = request_timeout_s
        self.expected_source_records = expected_source_records
        self.recorded_source_digest = recorded_source_digest
        self.poll_sec = poll_sec
        self.out_dir = Path(out_dir) if out_dir else self.root / "runtime-responses"
        self.state_dir = Path(state_dir) if state_dir else self.root / "runtime-state"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.requests_dir = self.root / "requests"
        self.responses_dir = self.root / "responses"
        self.calls = 0
        self.identity: HarnessIdentity | None = None
        self.responses: list[dict] = []
        self._seq = 0
        #: A per-process nonce in the request id. Without it a replayed run would
        #: re-use the previous run's response files and the "same bytes, same
        #: Outcome" check would be a tautology rather than a measurement.
        self._nonce = secrets.token_hex(6)

    # -- wiring -----------------------------------------------------------
    def verify_wiring(self) -> HarnessIdentity:
        """Prove the harness named by the ABI is the evaluator the run froze.

        Read from the *harness's* document, then re-derive the E* bytes locally
        and compare with both the harness's claim and the frozen ``EID*`` records.
        A mismatch is a wiring error (adapter exit 3), never a silent score.
        """
        identity_path = self.root / "harness_identity.json"
        if not identity_path.is_file():
            raise HarnessEvalError(
                f"no harness identity at {identity_path}: the harness evaluation service "
                "is not running, and this lane has no local evaluator to fall back on"
            )
        document = json.loads(identity_path.read_text(encoding="utf-8"))
        if document.get("schema") != IDENTITY_SCHEMA:
            raise HarnessEvalError(f"unexpected harness identity schema {document.get('schema')!r}")
        if not document.get("owns_evaluation"):
            raise HarnessEvalError("the harness identity does not claim ownership of evaluation")
        if document.get("runtime_may_evaluate"):
            raise HarnessEvalError("the harness identity permits runtime-side evaluation")

        script = Path(document["e_star_script"])
        if not script.is_file():
            raise HarnessEvalError(f"the harness names an evaluator that is not on disk: {script}")
        recomputed = sha256_file(script)
        if recomputed != document["e_star_script_sha256"]:
            raise HarnessEvalError(
                f"E* bytes moved since the harness wrote its identity: "
                f"{document['e_star_script_sha256']} -> {recomputed}"
            )
        verified = True
        for record in self.expected_source_records or []:
            path = script.parent / record["path"]
            if not path.is_file():
                raise HarnessEvalError(f"EID* records {record['path']!r} but it is missing")
            if sha256_file(path) != record["sha256"]:
                verified = False
                raise HarnessEvalError(f"E* source drift on {record['path']}")
        # The two ways of naming the evaluator must be built from the same
        # material: the EID*'s EvaluatorSource records and the harness's own
        # source records are compared file by file. They are *not* compared as
        # digests — EID*'s EvaluatorSource component and E*'s own
        # `evaluator_source_sha256` are different constructions over the same
        # bytes, and pretending otherwise would be a false red.
        harness_records = {
            record["path"]: record["sha256"] for record in document.get("source_records", [])
        }
        eid_records = {
            record["path"]: record["sha256"] for record in (self.expected_source_records or [])
        }
        if eid_records and harness_records and eid_records != harness_records:
            raise HarnessEvalError(
                "the harness evaluates a different set of files than EID* records: "
                f"harness={harness_records} eid={eid_records}"
            )
        self.identity = HarnessIdentity(
            document=document,
            identity_path=identity_path,
            script_sha256_recomputed=recomputed,
            source_verified=verified,
        )
        return self.identity

    # -- evaluation -------------------------------------------------------
    def evaluate(self, candidate, *, iteration: int, tag: str | None = None) -> EStarResult:
        """Ask the harness to evaluate; consume whatever it hands back.

        There is no branch here that computes a score locally — that is the
        point of the module.  A missing response is reported as an ``error``
        Outcome with ``cut_edges: null``, so the candidate is unscored and the
        selection never sees a number the harness did not author.
        """
        self._seq += 1
        request_id = (
            f"{self.arm_id}.{self._nonce}.i{iteration:04d}.{self._seq:04d}."
            f"{candidate.candidate_id}"
        )
        request_path = self.requests_dir / f"{request_id}.json"
        response_path = self.responses_dir / f"{request_id}.json"
        request = {
            "schema": REQUEST_SCHEMA,
            "request_id": request_id,
            "campaign_id": self.campaign_id,
            "arm_id": self.arm_id,
            "iteration": iteration,
            "candidate_id": candidate.candidate_id,
            "candidate_path": str(Path(candidate.path).resolve()),
            "graph_path": str(Path(self.graph_path).resolve()),
            "seed": self.seed,
            "timeout_s": self.timeout_s,
        }
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        tmp = request_path.with_suffix(".json.partial")
        tmp.write_text(json.dumps(request, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(request_path)

        started = time.monotonic()
        deadline = started + self.request_timeout_s
        while time.monotonic() < deadline:
            if response_path.is_file():
                break
            time.sleep(self.poll_sec)
        wall = time.monotonic() - started
        self.calls += 1

        if not response_path.is_file():
            return self._failure_result(
                candidate,
                request_id=request_id,
                wall=wall,
                kind="harness_outcome_missing",
                message=(
                    f"the harness evaluation service did not answer {request_id} within "
                    f"{self.request_timeout_s}s; the runtime does not evaluate, so the "
                    "candidate is unscored"
                ),
            )
        try:
            response = json.loads(response_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return self._failure_result(
                candidate,
                request_id=request_id,
                wall=wall,
                kind="harness_outcome_unreadable",
                message=f"{type(exc).__name__}: {exc}",
            )
        self.responses.append(response)
        if response.get("schema") != RESPONSE_SCHEMA:
            return self._failure_result(
                candidate,
                request_id=request_id,
                wall=wall,
                kind="harness_outcome_schema_mismatch",
                message=f"unexpected response schema {response.get('schema')!r}",
            )
        outcome = response.get("outcome")
        if outcome is None:
            failure = response.get("failure") or {}
            return self._failure_result(
                candidate,
                request_id=request_id,
                wall=wall,
                kind=failure.get("kind") or "harness_evaluation_failed",
                message=failure.get("detail") or "the harness returned no outcome",
            )
        status = outcome.get("status")
        exit_code = {"ok": EXIT_OK, "invalid": EXIT_INVALID}.get(status, EXIT_ERROR)
        failure = outcome.get("failure") or {}
        return EStarResult(
            candidate_id=candidate.candidate_id,
            exit_code=exit_code,
            status=status,
            outcome=outcome,
            manifest=None,
            manifest_line=None,
            stdout="",
            stderr="",
            wall_sec=wall,
            out_path=response_path,
            command=[],
            failure_kind=failure.get("kind"),
            failure_message=failure.get("detail"),
            fields=_fields_of(outcome),
        )

    def _failure_result(self, candidate, *, request_id: str, wall: float, kind: str,
                        message: str) -> EStarResult:
        return EStarResult(
            candidate_id=candidate.candidate_id,
            exit_code=EXIT_ERROR,
            status="error",
            outcome={
                "schema": "a0.maxcut.outcome/v1",
                "candidate_id": candidate.candidate_id,
                "status": "error",
                "cut_edges": None,
                "failure": {"kind": kind, "detail": message},
                "harness_request_id": request_id,
            },
            manifest=None,
            manifest_line=None,
            stdout="",
            stderr=message,
            wall_sec=wall,
            out_path=self.responses_dir / f"{request_id}.json",
            command=[],
            failure_kind=kind,
            failure_message=message,
            fields={},
        )

    # -- the runtime's view of the harness --------------------------------
    def evidence_detail(self, candidate_id: str) -> str:
        """What the score trace records about where this number came from.

        ``evaluator_evidence`` is a closed object in the trace schema, so this is
        a *string*: the harness's run id, the measurement token and the ledger
        sequence. A reader can therefore tell a harness-authored number from a
        locally measured one without any new trace field.
        """
        for response in reversed(self.responses):
            if response.get("candidate_id") == candidate_id:
                measurement = response.get("measurement") or {}
                return (
                    "harness_supplied "
                    f"harness_run_id={response.get('harness_run_id')} "
                    f"request_id={response.get('request_id')} "
                    f"ledger_seq={response.get('harness_ledger_seq')} "
                    f"oid={measurement.get('oid')} "
                    f"override_applied={response.get('override_applied')} "
                    f"true_cut_edges={response.get('true_cut_edges')} "
                    f"handed_cut_edges={response.get('handed_cut_edges')}"
                )
        return "harness_supplied (no response recorded)"

    def substitute_score(self, *args, **kwargs):  # pragma: no cover - a guard, not a feature
        raise HarnessEvalError(
            "this lane cannot substitute a score: the harness is the sole author of the Outcome"
        )


def _fields_of(outcome: dict) -> dict:
    """The multi-field projection the score trace carries.

    For T1 the authoritative quantity is the integer ``cut_edges`` (§5), so it
    is what the trace records.  A non-``ok`` outcome contributes no field at all:
    `invalid`, `error` and `timeout` must never look like a small score.
    """
    if outcome.get("status") != "ok":
        return {}
    cut = outcome.get("cut_edges")
    return {} if cut is None else {"cut_edges": cut}
