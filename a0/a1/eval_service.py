"""The harness-owned evaluation service for T1 (max-cut).

**What this process is.**  In A1 the runtime under test does not evaluate.  This
process does.  It is started by the *harness*, it runs the frozen evaluator
(`a0/tasks/maxcut/e_star.py`) as its own subprocess, it authors the ``Outcome``
document, it binds that outcome into an ``a0/envelope`` measurement token, it
appends a row to an append-only harness ledger, and only then does it publish a
response.  A runtime that cannot read a response has no score at all.

**The ABI** (a directory of files, so it survives a network namespace and a
process boundary — see ``topology.py``):

```
<root>/harness_identity.json     written once at startup, by the harness
<root>/requests/<request_id>.json     written by the runtime under test
<root>/responses/<request_id>.json    written by this process, atomically
<root>/ledger.jsonl                   append-only, one row per evaluation, fsync'd
```

Request  ``a0.a1.eval_request/v1``::

    {"schema":"a0.a1.eval_request/v1","request_id":"r0001",
     "campaign_id":"C_...","arm_id":"A_...","iteration":3,
     "candidate_id":"...","candidate_path":"<abs file or dir>",
     "graph_path":"<abs graph.json>","seed":1337,"timeout_s":10.0}

Response ``a0.a1.harness_outcome/v1``::

    {"schema":"a0.a1.harness_outcome/v1","request_id":"r0001",...
     "status":"ok","score_field":"cut_edges","value":317,
     "outcome":{...the Outcome the runtime must consume...},
     "measurement":{...a0.envelope.measurement_attestation/v1...},
     "harness_supplied":true,
     "true_value":317,"handed_value":317,"override_applied":false,
     "harness_ledger_seq":0}

**Two evaluators, one ABI.**  ``--evaluator maxcut`` (T1, the A1 task) drives
``a0/tasks/maxcut/e_star.py`` and reads ``cut_edges``; ``--evaluator
circle-packing`` drives the plumbing evaluator and reads ``fields.sum_radii``.
Only the argv and the score field differ (see ``EVALUATORS``); the ABI, the
token, the ledger and the fail-closed ordering are identical, because the claim
they carry — the harness authors the number — is not task-specific.

**The override.**  ``--override <json>`` maps ``candidate_id -> integer``.  When
a candidate is listed, the harness authors the *handed* value of its score field
from that map instead of from ``E*``, and records both numbers.  This exists to make the
A1 property "the runtime consumes, it does not measure" observable: the
runtime's selection must follow the harness's number even when the harness's
number is a deliberate lie.  The override is never silent — ``harness_supplied``
and ``override_applied`` are on every response and on every ledger row.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
ENVELOPE_DIR = REPO_ROOT / "a0" / "envelope"
MAXCUT_DIR = REPO_ROOT / "a0" / "tasks" / "maxcut"

if str(ENVELOPE_DIR) not in sys.path:
    sys.path.insert(0, str(ENVELOPE_DIR))
import envelope as env  # noqa: E402  (a0/envelope/envelope.py, by path on purpose)

REQUEST_SCHEMA = "a0.a1.eval_request/v1"
RESPONSE_SCHEMA = "a0.a1.harness_outcome/v1"
IDENTITY_SCHEMA = "a0.a1.harness_identity/v1"
LEDGER_SCHEMA = "a0.a1.harness_eval_ledger/v1"

DEFAULT_E_STAR = MAXCUT_DIR / "e_star.py"
DEFAULT_PYTHON = Path("/usr/bin/python3")
DEFAULT_SEED = 1337
DEFAULT_TIMEOUT_S = 10.0

#: The two frozen T1/A0 evaluators this service can own. The ABI is identical;
#: only the argv and the score field differ. `maxcut` is the A1 task; the
#: plumbing evaluator is accepted because the KAPSO adapter's verified wiring is
#: on the plumbing task (`a0/a1/DEVIATIONS.md` D-A1-2) and its ordering test must
#: run against a real runtime rather than a mock.
EVALUATORS = {
    "maxcut": {
        "argv": [
            "evaluate", "--candidate", "{candidate}", "--graph", "{graph}",
            "--seed", "{seed}", "--timeout", "{timeout}", "--out", "{out}",
            "--emit-resources", "{resources}", "--state-dir", "{state}",
        ],
        "requires_graph": True,
        "score_field": "cut_edges",
        "default_script": str(MAXCUT_DIR / "e_star.py"),
    },
    "circle-packing": {
        "argv": [
            "evaluate", "--candidate", "{candidate}", "--seed", "{seed}",
            "--fidelity", "{fidelity}", "--fraction", "{fraction}",
            "--n", "{n}", "--runs", "{runs}", "--runtime-budget-ms", "{budget}",
            "--timeout-s", "{timeout}", "--out", "{out}",
            "--emit-resources", "{resources}", "--state-dir", "{state}",
        ],
        "requires_graph": False,
        "score_field": "fields.sum_radii",
        "default_script": str(REPO_ROOT / "a0" / "tasks" / "circle-packing" / "e_star.py"),
    },
}

#: E*'s own exit codes (a0/tasks/maxcut/e_star.py:95) map onto these statuses.
STATUS_BY_EXIT = {0: "ok", 2: "invalid", 3: "error", 4: "timeout"}


class ServiceError(RuntimeError):
    """A malformed request, or a harness-side failure to author an outcome."""


# ---------------------------------------------------------------------------
# canonicalisation — E*'s own scheme is reused, never re-implemented
# ---------------------------------------------------------------------------
def canonical_json(payload: Any) -> str:
    """E*'s canonical form (a0/tasks/maxcut/e_star.py:109), recomputed here.

    The service writes canonical bytes for everything it authors so that two
    identical evaluations are byte-identical documents and a third party can
    re-derive every digest with `json.dumps(..., sort_keys=True, indent=2)`.
    """
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fsync_append(path: Path, row: dict) -> int:
    """Append one row and fsync before returning its 0-based sequence number.

    Fail-closed: if the row cannot be booked, the evaluation is never published,
    so an unbooked evaluation is not expressible (the same guarantee the meter
    makes for model calls).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        handle.seek(0, os.SEEK_END)
        seq = sum(1 for line in _iter_lines(path) if line.strip())
        row = dict(row)
        row["seq"] = seq
        handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return seq


