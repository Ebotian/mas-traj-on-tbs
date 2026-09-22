#!/usr/bin/env python3
"""A *hostile* candidate, run three ways, so every closure claim has an attempt.

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

Then it runs that same candidate three ways:

| run | lane | what it establishes |
|---|---|---|
| `raw_pre_fix` | `e_star.py evaluate`, no flags, as the service used to run it | the leak is real: network reached, key file readable, witness copied |
| `service_net_isolate_only` | `eval_service.py --candidate-isolation none` | `--net-isolate` alone closes the network and nothing else |
| `service_sandbox` | `eval_service.py` (the default) | all of it closed, and the lane still measures |

    python3 a0/a1/probes/hostile_candidate.py --out-dir /tmp/a1/hostile

The provider key is never read: the probe plants a **canary** variable in the
service's environment (`DEEPSEEK_API_KEY=<canary>`) and asks the candidate to
report only *whether* that variable name is present in a readable environment —
presence and pid, never a value. `~/gptapi.md` is opened for one byte, and the
probe records only that the open succeeded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
E_SERVICE = REPO_ROOT / "a0" / "a1" / "eval_service.py"
E_STAR = REPO_ROOT / "a0" / "tasks" / "maxcut" / "e_star.py"
GRAPH = REPO_ROOT / "a0" / "tasks" / "maxcut" / "suite" / "dev" / "G_dev_0001.json"
TARGETS_JSON = REPO_ROOT / "a0" / "tasks" / "maxcut" / "references" / "targets.json"

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

# 4. the stored reference partitions for the graph in hand, used as an answer
readable = []
best = None
visible = sorted(glob.glob(TARGETS["references_glob"].format(graph_id=graph_id)))
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
    if best is None or cut > best[1]:
        best = (path, cut, assignment)
report["attempts"]["references"] = {
    "glob": TARGETS["references_glob"].format(graph_id=graph_id),
    "files_visible": len(visible),
    "files_readable": len(readable),
    "best_cut": None if best is None else best[1],
    "best_path": None if best is None else best[0],
    "examples": readable[:5],
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


def reference_targets() -> dict:
    """Where the answers are, as the candidate would find them (baked in).

    The paths are literal, which is the point: a hostile candidate does not need
    to *discover* the repository layout, it only needs one absolute path and the
    uid it runs under.
    """
    return {
        "home_secret": str(Path.home() / "gptapi.md"),
        "references_glob": str(REPO_ROOT / "a0/tasks/maxcut/references/logs/partitions/{graph_id}__*.partition.json"),
        "other": {
            "eval_suite": str(REPO_ROOT / "a0/tasks/maxcut/suite/eval/*.json"),
            "generators": str(REPO_ROOT / "a0/tasks/maxcut/generators/**/*"),
            "git_objects": str(REPO_ROOT / ".git/objects/*/*"),
            "reference_targets": str(REPO_ROOT / "a0/tasks/maxcut/references/targets.json"),
        },
    }


def build_candidate(root: Path) -> Path:
    directory = root / "candidate"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "candidate.json").write_text(
        json.dumps({"candidate_id": "hostile_probe", "version": "1.0.0"}, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    source = CANDIDATE_TEMPLATE.replace("__TARGETS__", json.dumps(reference_targets(), indent=1, sort_keys=True))
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


def extract_pre_fix(out_dir: Path) -> dict:
    """The evaluator *as committed*, for the before-side of the comparison.

    The lane that the verifier measured is the committed evaluator invoked the way
    the service used to invoke it: no `--net-isolate`, no namespace around `E*`.
    Using the bytes at `HEAD` (rather than the working tree, which another
    workstream may be editing) makes the before-side a fixed, named revision.
    """
    target = out_dir / "pre_fix_evaluator"
    target.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in ("e_star.py", "e_star_child.py"):
        blob = subprocess.run(["git", "show", f"HEAD:a0/tasks/maxcut/{name}"],
                              cwd=str(REPO_ROOT), capture_output=True, check=True)
        (target / name).write_bytes(blob.stdout)
        files[name] = {"sha256": hashlib.sha256(blob.stdout).hexdigest(), "bytes": len(blob.stdout)}
    return {"path": str(target / "e_star.py"), "files": files, "revision": "HEAD"}


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


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="hostile_candidate")
    parser.add_argument("--out-dir", default="/tmp/a1/hostile")
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir).resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    candidate = build_candidate(out_dir)
    # The canary is planted in this process's environment as well as the
    # service's: a candidate can read its *ancestors'* environments, and the
    # harness is one of them. Without a PID namespace the candidate finds the
    # variable; with one it finds nothing to read it from.
    os.environ["DEEPSEEK_API_KEY"] = CANARY

    targets = json.loads(TARGETS_JSON.read_text(encoding="utf-8"))
    graph_id = json.loads(GRAPH.read_text(encoding="utf-8"))["graph_id"]
    reference_R = targets["graphs"][graph_id]["R"]

    runs: Dict[str, dict] = {}
    pre_fix = extract_pre_fix(out_dir)
    runs["raw_pre_fix"] = run_raw(out_dir / "raw_pre_fix", candidate, Path(pre_fix["path"]))
    runs["service_net_isolate_only"] = run_service(out_dir / "service_net_isolate_only", candidate,
                                                   isolation="none", evaluator=Path(pre_fix["path"]))
    runs["service_sandbox"] = run_service(out_dir / "service_sandbox", candidate,
                                          isolation="sandbox", evaluator=Path(pre_fix["path"]))
    # A fourth lane, not part of the mechanism comparison: the evaluator as it
    # stands in the working tree (another workstream is closing the same door from
    # inside `E*`), inside this sandbox. Recorded so the composition is measured
    # rather than assumed.
    runs["current_evaluator_sandboxed"] = run_service(out_dir / "current_evaluator_sandboxed", candidate,
                                                      isolation="sandbox", evaluator=E_STAR)

    report: Dict[str, object] = {
        "schema": "a0.a1.hostile_candidate/v1",
        "candidate": {
            "source": "built by a0/a1/probes/hostile_candidate.py",
            "attempts": ["network", "provider key from /proc/*/environ", "~/gptapi.md",
                         "the stored reference partitions, used as the answer",
                         "the eval suite / generators / git objects"],
            "canary_variable_in_the_service_environment": "DEEPSEEK_API_KEY",
            "secret_is_never_read": "presence only; the one byte of ~/gptapi.md is not recorded",
        },
        "graph": {"path": str(GRAPH.relative_to(REPO_ROOT)), "graph_id": graph_id,
                  "sha256": sha256_file(GRAPH), "references_R": reference_R},
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
        # key variable in an ancestor's environment (E* inherits the harness's
        # environment there), so the closure above is measured against a real
        # attack rather than against an absent canary. Two mechanisms close it and
        # the probe measures both: the service no longer hands E* the harness's
        # environment at all, and a user/PID namespace refuses the `/proc` read.
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
