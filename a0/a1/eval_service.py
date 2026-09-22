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

**The override, and the bound on it.**  ``--override <json>`` maps
``candidate_id -> integer``.  When a candidate is listed, the harness authors the
*handed* value of its score field from that map instead of from ``E*``, and
records both numbers.  This exists to make the A1 property "the runtime consumes,
it does not measure" observable: the runtime's selection must follow the
harness's number even when the harness's number is a deliberate lie.  The
override is never silent — ``harness_supplied`` and ``override_applied`` are on
every response and on every ledger row.

A harness-authored number is still a number *about this task*, so it is bounded
by the task where a bound exists: for ``maxcut``, ``0 <= cut_edges <= |E|``
(the Outcome's own ``edges_total``).  ``--override-mode`` decides what an
out-of-bound value does:

* ``bounded`` (the default) — the harness **refuses to publish** the value.  The
  request is answered with ``status: error`` / ``failure.kind:
  implausible_override``, ``value: null``, and the attempt is booked with
  ``override_rejected: true``.  A number the task cannot produce never reaches a
  runtime's selection, and no campaign can be scored on it.
* ``labelled_implausible`` — the value **is published**, with a ``plausibility``
  block on the response, on the handed Outcome and on the ledger row saying that
  it is out of bound and that it was accepted only because the harness was
  explicitly told to.  This is the mode the wiring probe uses: the deliberate
  wrong-value probe must keep working, because "the runtime consumes rather than
  measures" can only be shown with a number ``E*`` could not have produced —
  but it must be visible that the harness knew.

The bound is checked on *every* published value, not only on overrides: an
Outcome whose own number is outside ``[0, |E|]`` is a harness-side integrity
failure and is refused the same way (``failure.kind: implausible_outcome``).

**The candidate lane.**  ``E*`` is run inside
``a0/a1/candidate_sandbox.py`` (user + mount + network + PID namespace, the
repository/home hidden by tmpfs, the invocation's own inputs bound back) and is
given ``--net-isolate``, so a *hostile* candidate cannot reach any host, cannot
read ``~/gptapi.md`` or the stored reference partitions, and cannot read another
process's environment.  ``--candidate-isolation none`` exists for a labelled
control run; it says so in ``harness_identity.json`` and on every response.
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
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
ENVELOPE_DIR = REPO_ROOT / "a0" / "envelope"
MAXCUT_DIR = REPO_ROOT / "a0" / "tasks" / "maxcut"
A1_DIR = Path(__file__).resolve().parent

if str(ENVELOPE_DIR) not in sys.path:
    sys.path.insert(0, str(ENVELOPE_DIR))
import envelope as env  # noqa: E402  (a0/envelope/envelope.py, by path on purpose)

if str(A1_DIR) not in sys.path:
    sys.path.insert(0, str(A1_DIR))
import candidate_sandbox  # noqa: E402  (a0/a1/candidate_sandbox.py, by path on purpose)

REQUEST_SCHEMA = "a0.a1.eval_request/v1"
RESPONSE_SCHEMA = "a0.a1.harness_outcome/v1"
IDENTITY_SCHEMA = "a0.a1.harness_identity/v1"
LEDGER_SCHEMA = "a0.a1.harness_eval_ledger/v1"
PLAUSIBILITY_SCHEMA = "a0.a1.plausibility/v1"

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
            # §4's "inject no network", passed by the *harness* rather than left
            # to the caller: the frozen argv used to omit it, so a candidate
            # evaluated through this service ran in the host's network namespace.
            # The sandbox already has no route, so this is the second closure of
            # the same door, made by the candidate's own loader.
            "--net-isolate",
        ],
        "requires_graph": True,
        "score_field": "cut_edges",
        "default_script": str(MAXCUT_DIR / "e_star.py"),
        #: The task's own bound on a score: every Max-Cut outcome carries
        #: `edges_total`, and a cut is a subset of those edges.
        "score_bound": {"field": "edges_total", "lower": 0,
                        "rule": "0 <= cut_edges <= edges_total"},
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
        #: No frozen bound is available for this evaluator (the plumbing
        #: Outcome carries no `|E|`-like denominator to bound `sum_radii` by),
        #: so there is nothing here to enforce. Named rather than implied:
        #: a score from this lane is *not* bounded, and D-A1-11 says so.
        "score_bound": None,
    },
}

