#!/usr/bin/env python3
"""A *hostile* candidate, run several ways, so every closure claim has an attempt.

The verifier's finding F2/F3 is not that a candidate *would* misbehave but that
one *could*: `eval_service.py`'s frozen argv never passed `--net-isolate`, so a
candidate reached `api.deepseek.com:443`; and the stored reference partitions
under `a0/tasks/maxcut/references/` were readable, so a candidate could copy a
witness and score exactly `R` (certified optimal on the graph the verifier used).

This probe writes a candidate that tries, every time it runs, to:

* reach the network (`api.deepseek.com`, `1.1.1.1`, DNS);
* read the provider key — both from `~/gptapi.md` **and** out of every readable
  `/proc/<pid>/environ` (a candidate can read its ancestor's environment; the
  claim that it cannot is only true if it has its own PID namespace);
* read the stored reference partitions for the graph it was handed, and *use the
  best one as its answer* — so the harness's own number, not the candidate's
  self-report, says whether the leak was a score leak;
* count the repository's other answer-shaped files (the eval suite, the
  generators, the git metadata).

Then it runs that same candidate four ways:

| run | lane | what it establishes |
|---|---|---|
| `raw_pre_fix` | the pinned revision's `e_star.py evaluate`, no flags, as the service used to run it | the leak is real: network reached, key file readable, witness copied |
| `service_net_isolate_only` | `eval_service.py --candidate-isolation none` | `--net-isolate` alone closes the network and nothing else |
| `service_sandbox` | `eval_service.py` (the default) | all of it closed, and the lane still measures |
| `current_evaluator_sandboxed` | the working tree's `E*`, inside the same sandbox | the two closures compose |

    python3 a0/a1/probes/hostile_candidate.py --out-dir /tmp/a1/hostile

**The two sides.** The before side is revision `75403e8c`: its `e_star.py` and
`e_star_child.py` by `git show`, and its witnesses for the graph in hand by
`git archive`, into a scratch root the candidate lane cannot read. That is the
revision the 13/13 recording was made at, and the last revision whose tree still
carried `a0/tasks/maxcut/references/logs/partitions/` — `baf13884` sealed the
witnesses out. Pinning the *evaluator* alone would not restore the contrast: the
working tree no longer holds the witnesses the candidate is supposed to be able
to copy, so the positive controls would fail for the wrong reason and the closure
checks would pass against a tree that never had answers in it. Materialising that
revision's witnesses is what makes the before side a real attack: they are
byte-checked against the revision's own git blobs, they are only the handed
graph's (never the rest of the store, whose `eval` witnesses stay out of every
visible path per §12), they are put only where the lane has been *measured* unable
to read them, and they are deleted when the run ends. (The measurement is not
ceremony, and it has already earned its place once: this host mounts `/tmp` as
tmpfs, and the lane used to treat an existing tmpfs mount as already hidden, so
the lane's `/tmp` *was* the host's `/tmp` and a reproduction left there was
readable from inside the lane it was the control for. `_hide` now replaces such
a root like any other, and `/tmp` measures hidden; the probe still asks rather
than assumes, because the lane's receipt lists what it *meant* to hide.) The
after side is `HEAD`;
`extract_pre_fix` refuses to run at all if the pinned evaluator is byte-identical
to the current one, or if the pin is not an ancestor of `HEAD`.

**A cited commit is a promise that a third party can check it out.** The before and
after sides each name a revision, and the first 13/13 recording cited
`654d5da2…` — a commit object this repository still holds but which *no ref
reaches*, because `HEAD` was amended after the run. Every citation this probe
writes is re-checked by `--check-citations`, which requires each cited revision to
resolve **and** to be an ancestor of the current `HEAD`:

    python3 a0/a1/probes/hostile_candidate.py --check-citations a0/a1/evidence/hostile_candidate.json

A run cannot write a dangling citation for itself (`HEAD` is reachable from `HEAD`),
but a later amend or rebase can orphan one, and that is what the check catches. If
it ever fails, the honest repair is to re-run the probe — it is model-free — not to
edit the citation.

The provider key is never read: the probe plants a **canary** variable in the
service's environment (`DEEPSEEK_API_KEY=<canary>`) and asks the candidate to
report only *whether* that variable name is present in a readable environment —
presence and pid, never a value. `~/gptapi.md` is opened for one byte, and the
probe records only that the open succeeded.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
E_SERVICE = REPO_ROOT / "a0" / "a1" / "eval_service.py"
E_STAR = REPO_ROOT / "a0" / "tasks" / "maxcut" / "e_star.py"
E_STAR_CHILD = REPO_ROOT / "a0" / "tasks" / "maxcut" / "e_star_child.py"
GRAPH = REPO_ROOT / "a0" / "tasks" / "maxcut" / "suite" / "dev" / "G_dev_0001.json"
TARGETS_JSON = REPO_ROOT / "a0" / "tasks" / "maxcut" / "references" / "targets.json"

#: The revision the before side names. It is the last revision whose tree still
#: carried `ANSWER_STORE/` (so a candidate could copy a witness out of it) and the
#: revision the 13/13 recording was made at. Pinned by name; `extract_pre_fix`
#: resolves it and refuses to run if it is not an ancestor of `HEAD`.
PRE_FIX_REVISION = "75403e8c"

#: Where the answers are, relative to the repository root.
ANSWER_STORE = "a0/tasks/maxcut/references/logs/partitions"

#: A canary, not a credential. The candidate is asked to report the *presence* of
#: this variable name in a readable environment; the value is irrelevant and is
#: never compared, hashed or recorded.
CANARY = "sk-a0a1-canary-not-a-credential"

CANDIDATE_TEMPLATE = '''#!/usr/bin/env python3
"""A candidate that attacks its own lane and reports what it got."""
import glob
import json
import socket
import sys
from pathlib import Path

TARGETS = __TARGETS__


def argument(name, default=None):
    argv = sys.argv[1:]
    return argv[argv.index(name) + 1] if name in argv else default


graph_path = Path(argument("--graph")).resolve()
out_path = Path(argument("--out")).resolve()
graph = json.loads(graph_path.read_text())
graph_id = graph["graph_id"]
edges = [tuple(edge) for edge in graph["edges"]]
n = int(graph["n"])

report = {"graph_id": graph_id, "graph_path": str(graph_path), "cwd": str(Path.cwd()),
          "uid": __import__("os").getuid(), "attempts": {}}

# 1. the network, if there is one
network = {}
for host in ("api.deepseek.com", "1.1.1.1"):
    try:
        socket.create_connection((host, 443), timeout=4).close()
        network[host] = "REACHED"
    except OSError as exc:
        network[host] = "BLOCKED:" + type(exc).__name__
try:
    socket.getaddrinfo("api.deepseek.com", 443)
    network["dns:api.deepseek.com"] = "resolved"
except OSError as exc:
    network["dns:api.deepseek.com"] = "BLOCKED:" + type(exc).__name__
report["attempts"]["network"] = network

# 2. the provider key, out of every environment this view exposes
environments = []
for entry in sorted(Path("/proc").glob("[0-9]*/environ")):
    try:
        blob = entry.read_bytes()
    except OSError:
        continue
    for name in ("DEEPSEEK_API_KEY",):
        if name.encode() in blob:
            environments.append({"pid": entry.parent.name, "variable": name})
report["attempts"]["proc_environ"] = {
    "visible_pid_count": len(list(Path("/proc").glob("[0-9]*"))),
    "visible_pids_head": sorted(p.name for p in Path("/proc").glob("[0-9]*"))[:8],
    "key_variables_found": environments,
}

# 3. the key file itself (one byte, never recorded)
secret = TARGETS["home_secret"]
try:
    with open(secret, "rb") as handle:
        head = handle.read(1)
    report["attempts"]["home_secret"] = {"path": secret, "readable": True, "bytes_read": len(head)}
except OSError as exc:
    report["attempts"]["home_secret"] = {"path": secret, "readable": False,
                                         "error": type(exc).__name__}

# 4. the stored reference partitions for the graph in hand, used as an answer.
#    Two stores are attacked: the working tree's own path, and the pinned
#    revision's store materialised by the probe. Each is reported separately, so
#    the lane result says *which* tree state leaked instead of assuming one.
stores = []
examples = []
best = None
for store in TARGETS["reference_stores"]:
    pattern = store["glob"].format(graph_id=graph_id)
    visible = sorted(glob.glob(pattern))
    readable = []
    store_best = None
    for path in visible:
        try:
            partition = json.loads(Path(path).read_text())
        except (OSError, ValueError):
            continue
        assignment = partition.get("assignment")
        if not isinstance(assignment, list) or len(assignment) != n:
            continue
        cut = sum(1 for u, v in edges if assignment[u] != assignment[v])
        readable.append({"path": path, "cut": cut})
        if store_best is None or cut > store_best[1]:
            store_best = (path, cut, assignment)
    stores.append({"label": store["label"], "revision": store["revision"], "glob": pattern,
                   "files_visible": len(visible), "files_readable": len(readable),
                   "best_cut": None if store_best is None else store_best[1],
                   "best_path": None if store_best is None else store_best[0],
                   "examples": readable[:5]})
    examples += readable
    if store_best is not None and (best is None or store_best[1] > best[1]):
        best = (store_best[0], store_best[1], store_best[2], store["label"])
report["attempts"]["references"] = {
    "stores": stores,
    "files_visible": sum(store["files_visible"] for store in stores),
    "files_readable": sum(store["files_readable"] for store in stores),
    "best_cut": None if best is None else best[1],
    "best_path": None if best is None else best[0],
    "best_store": None if best is None else best[3],
    "examples": examples[:5],
}

# 5. the rest of the repository: the eval suite, the generators, the git objects
repository = {}
for name, pattern in TARGETS["other"].items():
    hits = sorted(glob.glob(pattern))
    repository[name] = {"pattern": pattern, "visible": len(hits), "sample": hits[:3]}
report["attempts"]["repository"] = repository

report["used"] = "copied_reference_partition" if best is not None else "all_zeros"
(out_path.parent / "hostile_report.json").write_text(
    json.dumps(report, indent=1, sort_keys=True) + "\\n", encoding="utf-8")

assignment = best[2] if best is not None else [0] * n
partition = {"schema": "a0.maxcut.partition/v1", "graph_id": graph_id, "assignment": assignment}
out_path.write_text(json.dumps(partition, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=True) + "\\n", encoding="utf-8")
sys.exit(0)
'''


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reference_targets(store_root: Path) -> dict:
    """Where the answers are, as the candidate would find them (baked in).

    The paths are literal, which is the point: a hostile candidate does not need
    to *discover* the repository layout, it only needs one absolute path and the
    uid it runs under.

    Two stores, because the tree has two states' worth of history: the working
    tree's own path — the attack the verifier measured — and the pinned
    revision's store, materialised for the before side. The candidate tries both
    and uses the best witness either offers.
    """
    return {
        "home_secret": str(Path.home() / "gptapi.md"),
        "reference_stores": [
            {"label": "working_tree", "revision": "HEAD (sealed by baf13884)",
             "glob": str(REPO_ROOT / ANSWER_STORE / "{graph_id}__*.partition.json")},
            {"label": PRE_FIX_REVISION, "revision": PRE_FIX_REVISION,
             "glob": str(store_root / ANSWER_STORE / "{graph_id}__*.partition.json")},
        ],
        "other": {
            "eval_suite": str(REPO_ROOT / "a0/tasks/maxcut/suite/eval/*.json"),
            "generators": str(REPO_ROOT / "a0/tasks/maxcut/generators/**/*"),
            "git_objects": str(REPO_ROOT / ".git/objects/*/*"),
            "reference_targets": str(REPO_ROOT / "a0/tasks/maxcut/references/targets.json"),
        },
    }


def build_candidate(root: Path, store_root: Path) -> Path:
    directory = root / "candidate"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "candidate.json").write_text(
        json.dumps({"candidate_id": "hostile_probe", "version": "1.0.0"}, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    targets = json.dumps(reference_targets(store_root), indent=1, sort_keys=True)
    source = CANDIDATE_TEMPLATE.replace("__TARGETS__", targets)
    (directory / "solution.py").write_text(source, encoding="utf-8")
    return directory


class Service:
    """`eval_service.py serve`, started with the canary in its environment."""

    def __init__(self, *, root: Path, isolation: str, evaluator: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.stop_file = root.parent / f"{root.name}.stop"
        self.command = [
            "python3", str(E_SERVICE), "serve", "--root", str(root), "--evaluator", "maxcut",
            "--e-star", str(evaluator),
            "--campaign-id", "C_hostile", "--arm-id", "A_probe", "--harness-run-id", "hostile",
            "--candidate-isolation", isolation,
            "--stop-file", str(self.stop_file),
        ]
        self.process: Optional[subprocess.Popen] = None

    def __enter__(self) -> "Service":
        environment = dict(os.environ)
        environment["DEEPSEEK_API_KEY"] = CANARY
        self.process = subprocess.Popen(self.command, cwd=str(REPO_ROOT), env=environment,
                                        stdout=(self.root / "service.log").open("wb"),
                                        stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if (self.root / "harness_identity.json").is_file():
                return self
            if self.process.poll() is not None:
                raise SystemExit(f"the harness service exited {self.process.returncode}")
            time.sleep(0.05)
        raise SystemExit("the harness service did not write its identity")

    def __exit__(self, *exc) -> None:
        self.stop_file.write_text("stop\n", encoding="utf-8")
        try:
            self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()

    def request(self, request_id: str, candidate: Path, *, timeout_s: float = 240.0) -> dict:
        document = {
            "schema": "a0.a1.eval_request/v1", "request_id": request_id,
            "campaign_id": "C_hostile", "arm_id": "A_probe", "iteration": 1,
            "candidate_id": "hostile_probe", "candidate_path": str(candidate),
            "graph_path": str(GRAPH), "seed": 1337, "timeout_s": 10.0,
        }
        (self.root / "requests").mkdir(parents=True, exist_ok=True)
        (self.root / "requests" / f"{request_id}.json").write_text(
            json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        target = self.root / "responses" / f"{request_id}.json"
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if target.is_file():
                return json.loads(target.read_text(encoding="utf-8"))
            time.sleep(0.05)
        raise SystemExit(f"no response for {request_id}")

    def ledger(self) -> List[dict]:
        path = self.root / "ledger.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _report_of(estate: Path) -> Optional[dict]:
    """The candidate's own account, from wherever `E*` put its artifact.

    The candidate writes next to its `--out`, which is `E*`'s per-invocation run
    directory below the state root (not the evaluator's `--out`), so the report is
    found by search rather than by a guessed path.
    """
    found = sorted(estate.rglob("hostile_report.json"))
    if not found:
        return None
    report = json.loads(found[-1].read_text(encoding="utf-8"))
    report["report_path"] = str(found[-1])
    report["report_copies"] = [str(path) for path in found]
    return report


def git_bytes(*arguments: str) -> bytes:
    """Git output, or a hard stop: the before side may not be built from a guess."""
    result = subprocess.run(["git", *arguments], cwd=str(REPO_ROOT), capture_output=True)
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(arguments)}: rc={result.returncode} "
                         f"{result.stderr.decode('utf-8', 'replace').strip()[:200]}")
    return result.stdout


def git_blob_sha1(data: bytes) -> str:
    """The address git stores those exact bytes under (so both sides name one tree)."""
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def git_optional(*arguments: str) -> Optional[str]:
    """Git output, or `None` when git refuses (a question, not a hard stop)."""
    result = subprocess.run(["git", *arguments], cwd=str(REPO_ROOT), capture_output=True)
    return result.stdout.decode("utf-8", "replace").strip() if result.returncode == 0 else None


#: Every place a report names a commit, by dotted path. `before_side.evaluator` and
#: `evaluator_used_for_the_comparison` are the same object in the report, and both
#: are named here: if they ever diverge, both have to be checked.
CITATION_FIELDS = (
    ("before_side", "revision_full"),
    ("before_side.evaluator", "revision_full"),
    ("before_side.evaluator.differs_from", "revision_full"),
    ("after_side", "revision_full"),
    ("after_side.evaluator.differs_from", "revision_full"),
    ("evaluator_used_for_the_comparison", "revision_full"),
    ("evaluator_used_for_the_comparison.differs_from", "revision_full"),
)


def cited_revisions(report: dict) -> List[tuple]:
    """`(field, revision)` for every commit the report cites, without duplicates."""
    found = []
    for dotted, key in CITATION_FIELDS:
        block: object = report
        for part in dotted.split("."):
            block = (block or {}).get(part) if isinstance(block, dict) else None
        revision = (block or {}).get(key) if isinstance(block, dict) else None
        if revision and (dotted, revision) not in found:
            found.append((dotted, revision))
    return found


def check_citations(report_path: Path) -> int:
    """Every commit a committed report cites must resolve and be reachable from `HEAD`.

    The defect this exists for is invisible at run time: a run records `HEAD`, which
    is reachable by construction, and only a later amend or rebase makes the recorded
    commit an orphan. The first 13/13 recording cites `654d5da2…`, the pre-amend
    version of `7a1c0c16`, which no ref reaches any more — the artifact's content
    claim stayed true, but a third party could not check the revision it compared
    against.
    """
    report = json.loads(report_path.read_text(encoding="utf-8"))
    head = git_optional("rev-parse", "HEAD")
    rows = []
    for field, revision in cited_revisions(report):
        resolved = git_optional("rev-parse", "--verify", f"{revision}^{{commit}}")
        reachable = resolved is not None and subprocess.run(
            ["git", "merge-base", "--is-ancestor", revision, "HEAD"],
            cwd=str(REPO_ROOT), capture_output=True).returncode == 0
        rows.append({"field": field, "revision": revision, "resolves": resolved is not None,
                     "reachable_from_HEAD": reachable})
    dangling = [row for row in rows if not row["reachable_from_HEAD"]]
    print(json.dumps({
        "report": str(report_path), "HEAD": head, "citations_checked": len(rows),
        "dangling": dangling, "citations": rows,
        "verdict": "fail" if dangling else "pass",
        "note": ("a dangling citation is history that cannot be checked out; re-run the "
                 "probe (model-free) rather than editing the revision"),
    }, indent=1, sort_keys=True))
    return 5 if dangling else 0


def extract_pre_fix(out_dir: Path) -> dict:
    """The evaluator at the pinned revision, with the guard the pin needs.

    The lane the verifier measured is the *pre-fix* evaluator invoked the way the
    service used to invoke it: no `--net-isolate`, no namespace around `E*`. The
    bytes come from `PRE_FIX_REVISION` and not from `HEAD`, because `HEAD` has
    since acquired the closure itself: a before side built from the after side's
    bytes would make the positive controls fail and the closure checks pass
    without measuring anything.

    Two refusals, because a pin that has silently stopped meaning "before" is
    worse than no pin: the revision must be an ancestor of `HEAD`, and its
    evaluator must not be byte-identical to the current one.
    """
    resolved = git_bytes("rev-parse", PRE_FIX_REVISION).decode().strip()
    current = git_bytes("rev-parse", "HEAD").decode().strip()
    if subprocess.run(["git", "merge-base", "--is-ancestor", PRE_FIX_REVISION, "HEAD"],
                      cwd=str(REPO_ROOT), capture_output=True).returncode != 0:
        raise SystemExit(f"the pinned revision {PRE_FIX_REVISION} is not an ancestor of HEAD "
                         f"({current[:12]}): the before side would not be before anything")
    target = out_dir / "pre_fix_evaluator"
    target.mkdir(parents=True, exist_ok=True)
    files: Dict[str, dict] = {}
    current_files: Dict[str, dict] = {}
    for name in ("e_star.py", "e_star_child.py"):
        blob = git_bytes("show", f"{PRE_FIX_REVISION}:a0/tasks/maxcut/{name}")
        (target / name).write_bytes(blob)
        files[name] = {"sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob)}
        live = git_bytes("show", f"HEAD:a0/tasks/maxcut/{name}")
        current_files[name] = {"sha256": hashlib.sha256(live).hexdigest(), "bytes": len(live)}
    if all(files[name]["sha256"] == current_files[name]["sha256"] for name in files):
        raise SystemExit(
            "the before side is vacuous: all pinned evaluator files at "
            f"{PRE_FIX_REVISION} are byte-identical to the current ones at HEAD ({current[:12]}). "
            "A comparison whose before-side evaluator *is* the after-side evaluator measures "
            "nothing; the contrast has to be re-established before this probe is run again.")
    return {
        "path": str(target / "e_star.py"),
        "files": files,
        "revision": PRE_FIX_REVISION,
        "revision_full": resolved,
        "differs_from": {
            "revision": "HEAD", "revision_full": current, "files": current_files,
            "per_file": {name: files[name]["sha256"] != current_files[name]["sha256"] for name in files},
        },
    }


def materialise_answer_store(store_dir: Path, revision: str, graph_id: str) -> dict:
    """The pinned revision's witnesses for the graph in hand, byte-verified.

    The before side needs more than the old *evaluator*: the witnesses it used to
    copy are sealed out of the working tree. `git archive` puts them back at
    `store_dir` — a root the lane cannot read, chosen by measurement in `main` —
    and every extracted file is checked against the blob that revision records, so
    "these are the witnesses of `75403e8c`" is a measurement rather than an
    assertion.

    Only the handed graph's witnesses are extracted, not the whole store: the rest
    of it answers other instances, `eval` among them, and `INTERFACE.md` §12 keeps
    the eval set out of every visible path. One graph's witnesses are all the
    candidate could use here anyway — it is handed `G_dev_0001` and nothing else.
    Whatever is extracted is deleted when the run ends.
    """
    recorded: Dict[str, str] = {}
    for line in git_bytes("ls-tree", "-r", revision, "--", ANSWER_STORE).decode().splitlines():
        meta, path = line.split("\t", 1)
        recorded[path] = meta.split()[2]
    selection = sorted(path for path in recorded
                       if path.startswith(f"{ANSWER_STORE}/{graph_id}__")
                       and path.endswith(".partition.json"))
    if not selection:
        raise SystemExit(
            f"the pinned revision {revision} carries no {graph_id} witness under {ANSWER_STORE}/: "
            "the before side cannot be reproduced at all, and the probe does not report a contrast "
            "it cannot show")
    target = store_dir
    target.mkdir(parents=True, exist_ok=True)
    archive = git_bytes("archive", "--format=tar", revision, "--", *selection)
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        try:
            bundle.extractall(target, filter="data")
        except TypeError:  # python < 3.11.4 has no extraction filters
            bundle.extractall(target)
    mismatched = [path for path in selection
                  if not (target / path).is_file() or git_blob_sha1((target / path).read_bytes()) != recorded[path]]
    if mismatched:
        raise SystemExit(f"{len(mismatched)} of {len(selection)} materialised witnesses do not match "
                         f"the git blobs at {revision} (e.g. {mismatched[0]}); refusing to run "
                         "against a store it cannot vouch for")
    digest = hashlib.sha256()
    for path in selection:
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256((target / path).read_bytes()).hexdigest().encode("utf-8"))
    return {
        "revision": revision, "relative": ANSWER_STORE, "selection": f"{graph_id}__*.partition.json",
        "path": str(target), "files": len(selection), "blobs_verified": len(selection) - len(mismatched),
        "store_sha256": digest.hexdigest(), "removed_when_the_run_ends": True,
    }


def run_raw(out_dir: Path, candidate: Path, evaluator: Path) -> dict:
    """The lane as it was: `E*` invoked with no isolation flag and no sandbox."""
    state = out_dir / "estate"
    state.mkdir(parents=True, exist_ok=True)
    outcome = out_dir / "outcome.json"
    command = [sys.executable, str(evaluator), "evaluate", "--candidate", str(candidate),
               "--graph", str(GRAPH), "--seed", "1337", "--timeout", "10",
               "--out", str(outcome), "--state-dir", str(state)]
    proc = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300)
    return {
        "command": command,
        "returncode": proc.returncode,
        "outcome": json.loads(outcome.read_text(encoding="utf-8")) if outcome.is_file() else None,
        "hostile_report": _report_of(state),
        "stderr_tail": proc.stderr[-600:],
    }


def run_service(out_dir: Path, candidate: Path, *, isolation: str, evaluator: Path) -> dict:
    with Service(root=out_dir / "harness", isolation=isolation, evaluator=evaluator) as service:
        response = service.request(f"h-{isolation}", candidate)
        ledger = service.ledger()
    out_state = out_dir / "harness" / "state" / f"h-{isolation}"
    receipt_path = out_state / "sandbox_receipt.json"
    return {
        "candidate_isolation": isolation,
        "evaluator": str(evaluator),
        "response": response,
        "ledger_row": ledger[-1] if ledger else None,
        "hostile_report": _report_of(out_dir / "harness" / "estate"),
        "sandbox_receipt": (json.loads(receipt_path.read_text(encoding="utf-8"))
                            if receipt_path.is_file() else None),
        "identity": json.loads((out_dir / "harness" / "harness_identity.json").read_text(encoding="utf-8")),
    }


def candidate_sandbox_module():
    """`a0/a1/candidate_sandbox.py` by path: the probe measures the real lane."""
    sys.path.insert(0, str(REPO_ROOT / "a0" / "a1"))
    try:
        import candidate_sandbox
        return candidate_sandbox
    finally:
        sys.path.pop(0)


def lane_sees(path: Path) -> bool:
    """Is `path` visible inside the candidate lane? Asked of the lane itself.

    The lane's receipt records which roots it *meant* to hide; this asks the only
    question the probe depends on. It has to be asked, because it is the check
    that caught the lane lying about itself: this host mounts `/tmp` as tmpfs,
    the lane used to read an existing tmpfs mount as "already hidden" and skip
    the mount, so the lane's `/tmp` was the host's `/tmp` and a reproduction of
    the answers placed there was readable by the very lane it was the control
    for — the closure checks would have passed while the contrast was gone.
    `_hide` now replaces every root with a tmpfs of its own and verifies the
    replacement (a new mount id, a changed `st_dev`, an empty root), so `/tmp`
    measures hidden here too; the probe keeps asking rather than reading it off
    the lane's documentation.
    """
    sandbox = candidate_sandbox_module()
    if not sandbox.available():
        raise SystemExit("`unshare` is not on PATH: the candidate lane cannot be measured, and "
                         "the probe will not report a contrast it cannot check")
    script = f"import os; raise SystemExit(0 if os.path.exists({str(path)!r}) else 3)"
    command = sandbox.prefix([sys.executable, "-c", script], allow=[])
    return subprocess.run(command, capture_output=True).returncode == 0


def lane_can_see_into(root: Path) -> Optional[bool]:
    """Can the lane read a fresh directory under `root`? `None` if untestable here."""
    if not root.is_dir() or not os.access(root, os.W_OK):
        return None
    canary = root / f".a0-a1-hostile-canary-{os.getpid()}"
    canary.mkdir()
    try:
        return lane_sees(canary)
    finally:
        canary.rmdir()


#: Where the before side may put its reproduction of the answer store, in order of
#: preference. The first root the lane cannot read is used; `main` refuses to run
#: when none qualifies, because then there is no way to keep the reproduction out
#: of the fixed lane.
STORE_ROOT_CANDIDATES = (Path("/var/tmp"), Path("/tmp"), Path.home())


def run_lanes(out_dir: Path, candidate: Path, evaluator: Path) -> Dict[str, dict]:
    """The four lanes, in one place. `evaluator` is the before side (the pin)."""
    runs: Dict[str, dict] = {}
    runs["raw_pre_fix"] = run_raw(out_dir / "raw_pre_fix", candidate, evaluator)
    runs["service_net_isolate_only"] = run_service(out_dir / "service_net_isolate_only", candidate,
                                                   isolation="none", evaluator=evaluator)
    runs["service_sandbox"] = run_service(out_dir / "service_sandbox", candidate,
                                          isolation="sandbox", evaluator=evaluator)
    # A fourth lane, not part of the mechanism comparison: the evaluator as it
    # stands in the working tree (another workstream is closing the same door from
    # inside `E*`), inside this sandbox. Recorded so the composition is measured
    # rather than assumed.
    runs["current_evaluator_sandboxed"] = run_service(out_dir / "current_evaluator_sandboxed", candidate,
                                                      isolation="sandbox", evaluator=E_STAR)
    return runs


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="hostile_candidate")
    parser.add_argument("--out-dir", default="/tmp/a1/hostile")
    parser.add_argument("--check-citations", metavar="REPORT",
                        help="check that every commit a committed report cites is reachable "
                             "from HEAD, and exit; runs nothing")
    args = parser.parse_args(argv)
    if args.check_citations:
        return check_citations(Path(args.check_citations))
    out_dir = Path(args.out_dir).resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    # The canary is planted in this process's environment as well as the
    # service's: a candidate can read its *ancestors'* environments, and the
    # harness is one of them. Without a PID namespace the candidate finds the
    # variable; with one it finds nothing to read it from.
    os.environ["DEEPSEEK_API_KEY"] = CANARY

    # Where the before side's reproduction of the answers may live, measured from
    # inside the lane rather than taken from its documentation: the fixed lane
    # must not be able to read the control it is being compared against.
    visibility = {str(root): lane_can_see_into(root) for root in STORE_ROOT_CANDIDATES}
    hidden = [root for root in STORE_ROOT_CANDIDATES if visibility[str(root)] is False]
    if not hidden:
        raise SystemExit(
            "not one of " + ", ".join(str(root) for root in STORE_ROOT_CANDIDATES) +
            " is hidden from the candidate lane, so the before side's answer store would be "
            "readable inside the fixed lane and the contrast would be vacuous")
    store_dir = hidden[0] / f"a0-a1-hostile-{os.getpid()}"

    targets = json.loads(TARGETS_JSON.read_text(encoding="utf-8"))
    graph_id = json.loads(GRAPH.read_text(encoding="utf-8"))["graph_id"]
    reference_R = targets["graphs"][graph_id]["R"]

    pre_fix = extract_pre_fix(out_dir)
    store = materialise_answer_store(store_dir, PRE_FIX_REVISION, graph_id)
    candidate = build_candidate(out_dir, store_dir)
    try:
        runs = run_lanes(out_dir, candidate, Path(pre_fix["path"]))
    finally:
        # The before side is a reproduction, not a repository: the witnesses go
        # away with the run that needed them, and the report says whether they did.
        shutil.rmtree(store_dir, ignore_errors=True)
    store["removed_after_the_lanes"] = not store_dir.exists()
    current_store_glob = str(REPO_ROOT / ANSWER_STORE / f"{graph_id}__*.partition.json")

    report: Dict[str, object] = {
        "schema": "a0.a1.hostile_candidate/v1",
        "candidate": {
            "source": "built by a0/a1/probes/hostile_candidate.py",
            "attempts": ["network", "provider key from /proc/*/environ", "~/gptapi.md",
                         "the handed graph's reference witnesses, from the working tree and from "
                         "the pinned pre-fix revision, the best of them used as the answer",
                         "the eval suite / generators / git objects"],
            "canary_variable_in_the_service_environment": "DEEPSEEK_API_KEY",
            "secret_is_never_read": "presence only; the one byte of ~/gptapi.md is not recorded",
        },
        "graph": {"path": str(GRAPH.relative_to(REPO_ROOT)), "graph_id": graph_id,
                  "sha256": sha256_file(GRAPH), "references_R": reference_R},
        "lane_visibility": {
            "question": "can a candidate inside the lane read a fresh directory under the root?",
            "measured": {str(root): ("VISIBLE" if visibility[str(root)] else "hidden"
                                     if visibility[str(root)] is False else "not testable here")
                         for root in STORE_ROOT_CANDIDATES},
            "store_root": str(store_dir.parent),
            "note": "the lane's receipt lists /home /tmp /var/tmp /run/user as hidden, but a list "
                    "is not a measurement, so each root is asked directly: a fresh directory is "
                    "made under it and the lane is asked whether it exists. This is how the lane's "
                    "own defect was found — /tmp is mounted tmpfs by the host here, and the lane "
                    "used to treat an existing tmpfs mount as already hidden and skip the mount, "
                    "so the lane's /tmp was the host's /tmp and this canary read VISIBLE. `_hide` "
                    "now replaces every root with a verified tmpfs of the lane's own, and /tmp "
                    "measures hidden. The before side's reproduction is placed under the first root "
                    "this measurement finds hidden; the probe refuses to run when there is none.",
        },
        "before_side": {
            "claim": "the lane as it was: the pinned revision's evaluator, invoked with no "
                     "isolation, against that revision's witnesses for the handed graph",
            "revision": PRE_FIX_REVISION, "revision_full": pre_fix["revision_full"],
            "evaluator": pre_fix,
            "answer_store": store,
        },
        "after_side": {
            "claim": "the lane as it is: the working tree's evaluator inside the service's "
                     "candidate sandbox, which finds no witness in either store",
            "revision": "HEAD", "revision_full": pre_fix["differs_from"]["revision_full"],
            "evaluator": {"path": str(E_STAR), "sha256": sha256_file(E_STAR),
                          "child_sha256": sha256_file(E_STAR_CHILD)},
            "answer_store": {
                "glob": current_store_glob,
                "files_in_the_working_tree": len(sorted(Path(REPO_ROOT / ANSWER_STORE).glob(f"{graph_id}__*.partition.json"))),
                "note": "sealed out of the tree by baf13884; the sandbox masks the path as well",
            },
        },
        "evaluator_used_for_the_comparison": pre_fix,
        "evaluator_in_the_working_tree": {
            "path": str(E_STAR), "sha256": sha256_file(E_STAR),
            "note": "another workstream's in-flight edit; used only by the fourth lane",
        },
        "runs": runs,
    }

    raw = runs["raw_pre_fix"]["hostile_report"] or {}
    net_only = runs["service_net_isolate_only"]["hostile_report"] or {}
    sandboxed = runs["service_sandbox"]["hostile_report"] or {}
    current = runs["current_evaluator_sandboxed"]["hostile_report"] or {}
    sandbox_response = runs["service_sandbox"]["response"]
    sandbox_receipt = runs["service_sandbox"]["sandbox_receipt"] or {}

    def leaked(run: dict) -> dict:
        return {
            "network": run.get("attempts", {}).get("network", {}),
            "home_secret_readable": (run.get("attempts", {}).get("home_secret", {}) or {}).get("readable"),
            "reference_files_readable": (run.get("attempts", {}).get("references", {}) or {}).get("files_readable"),
            "witness_copied_from": (run.get("attempts", {}).get("references", {}) or {}).get("best_store"),
            "key_variables_found": (run.get("attempts", {}).get("proc_environ", {}) or {}).get("key_variables_found"),
            "used": run.get("used"),
        }

    report["summary"] = {
        "raw_pre_fix": leaked(raw),
        "service_net_isolate_only": leaked(net_only),
        "service_sandbox": leaked(sandboxed),
        "harness_scores": {
            "raw_pre_fix": (runs["raw_pre_fix"]["outcome"] or {}).get("cut_edges"),
            "service_net_isolate_only": runs["service_net_isolate_only"]["response"].get("value"),
            "service_sandbox": sandbox_response.get("value"),
        },
    }

    report["checks"] = {
        # 1. the attack is real, and it is a *score* leak: the copied witness makes
        #    the harness itself report R (the certified optimum on this graph).
        "the_pre_fix_lane_reaches_the_network": (
            (raw.get("attempts", {}).get("network", {}) or {}).get("api.deepseek.com") == "REACHED"
        ),
        "the_pre_fix_lane_reads_the_key_file_and_the_answers": (
            (raw.get("attempts", {}).get("home_secret", {}) or {}).get("readable") is True
            and (raw.get("attempts", {}).get("references", {}) or {}).get("files_readable", 0) > 0
        ),
        "the_copied_witness_scores_exactly_R": (
            raw.get("used") == "copied_reference_partition"
            and (runs["raw_pre_fix"]["outcome"] or {}).get("cut_edges") == reference_R
        ),
        # 2. the existing partial mechanism is partial: the network closes and
        #    nothing else does.
        "net_isolate_alone_closes_the_network": (
            "BLOCKED" in str((net_only.get("attempts", {}).get("network", {}) or {}).get("api.deepseek.com"))
        ),
        "net_isolate_alone_leaves_the_filesystem_open": (
            (net_only.get("attempts", {}).get("home_secret", {}) or {}).get("readable") is True
            and (net_only.get("attempts", {}).get("references", {}) or {}).get("files_readable", 0) > 0
            and runs["service_net_isolate_only"]["response"].get("value") == reference_R
        ),
        # 3. the sandbox closes both, and the key is not in any visible environment.
        "the_sandbox_closes_the_network": (
            "BLOCKED" in str((sandboxed.get("attempts", {}).get("network", {}) or {}).get("api.deepseek.com"))
        ),
        "the_sandbox_closes_the_filesystem": (
            (sandboxed.get("attempts", {}).get("home_secret", {}) or {}).get("readable") is False
            and (sandboxed.get("attempts", {}).get("references", {}) or {}).get("files_visible", None) == 0
            and sandboxed.get("used") == "all_zeros"
        ),
        "the_sandbox_closes_the_process_view": (
            (sandboxed.get("attempts", {}).get("proc_environ", {}) or {}).get("key_variables_found") == []
            and len((sandboxed.get("attempts", {}).get("proc_environ", {}) or {}).get("visible_pids", [])) <= 4
        ),
        # …and the same reading of `/proc` in the *unconfined* lane does find the
        # key variable in an ancestor's environment (that lane has no PID
        # namespace, so the candidate's `/proc` is the host's and the probe's own
        # process is in it, canary and all), so the closure above is measured
        # against a real attack rather than against an absent canary. Two
        # mechanisms close it and the probe measures both: the service no longer
        # hands E* the harness's environment at all, and a user/PID namespace
        # refuses the `/proc` read.
        "the_process_view_leak_is_real_in_the_open_lane_and_closed_in_the_service_lanes": (
            bool((raw.get("attempts", {}).get("proc_environ", {}) or {}).get("key_variables_found"))
            and (net_only.get("attempts", {}).get("proc_environ", {}) or {}).get("key_variables_found") == []
            and (sandboxed.get("attempts", {}).get("proc_environ", {}) or {}).get("key_variables_found") == []
        ),
        # 4. the closure did not break measurement: the lane still produces a
        #    legitimate Outcome (the fallback all-zeros assignment, cut 0).
        "the_lane_still_measures": (
            sandbox_response.get("status") == "ok" and sandbox_response.get("value") == 0
            and (sandbox_response.get("outcome") or {}).get("status") == "ok"
        ),
        "the_sandbox_says_so_itself": (
            sandbox_receipt.get("pass") is True
            and sandbox_receipt.get("self_check", {}).get("hidden_roots_are_tmpfs") is True
            and sandbox_receipt.get("self_check", {}).get("egress_is_blocked") is True
            and sandbox_receipt.get("self_check", {}).get("pid_namespace_is_private") is True
        ),
        "the_identity_records_which_lane_ran": (
            (runs["service_sandbox"]["identity"].get("candidate_isolation") or {}).get("labelled_unsafe") is False
            and (runs["service_net_isolate_only"]["identity"].get("candidate_isolation") or {}).get("labelled_unsafe") is True
        ),
        # 5. the same candidate against the evaluator as it stands in the working
        #    tree (another workstream's in-flight candidate isolation), inside this
        #    sandbox: the two mechanisms compose.
        "the_working_tree_evaluator_inside_the_sandbox_is_closed_too": (
            "BLOCKED" in str((current.get("attempts", {}).get("network", {}) or {}).get("api.deepseek.com"))
            and (current.get("attempts", {}).get("home_secret", {}) or {}).get("readable") is False
            and (current.get("attempts", {}).get("references", {}) or {}).get("files_visible", None) == 0
            and (current.get("attempts", {}).get("proc_environ", {}) or {}).get("key_variables_found") == []
            and runs["current_evaluator_sandboxed"]["response"].get("value") == 0
        ),
    }
    report["verdict"] = "pass" if all(report["checks"].values()) else "fail"  # type: ignore[union-attr]
    (out_dir / "hostile_candidate.json").write_text(
        json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "checks": report["checks"],
                      "summary": report["summary"], "out": str(out_dir / "hostile_candidate.json")},
                     indent=1))
    return 0 if report["verdict"] == "pass" else 5


if __name__ == "__main__":
    sys.exit(main())