def _iter_lines(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        yield from handle


# ---------------------------------------------------------------------------
# the request the runtime writes
# ---------------------------------------------------------------------------
@dataclass
class EvalRequest:
    request_id: str
    campaign_id: str
    arm_id: str
    candidate_id: str
    candidate_path: Path
    graph_path: Optional[Path]
    seed: int = DEFAULT_SEED
    timeout_s: float = DEFAULT_TIMEOUT_S
    iteration: Optional[int] = None

    @classmethod
    def from_document(cls, document: dict, *, root: Path) -> "EvalRequest":
        if document.get("schema") != REQUEST_SCHEMA:
            raise ServiceError(f"unexpected request schema {document.get('schema')!r}")
        missing = [
            key
            for key in ("request_id", "candidate_id", "candidate_path")
            if key not in document
        ]
        if missing:
            raise ServiceError(f"request is missing {missing}")
        request_id = str(document["request_id"])
        if not request_id or "/" in request_id or ".." in request_id:
            raise ServiceError(f"unsafe request_id {request_id!r}")
        graph_path = None
        if document.get("graph_path"):
            graph_path = Path(document["graph_path"])
            if not graph_path.is_absolute():
                raise ServiceError("graph_path must be absolute")
            if not graph_path.is_file():
                raise ServiceError(f"graph_path does not exist: {graph_path}")
        candidate_path = Path(document["candidate_path"])
        if not candidate_path.is_absolute():
            # Relative candidate paths are resolved against the request root: the
            # runtime's own work directory is handed over as an opaque token, so
            # the runtime never has to name a host path.
            candidate_path = (root / candidate_path).resolve()
        if not candidate_path.exists():
            raise ServiceError(f"candidate_path does not exist: {candidate_path}")
        return cls(
            request_id=request_id,
            campaign_id=str(document.get("campaign_id") or ""),
            arm_id=str(document.get("arm_id") or ""),
            candidate_id=str(document["candidate_id"]),
            candidate_path=candidate_path,
            graph_path=graph_path,
            seed=int(document.get("seed", DEFAULT_SEED)),
            timeout_s=float(document.get("timeout_s", DEFAULT_TIMEOUT_S)),
            iteration=document.get("iteration"),
        )


# ---------------------------------------------------------------------------
# the service
# ---------------------------------------------------------------------------
@dataclass
class HarnessEvalService:
    """Owns every E* invocation.  The runtime only ever reads a response."""

    root: Path
    campaign_id: str = "C_a1_probe"
    arm_id: str = "A_unknown"
    evaluator: str = "maxcut"
    e_star_script: Path = DEFAULT_E_STAR
    python: Path = DEFAULT_PYTHON
    seed: int = DEFAULT_SEED
    timeout_s: float = DEFAULT_TIMEOUT_S
    fidelity: str = "full"
    fraction: float = 1.0
    n: int = 26
    runs: int = 5
    runtime_budget_ms: float = 250.0
    harness_run_id: str = ""
    nonce: str = ""
    override: Dict[str, int] = field(default_factory=dict)
    overrides_ignored: bool = False
    #: how many E* invocations this process has made — the harness's own counter,
    #: which is what the budget enforcer reads (never the runtime's).
    evaluator_calls: int = 0
    calls: List[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.evaluator not in EVALUATORS:
            raise ServiceError(f"unknown evaluator {self.evaluator!r}; known: {sorted(EVALUATORS)}")
        self.spec = EVALUATORS[self.evaluator]
        if self.e_star_script == DEFAULT_E_STAR and self.spec["default_script"] != str(DEFAULT_E_STAR):
            self.e_star_script = Path(self.spec["default_script"])
        self.root = Path(self.root).resolve()
        self.harness_run_id = self.harness_run_id or f"a1-{int(time.time())}"
        self.nonce = self.nonce or secrets.token_hex(16)
        (self.root / "requests").mkdir(parents=True, exist_ok=True)
        (self.root / "responses").mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.root / "ledger.jsonl"
        self.identity = self._identity()
        self._write_json(self.root / "harness_identity.json", self.identity)

    # -- identity ---------------------------------------------------------
    def source_records(self) -> List[dict]:
        records = []
        for name in ("e_star.py", "e_star_child.py"):
            path = Path(self.e_star_script).parent / name
            records.append(
                {"path": name, "sha256": sha256_file(path), "bytes": path.stat().st_size}
            )
        return records

    def _identity(self) -> dict:
        """The harness's own statement of which evaluator it will run.

        `eid_star` is T1's frozen evaluator identity: the digest E*'s own
        `digest` subcommand prints, recomputed from the bytes on disk here so a
        third party can re-derive it (`a0/tasks/maxcut/e_star.py digest
        --value-only`).
        """
        digest = subprocess.run(
            [str(self.python), str(self.e_star_script), "digest"],
            capture_output=True,
            text=True,
            cwd=str(self.root),
            timeout=120,
        )
        if digest.returncode != 0:
            raise ServiceError(f"`e_star.py digest` failed: {digest.stderr.strip()}")
        payload = json.loads(digest.stdout)
        evaluator_source_sha256 = payload["evaluator_source_sha256"]
        return {
            "schema": IDENTITY_SCHEMA,
            "campaign_id": self.campaign_id,
            "arm_id": self.arm_id,
            "harness_run_id": self.harness_run_id,
            "nonce": self.nonce,
            "e_star_script": str(self.e_star_script),
            "e_star_script_sha256": sha256_file(self.e_star_script),
            "evaluator_source_sha256": evaluator_source_sha256,
            "eid_star": f"sha256:{evaluator_source_sha256}",
            "source_records": self.source_records(),
            "theta_e": {
                "seed": self.seed,
                "timeout_s": self.timeout_s,
                "fidelity": "full",
                "fraction": 1.0,
            },
            "owns_evaluation": True,
            "runtime_may_evaluate": False,
            "override": {k: int(v) for k, v in sorted(self.override.items())},
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    # -- evaluation -------------------------------------------------------
    def evaluate(self, request: EvalRequest) -> dict:
        """Run E*, author the outcome, book it, publish it.  In that order."""
        if self.spec["requires_graph"] and not request.graph_path:
            raise ServiceError(
                f"the {self.evaluator} evaluator needs a graph, but the request carries none"
            )
        out_dir = self.root / "state" / request.request_id
        out_dir.mkdir(parents=True, exist_ok=True)
        outcome_path = out_dir / "outcome.json"
        values = {
            "candidate": str(request.candidate_path),
            "graph": str(request.graph_path) if request.graph_path else "",
            "seed": str(request.seed),
            "timeout": str(request.timeout_s),
            "out": str(outcome_path),
            "resources": str(out_dir / "resources.json"),
            "state": str(self.root / "estate"),
            "fidelity": self.fidelity,
            "fraction": repr(float(self.fraction)),
            "n": str(self.n),
            "runs": str(self.runs),
            "budget": str(self.runtime_budget_ms),
        }
        command = [str(self.python), str(self.e_star_script)] + [
            values.get(token.strip("{}"), token) if token.startswith("{") else token
            for token in self.spec["argv"]
        ]
        started = time.monotonic()
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=str(self.root),
            timeout=request.timeout_s + 300.0,
        )
        wall = time.monotonic() - started
        self.evaluator_calls += 1
        if not outcome_path.is_file():
            raise ServiceError(
                f"E* wrote no outcome for {request.candidate_id} "
                f"(exit {proc.returncode}): {proc.stderr.strip()[:400]}"
            )
        outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
        field = self.spec["score_field"]
        true_value = _value_at(outcome, field)

        handed = outcome
        override_applied = False
        if not self.overrides_ignored and request.candidate_id in self.override:
            handed = _apply_override(outcome, field, int(self.override[request.candidate_id]))
            override_applied = _value_at(handed, field) != true_value

        graph_sha = outcome.get("graph_sha256")
        candidate_sha = outcome.get("candidate_source_sha256")
        binding = env.token_binding(
            candidate_id=request.candidate_id,
            candidate_sha256=candidate_sha,
            eid_star=self.identity["eid_star"],
            theta_e={
                "seed": request.seed,
                "timeout_s": request.timeout_s,
                "fidelity": self.fidelity,
                "fraction": self.fraction,
            },
            behaviour_digest_value=env.behaviour_digest(handed),
            canonical_digest=handed.get("canonical_digest"),
            interpreter=handed.get("interpreter"),
            evaluator_source_sha256=handed.get("evaluator_source_sha256"),
            harness_run_id=self.harness_run_id,
            nonce=self.nonce,
        )
        oid = env.token_oid(binding)
        measurement = {
            "schema": "a0.envelope.measurement_attestation/v1",
            "oid": oid,
            "harness_run_id": self.harness_run_id,
            "nonce": self.nonce,
            "eid_star": self.identity["eid_star"],
            "evaluator_source_sha256": handed.get("evaluator_source_sha256"),
            "candidate_sha256": candidate_sha,
            "behaviour_digest": env.behaviour_digest(handed),
            "interpreter": env.interpreter_of(handed),
            "theta_e": binding["theta_e"],
        }
        row = {
            "schema": LEDGER_SCHEMA,
            "seq": None,  # filled from the append
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "campaign_id": self.campaign_id,
            "arm_id": self.arm_id,
            "harness_run_id": self.harness_run_id,
            "request_id": request.request_id,
            "iteration": request.iteration,
            "candidate_id": request.candidate_id,
            "graph_id": outcome.get("graph_id"),
            "graph_sha256": graph_sha,
            "candidate_source_sha256": candidate_sha,
            "e_star_exit_code": proc.returncode,
            "status": handed.get("status"),
            "true_value": true_value,
            "handed_value": _value_at(handed, field),
            "override_applied": override_applied,
            "measurement_oid": oid,
            "evaluator": self.evaluator,
            "score_field": self.spec["score_field"],
            "evaluator_source_sha256": handed.get("evaluator_source_sha256"),
            "wall_sec": round(wall, 6),
            "harness_supplied": True,
        }
        seq = _fsync_append(self.ledger_path, row)
        row["seq"] = seq
        self.calls.append(row)

        response = {
            "schema": RESPONSE_SCHEMA,
            "request_id": request.request_id,
            "campaign_id": self.campaign_id,
            "arm_id": self.arm_id,
            "harness_run_id": self.harness_run_id,
            "candidate_id": request.candidate_id,
            "graph_id": outcome.get("graph_id"),
            "graph_sha256": graph_sha,
            "status": handed.get("status"),
            "score_field": field,
            "value": _value_at(handed, field),
            "outcome": handed,
            "measurement": measurement,
            "harness_supplied": True,
            "true_value": true_value,
            "handed_value": _value_at(handed, field),
            "override_applied": override_applied,
            "harness_ledger_seq": seq,
            "evaluator_calls": self.evaluator_calls,
        }
        self._publish(request.request_id, response)
        return response

    def _publish(self, request_id: str, response: dict) -> None:
        """Atomic publish: the runtime never observes a partial response."""
        target = self.root / "responses" / f"{request_id}.json"
        tmp = target.with_suffix(".json.partial")
        tmp.write_text(canonical_json(response), encoding="utf-8")
        os.replace(tmp, target)

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    # -- the serving loop -------------------------------------------------
    def serve(
        self,
        *,
        poll_sec: float = 0.05,
        max_requests: Optional[int] = None,
        stop_file: Optional[Path] = None,
    ) -> dict:
        """Consume requests until `stop_file` appears or `max_requests` is met."""
        served: List[str] = []
        errors: List[dict] = []
        requests_dir = self.root / "requests"
        seen: set = set()
        idle_since = time.monotonic()
        while True:
            if max_requests is not None and len(served) >= max_requests:
                break
            if stop_file is not None and Path(stop_file).exists() and not _pending(
                requests_dir, seen
            ):
                break
            progressed = False
            for path in sorted(requests_dir.glob("*.json")):
                request_id = path.stem
                if request_id in seen:
                    continue
                seen.add(request_id)
                progressed = True
                idle_since = time.monotonic()
                try:
                    request = EvalRequest.from_document(
                        json.loads(path.read_text(encoding="utf-8")), root=self.root
                    )
                    self.evaluate(request)
                    served.append(request_id)
                except Exception as exc:  # noqa: BLE001 - a bad request is a result
                    errors.append({"request_id": request_id, "error": f"{type(exc).__name__}: {exc}"})
                    self._publish(
                        request_id,
                        {
                            "schema": RESPONSE_SCHEMA,
                            "request_id": request_id,
                            "campaign_id": self.campaign_id,
                            "arm_id": self.arm_id,
                            "harness_supplied": True,
                            "status": "error",
                            "value": None,
                            "outcome": None,
                            "failure": {
                                "kind": "harness_evaluation_failed",
                                "detail": f"{type(exc).__name__}: {exc}",
                            },
                            "measurement": None,
                            "true_value": None,
                            "handed_value": None,
                            "override_applied": False,
                            "harness_ledger_seq": None,
                        },
                    )
            if not progressed:
                if stop_file is not None and Path(stop_file).exists():
                    break
                if time.monotonic() - idle_since > 3600.0:
                    break
                time.sleep(poll_sec)
        return {
            "schema": "a0.a1.harness_eval_service/v1",
            "harness_run_id": self.harness_run_id,
            "campaign_id": self.campaign_id,
            "arm_id": self.arm_id,
            "served": served,
            "errors": errors,
            "evaluator_calls": self.evaluator_calls,
            "ledger": str(self.ledger_path),
        }


def _pending(requests_dir: Path, seen: set) -> bool:
    return any(path.stem not in seen for path in requests_dir.glob("*.json"))


def _value_at(document: dict, path: str):
    """Read a score field from an Outcome, by dotted path.

    `cut_edges` is a top-level key of the max-cut Outcome (``INTERFACE.md`` §5);
    the plumbing Outcome keeps its objective under `fields.sum_radii`
    (``objective.value`` mirrors it). The path is declared per evaluator in
    ``EVALUATORS`` so neither shape is guessed at run time.
    """
    node = document
    for part in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def _apply_override(outcome: dict, field: str, value: int) -> dict:
    """Author an Outcome around a harness-chosen score value.

    The harness is the author of this document, so it says so in the document:
    `harness_authored` is set, the true value stays reachable through the
    response's `true_value`, and the evaluator's own `canonical_digest` is
    removed rather than left to describe bytes that no longer exist.
    """
    handed = json.loads(json.dumps(outcome))
    handed["harness_authored"] = True
    handed["harness_authored_overrides"] = {field: value, "was": _value_at(outcome, field)}
    if field == "cut_edges":
        handed[field] = value
        total = handed.get("edges_total")
        # The display field is regenerated with E*'s own integer-only renderer, not
        # with a float format: §5 makes `cut_fraction` a function of the two integers.
        if isinstance(total, int) and total > 0:
            handed["cut_fraction"] = _decimal_string(value, total)
    elif field.startswith("fields.") and isinstance(handed.get("fields"), dict):
        handed["fields"][field.split(".", 1)[1]] = value
        if isinstance(handed.get("objective"), dict):
            handed["objective"]["value"] = value
    handed.pop("canonical_digest", None)
    return handed


def _decimal_string(numerator: int, denominator: int) -> Optional[str]:
    """E*'s own renderer, imported rather than re-implemented."""
    module = _e_star_module()
    return module.decimal_string(numerator, denominator)


def _e_star_module():
    if str(MAXCUT_DIR) not in sys.path:
        sys.path.insert(0, str(MAXCUT_DIR))
    import e_star  # noqa: PLC0415 - path import on purpose

    return e_star


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harness_eval", description="harness-owned evaluation service for T1 (max-cut)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="consume requests until told to stop")
    _add_common(serve)
    serve.add_argument("--poll-sec", type=float, default=0.05)
    serve.add_argument("--max-requests", type=int, default=None)
    serve.add_argument("--stop-file", default=None)
    serve.add_argument("--summary-out", default=None)

    one = sub.add_parser("evaluate", help="evaluate one request file and exit")
    _add_common(one)
    one.add_argument("--request", required=True)
    return parser


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", required=True, help="the harness eval root (ABI directory)")
    parser.add_argument("--campaign-id", default="C_a1_probe")
    parser.add_argument("--arm-id", default="A_unknown")
    parser.add_argument("--evaluator", default="maxcut", choices=sorted(EVALUATORS),
                        help="which frozen evaluator this service owns")
    parser.add_argument("--e-star", default=None)
    parser.add_argument("--python", default=str(DEFAULT_PYTHON))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--fidelity", default="full")
    parser.add_argument("--fraction", type=float, default=1.0)
    parser.add_argument("--n", type=int, default=26)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--runtime-budget-ms", type=float, default=250.0)
    parser.add_argument("--harness-run-id", default=None)
    parser.add_argument("--nonce", default=None)
    parser.add_argument("--override", default=None,
                        help="json file: candidate_id -> the value to hand over")
    parser.add_argument(
        "--ignore-override",
        action="store_true",
        help="accept the override file but do not apply it (the control run)",
    )


def _service_from_args(args) -> HarnessEvalService:
    override = {}
    if args.override:
        override = {
            str(k): int(v)
            for k, v in json.loads(Path(args.override).read_text(encoding="utf-8")).items()
        }
    return HarnessEvalService(
        root=Path(args.root),
        campaign_id=args.campaign_id,
        arm_id=args.arm_id,
        evaluator=args.evaluator,
        e_star_script=Path(args.e_star) if args.e_star else Path(EVALUATORS[args.evaluator]["default_script"]),
        python=Path(args.python),
        seed=args.seed,
        timeout_s=args.timeout_s,
        fidelity=args.fidelity,
        fraction=args.fraction,
        n=args.n,
        runs=args.runs,
        runtime_budget_ms=args.runtime_budget_ms,
        harness_run_id=args.harness_run_id,
        nonce=args.nonce,
        override=override,
        overrides_ignored=bool(getattr(args, "ignore_override", False)),
    )


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    service = _service_from_args(args)
    if args.command == "evaluate":
        request = EvalRequest.from_document(
            json.loads(Path(args.request).read_text(encoding="utf-8")), root=service.root
        )
        response = service.evaluate(request)
        print(canonical_json(response), end="")
        return 0
    summary = service.serve(
        poll_sec=args.poll_sec,
        max_requests=args.max_requests,
        stop_file=Path(args.stop_file) if args.stop_file else None,
    )
    text = canonical_json(summary)
    if args.summary_out:
        Path(args.summary_out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