#: The two answers to an out-of-bound harness-supplied score.
OVERRIDE_MODES = ("bounded", "labelled_implausible")

#: How the candidate lane is closed. `sandbox` is the default; `none` exists so
#: that a *labelled* control run can reproduce the pre-fix lane, and it says so
#: in the identity, on every response and on every ledger row.
CANDIDATE_ISOLATION = ("sandbox", "none")

#: `E*` and every candidate it spawns get this environment: no credential, no
#: proxy variable, nothing the harness itself was launched with. The candidate's
#: environment is narrower still (a0/tasks/maxcut/e_star_child.py §4).
EVALUATOR_ENV_KEEP = ("HOME", "LANG")
EVALUATOR_PATH = "/usr/bin:/bin"

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
    #: what an out-of-bound override does: refuse it, or publish it labelled
    #: (`OVERRIDE_MODES`). The default is to refuse.
    override_mode: str = "bounded"
    #: how E* and every candidate it spawns are confined (`CANDIDATE_ISOLATION`).
    candidate_isolation: str = "sandbox"
    hidden_roots: Sequence[str] = candidate_sandbox.DEFAULT_HIDDEN_ROOTS
    #: how many E* invocations this process has made — the harness's own counter,
    #: which is what the budget enforcer reads (never the runtime's).
    evaluator_calls: int = 0
    calls: List[dict] = field(default_factory=list)
    #: one receipt per invocation: what the lane's namespace actually hid and
    #: restored, and its own self-check. Written by the sandbox before E* runs.
    sandbox_receipts: List[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.evaluator not in EVALUATORS:
            raise ServiceError(f"unknown evaluator {self.evaluator!r}; known: {sorted(EVALUATORS)}")
        if self.override_mode not in OVERRIDE_MODES:
            raise ServiceError(f"unknown override mode {self.override_mode!r}; known: {list(OVERRIDE_MODES)}")
        if self.candidate_isolation not in CANDIDATE_ISOLATION:
            raise ServiceError(
                f"unknown candidate isolation {self.candidate_isolation!r}; known: {list(CANDIDATE_ISOLATION)}"
            )
        if self.candidate_isolation == "sandbox" and not candidate_sandbox.available():
            raise ServiceError(
                "`unshare` is not on PATH; the candidate lane cannot be closed and this service "
                "refuses to run in an open topology (use --candidate-isolation none to say so "
                "explicitly, which is recorded as unsafe)"
            )
        self.spec = EVALUATORS[self.evaluator]
        if self.e_star_script == DEFAULT_E_STAR and self.spec["default_script"] != str(DEFAULT_E_STAR):
            self.e_star_script = Path(self.spec["default_script"])
        self.root = Path(self.root).resolve()
        # The script and the interpreter are *not* resolved through symlinks:
        # `--e-star`/`--python` name the launcher, and a virtualenv's
        # `bin/python` is a symlink whose *path* is what makes `sys.prefix` the
        # venv. Resolving either would silently swap the interpreter's identity.
        self.e_star_script = Path(self.e_star_script)
        if not self.e_star_script.is_absolute():
            self.e_star_script = self.root / self.e_star_script
        self.python = Path(self.python)
        self.harness_run_id = self.harness_run_id or f"a1-{int(time.time())}"
        self.nonce = self.nonce or secrets.token_hex(16)
        (self.root / "requests").mkdir(parents=True, exist_ok=True)
        (self.root / "responses").mkdir(parents=True, exist_ok=True)
        (self.state_dir).mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.root / "ledger.jsonl"
        self.identity = self._identity()
        self._write_json(self.root / "harness_identity.json", self.identity)

    @property
    def state_dir(self) -> Path:
        """E*'s state root: staged candidates, invocation records, scratch."""
        return self.root / "estate"

    # -- identity ---------------------------------------------------------
    def source_records(self) -> List[dict]:
        records = []
        for name in ("e_star.py", "e_star_child.py"):
            path = Path(self.e_star_script).parent / name
            records.append(
                {"path": name, "sha256": sha256_file(path), "bytes": path.stat().st_size}
            )
        return records

    def isolation_identity(self) -> dict:
        """What confines the candidate lane, as a fact about this process."""
        if self.candidate_isolation == "none":
            return {
                "mechanism": "none",
                "labelled_unsafe": True,
                "reason": "started with --candidate-isolation none (a control run)",
                "candidate_can_reach_the_network": True,
                "candidate_can_read_the_host_filesystem": True,
            }
        module = Path(candidate_sandbox.__file__).resolve()
        return {
            "mechanism": "unshare -rmnpf --mount-proc (user+mount+network+pid namespace)",
            "module": "a0/a1/candidate_sandbox.py",
            "module_sha256": sha256_file(module),
            "hidden_roots": [str(root) for root in self.hidden_roots],
            "hidden_by": "an empty tmpfs per root; the invocation's own inputs are bound back",
            "candidate_sees": [
                "its staged bytes below the state dir",
                "the one graph named by the request",
                "its own scratch directory",
                "the invocation's state and out directory",
                "the evaluator's own two files and the interpreter",
            ],
            "network": "fresh netns with no route; E* is additionally given --net-isolate",
            "processes": "fresh pid namespace and a fresh /proc: no other process is visible",
            "net_isolate_flag": "--net-isolate" in self.spec["argv"],
            "labelled_unsafe": False,
            "self_check": "written per invocation to <out>/sandbox_receipt.json",
        }

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
            "override_mode": self.override_mode,
            "score_bound": self.spec["score_bound"],
            "candidate_isolation": self.isolation_identity(),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

    # -- evaluation -------------------------------------------------------
    def _evaluator_environment(self) -> Dict[str, str]:
        """E*'s environment: no credential, no proxy variable, minimal PATH.

        The service used to hand E* its own environment, so everything the
        harness process had been launched with (including the provider key) was
        inherited by the evaluator and, through `/proc/<ppid>/environ`, readable
        by the candidate it spawned. The candidate lane's PID namespace closes
        that path from the candidate's side; this closes it at the source, so
        the harness can be launched with the key present and still not pass it
        down. `HOME` and `LANG` are kept verbatim because §4's path handling and
        the candidate's own environment refer to them.
        """
        environment = {name: os.environ[name] for name in EVALUATOR_ENV_KEEP if name in os.environ}
        environment["PATH"] = EVALUATOR_PATH
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["TMPDIR"] = "/tmp"
        return environment

    def _allow_paths(self, request: EvalRequest, out_dir: Path) -> List[Path]:
        """Everything the invocation legitimately needs, and nothing else.

        This is the candidate lane's whole allow-list: the evaluator's two
        files, the interpreter (and its virtualenv root, when it has one), the
        one graph the request names, the candidate's own bytes, and the two
        directories the harness writes into. A path outside the hidden roots
        needs no entry; a path inside them that is missing here will not exist
        inside the lane.
        """
        allow: List[Path] = [self.e_star_script]
        child = self.e_star_script.parent / "e_star_child.py"
        if child.is_file():
            allow.append(child)
        if request.graph_path is not None:
            allow.append(request.graph_path)
        allow.append(request.candidate_path)
        allow.append(out_dir)
        allow.append(self.state_dir)
        allow.append(self.python)
        prefix_root = self.python.parent.parent
        if (prefix_root / "pyvenv.cfg").is_file():
            allow.append(prefix_root)
        return allow

    def evaluate(self, request: EvalRequest) -> dict:
        """Run E*, author the outcome, bound it, book it, publish it.  In that order."""
        if self.spec["requires_graph"] and not request.graph_path:
            raise ServiceError(
                f"the {self.evaluator} evaluator needs a graph, but the request carries none"
            )
        out_dir = self.root / "state" / request.request_id
        out_dir.mkdir(parents=True, exist_ok=True)
        outcome_path = out_dir / "outcome.json"
        receipt_path = out_dir / "sandbox_receipt.json"
        values = {
            "candidate": str(request.candidate_path),
            "graph": str(request.graph_path) if request.graph_path else "",
            "seed": str(request.seed),
            "timeout": str(request.timeout_s),
            "out": str(outcome_path),
            "resources": str(out_dir / "resources.json"),
            "state": str(self.state_dir),
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
        run_command = command
        if self.candidate_isolation == "sandbox":
            run_command = candidate_sandbox.prefix(
                command,
                allow=self._allow_paths(request, out_dir),
                receipt=receipt_path,
                hidden_roots=self.hidden_roots,
                python=self.python,
            )
        started = time.monotonic()
        proc = subprocess.run(
            run_command,
            capture_output=True,
            text=True,
            cwd=str(self.root),
            timeout=request.timeout_s + 300.0,
            env=self._evaluator_environment(),
        )
        wall = time.monotonic() - started
        self.evaluator_calls += 1
        if receipt_path.is_file():
            try:
                self.sandbox_receipts.append(json.loads(receipt_path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                self.sandbox_receipts.append({"pass": False, "error": "receipt is not JSON"})
        if not outcome_path.is_file():
            raise ServiceError(
                f"E* wrote no outcome for {request.candidate_id} "
                f"(exit {proc.returncode}): {proc.stderr.strip()[:400]}"
            )
        outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
        field = self.spec["score_field"]

        true_value = _value_at(outcome, field)
        bound = _score_bound(outcome, self.spec["score_bound"])

        handed = outcome
        override_applied = False
        refusal: Optional[dict] = None
        requested = None if self.overrides_ignored else self.override.get(request.candidate_id)
        plausibility = _plausibility(bound=bound, value=true_value, mode=self.override_mode,
                                     verdict=_verdict_for(true_value, bound))
        if _within_bound(true_value, bound) is False:
            # E*'s own number is outside the task's own bound: a harness-side
            # integrity failure, so no score is published for it.
            refusal = {
                "kind": "implausible_outcome",
                "detail": (f"the evaluator's own {field} = {true_value!r} is outside "
                           f"[{bound['lower']}, {bound['upper']}] ({bound['rule']})"),
            }
        elif requested is not None:
            requested = int(requested)
            if _within_bound(requested, bound) is False and self.override_mode == "bounded":
                # The bound is enforced *here*, at the boundary where the service
                # publishes a value: an impossible number never reaches a
                # runtime's selection.
                refusal = {
                    "kind": "implausible_override",
                    "detail": (f"the harness was asked to hand {requested} for "
                               f"{request.candidate_id!r}, outside [{bound['lower']}, "
                               f"{bound['upper']}] ({bound['rule']}); --override-mode "
                               f"labelled_implausible would publish it as a labelled lie"),
                    "requested_value": requested,
                }
                plausibility = _plausibility(bound=bound, value=requested, mode=self.override_mode,
                                             verdict="refused_out_of_bound")
            else:
                handed = _apply_override(outcome, field, requested)
                override_applied = _value_at(handed, field) != true_value
                plausibility = _plausibility(
                    bound=bound, value=_value_at(handed, field), mode=self.override_mode,
                    verdict=("within_bound" if _within_bound(_value_at(handed, field), bound) is not False
                             else "accepted_labelled_out_of_bound"),
                )
                if plausibility["verdict"] == "accepted_labelled_out_of_bound":
                    handed["plausibility"] = plausibility

        if refusal is not None:
            return self._refuse(request, outcome=outcome, field=field, true_value=true_value,
                                bound=bound, plausibility=plausibility, refusal=refusal,
                                exit_code=proc.returncode, wall=wall)

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
            "plausibility": plausibility,
            "candidate_isolation": self.candidate_isolation,
            "override_mode": self.override_mode,
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
            "plausibility": plausibility,
            "candidate_isolation": self.candidate_isolation,
            "override_mode": self.override_mode,
            "harness_ledger_seq": seq,
            "evaluator_calls": self.evaluator_calls,
        }
        self._publish(request.request_id, response)
        return response

    def _refuse(self, request: EvalRequest, *, outcome: dict, field: str, true_value: Any,
                bound: Optional[dict], plausibility: dict, refusal: dict, exit_code: int,
                wall: float) -> dict:
        """Book the evaluation, publish no score, and say exactly why.

        A refusal is not a failure to evaluate: `E*` ran and its true value is
        recorded, because the harness's own counter is what the budget reads. What
        is withheld is the *number a runtime could act on* — the response carries
        `value: null` and no Outcome at all, so a selection cannot see it.
        """
        row = {
            "schema": LEDGER_SCHEMA,
            "seq": None,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "campaign_id": self.campaign_id,
            "arm_id": self.arm_id,
            "harness_run_id": self.harness_run_id,
            "request_id": request.request_id,
            "iteration": request.iteration,
            "candidate_id": request.candidate_id,
            "graph_id": outcome.get("graph_id"),
            "graph_sha256": outcome.get("graph_sha256"),
            "candidate_source_sha256": outcome.get("candidate_source_sha256"),
            "e_star_exit_code": exit_code,
            "status": "error",
            "true_value": true_value,
            "handed_value": None,
            "override_applied": False,
            "override_rejected": True,
            "refusal": refusal,
            "measurement_oid": None,
            "evaluator": self.evaluator,
            "score_field": field,
            "evaluator_source_sha256": outcome.get("evaluator_source_sha256"),
            "wall_sec": round(wall, 6),
            "harness_supplied": True,
            "plausibility": plausibility,
            "candidate_isolation": self.candidate_isolation,
            "override_mode": self.override_mode,
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
            "graph_sha256": outcome.get("graph_sha256"),
            "status": "error",
            "score_field": field,
            "value": None,
            "outcome": None,
            "measurement": None,
            "failure": refusal,
            "harness_supplied": True,
            "true_value": true_value,
            "handed_value": None,
            "override_applied": False,
            "override_rejected": True,
            "plausibility": plausibility,
            "candidate_isolation": self.candidate_isolation,
            "override_mode": self.override_mode,
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
            "candidate_isolation": self.candidate_isolation,
            "override_mode": self.override_mode,
            # The lane's own self-check, one per E* invocation: "the candidate ran
            # closed" is a recorded measurement, not a claim about the flags.
            "sandbox_self_checks": [
                {"pass": receipt.get("pass"),
                 "hidden_roots": receipt.get("hidden_roots"),
                 "self_check": receipt.get("self_check"),
                 "error": receipt.get("error")}
                for receipt in self.sandbox_receipts
            ],
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


# ---------------------------------------------------------------------------
# the plausibility bound on a harness-supplied score
# ---------------------------------------------------------------------------
def _score_bound(outcome: dict, spec: Optional[dict]) -> Optional[dict]:
    """The task's own bound on the score field, with its concrete numbers.

    `spec` is declared per evaluator in `EVALUATORS`; the *numbers* come from the
    Outcome the evaluator itself wrote, so the bound is the evaluator's own
    statement about this instance (`edges_total`) rather than a constant this
    service keeps. An evaluator without a declared bound (the plumbing one)
    returns None, i.e. "no bound exists here", which is recorded rather than
    guessed at.
    """
    if not spec:
        return None
    total = outcome.get(str(spec["field"]))
    if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
        return None
    return {
        "field": str(spec["field"]),
        "lower": int(spec["lower"]),
        "upper": int(total),
        "rule": str(spec["rule"]),
        "source": f"the Outcome's own {spec['field']}",
    }


def _within_bound(value: Any, bound: Optional[dict]) -> Optional[bool]:
    """`True`/`False`, or `None` when there is no number or no bound to test."""
    if bound is None or value is None:
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return False
    if number != value:  # §5's metric is an integer; 3.5 is not a cut
        return False
    return bound["lower"] <= number <= bound["upper"]


def _verdict_for(value: Any, bound: Optional[dict]) -> str:
    """The one word a reader needs: was the number inside the task's bound?"""
    state = _within_bound(value, bound)
    if state is True:
        return "within_bound"
    if state is False:
        return "refused_out_of_bound"
    return "no_number" if value is None else "no_bound_declared"


def _plausibility(*, bound: Optional[dict], value: Any, mode: str, verdict: str) -> dict:
    """What the harness knew about a number when it published (or refused) it."""
    document = {
        "schema": PLAUSIBILITY_SCHEMA,
        "bounded": bound is not None,
        "mode": mode,
        "verdict": verdict,
        "value": value,
    }
    if bound is not None:
        document["bound"] = bound
        document["within_bound"] = _within_bound(value, bound)
    return document


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
    parser.add_argument(
        "--override-mode", default="bounded", choices=list(OVERRIDE_MODES),
        help="what an override outside the task's bound does: refuse it (the default) or "
             "publish it as a labelled lie (`labelled_implausible`)",
    )
    parser.add_argument(
        "--candidate-isolation", default="sandbox", choices=list(CANDIDATE_ISOLATION),
        help="`sandbox` runs E* (and every candidate it spawns) in a user+mount+network+PID "
             "namespace with the repository hidden; `none` is a labelled control run",
    )
    parser.add_argument(
        "--hide-root", action="append", default=None,
        help=f"a root the candidate lane hides (repeatable; default: "
             f"{', '.join(candidate_sandbox.DEFAULT_HIDDEN_ROOTS)})",
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
        override_mode=getattr(args, "override_mode", "bounded"),
        candidate_isolation=getattr(args, "candidate_isolation", "sandbox"),
        hidden_roots=tuple(getattr(args, "hide_root", None) or candidate_sandbox.DEFAULT_HIDDEN_ROOTS),
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
