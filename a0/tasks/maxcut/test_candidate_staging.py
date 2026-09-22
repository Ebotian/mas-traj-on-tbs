#!/usr/bin/env python3
"""Regression test for the candidate-staging defect (DEVIATIONS.md D-T1-10).

The defect: `resolve_candidate` decided *how* to launch a candidate from the
entry's mode bit and `#!` line, but `stage_candidate` runs a content-only copy of
the candidate that never carried the mode.  So a byte-identical candidate was
evaluable or not depending on a bit that (`INTERFACE.md` §2) is not part of its
identity: `positive_control/{baseline,pc}/solution.py` were `chmod +x`ed after
the gate ran and E* stopped being able to measure them.

The invariant this test pins down: **the launch is a function of the candidate's
bytes alone.**  Both mode variants of the same bytes must launch identically and
score identically, and the interpreter must be prefixed exactly once.  A
candidate that genuinely wants to be execve'd must say so with `exec: []` in its
`candidate.json`, and then the mode must survive staging.

    python3 test_candidate_staging.py                     # tests the working tree
    python3 test_candidate_staging.py --e-star <path>      # tests another E*
    python3 test_candidate_staging.py --json               # machine-readable

To see the test fail on the unfixed evaluator, run it against the frozen bytes:

    mkdir -p /tmp/pre-fix && git -C <repo> show <parent-rev>:a0/tasks/maxcut/e_star.py \\
        > /tmp/pre-fix/e_star.py && git -C <repo> show <parent-rev>:a0/tasks/maxcut/e_star_child.py \\
        > /tmp/pre-fix/e_star_child.py
    python3 test_candidate_staging.py --e-star /tmp/pre-fix/e_star.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_E_STAR = HERE / "e_star.py"
SEED = 1337
TAU_S = 30.0

#: A minimal, deterministic, always-valid candidate: side = index % 2.
CANDIDATE_SOURCE = '''#!/usr/bin/env python3
"""Staging-regression candidate: a valid, deterministic alternating partition."""

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    with open(args.graph, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    assignment = [index % 2 for index in range(int(document["n"]))]
    payload = {"schema": "a0.maxcut.partition/v1", "graph_id": document["graph_id"],
               "assignment": assignment}
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\\n")
    if "--probe-argv" in sys.argv:
        with open(args.out + ".argv", "w", encoding="utf-8") as handle:
            handle.write(json.dumps(sys.argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def build_candidate(
    root: Path, name: str, mode: int, *, declared_exec: list[str] | None, candidate_id: str | None = None,
) -> Path:
    """Write one candidate directory.

    `candidate_id` defaults to `name`, but the mode-pair fixtures pass a shared id
    so that the two directories are **byte-identical** apart from the mode bit --
    which is the whole point of the pair.
    """
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    entry = directory / "solution.py"
    entry.write_bytes(CANDIDATE_SOURCE.encode("utf-8"))
    metadata = {
        "schema": "a0.maxcut.candidate/v1",
        "candidate_id": candidate_id or name,
        "kind": "ok",
        "role": "staging-regression",
        "purpose": "regression fixture for D-T1-10",
        "version": "1.0.0",
    }
    if declared_exec is not None:
        metadata["exec"] = declared_exec
    (directory / "candidate.json").write_bytes(
        (json.dumps(metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")
    )
    os.chmod(entry, mode)
    return directory


def evaluate(e_star: Path, candidate: Path, graph: Path, work: Path, tag: str) -> dict:
    out_path = work / f"{tag}.outcome.json"
    resources_path = work / f"{tag}.resources.json"
    completed = subprocess.run(
        [sys.executable, str(e_star), "evaluate", "--candidate", str(candidate),
         "--graph", str(graph), "--seed", str(SEED), "--timeout", str(TAU_S),
         "--out", str(out_path), "--emit-resources", str(resources_path),
         "--state-dir", str(work / "state" / tag)],
        capture_output=True, text=True, check=False,
    )
    if not out_path.is_file():
        return {"status": "<no outcome>", "stderr": completed.stderr[-600:], "evaluator_exit": completed.returncode}
    outcome = json.loads(out_path.read_text(encoding="utf-8"))
    resources = json.loads(resources_path.read_text(encoding="utf-8")) if resources_path.is_file() else {}
    return {
        "status": outcome["status"],
        "cut_edges": outcome["cut_edges"],
        "candidate_source_sha256": outcome["candidate_source_sha256"],
        "failure_kind": (outcome["failure"] or {}).get("kind"),
        "failure_detail": (outcome["failure"] or {}).get("detail"),
        "evaluator_exit": completed.returncode,
        "argv": (resources.get("runs") or [{}])[0].get("argv"),
    }


def launch_shape(arguments: list[str] | None, graph: Path, tag: str) -> tuple[dict, list[str]]:
    """Reduce an argv to the part that is the *launch decision*.

    The staged path and the `--out` path necessarily differ between two runs (they
    live under different state roots), so comparing raw argv would fail for
    reasons that have nothing to do with the mode bit.  What must be identical is
    the launcher, the entry's name and §4's argument list.
    """
    if not arguments or len(arguments) < 8:
        return {}, [f"{tag}: no usable launched argv was recorded: {arguments!r}"]
    problems: list[str] = []
    launcher, entry = arguments[0], arguments[1]
    if launcher.endswith("/solution.py"):
        problems.append(f"{tag}: expected an interpreter launcher, got the entry itself: {launcher}")
    if not entry.endswith("/solution.py"):
        problems.append(f"{tag}: argv[1] is not the candidate entry: {entry}")
    if arguments.count(launcher) != 1:
        problems.append(f"{tag}: the launcher appears {arguments.count(launcher)} times in argv: {arguments}")
    if sum(1 for part in arguments if part.endswith("/solution.py")) != 1:
        problems.append(f"{tag}: the entry appears more than once in argv: {arguments}")
    if arguments[2::2] != ["--graph", "--out", "--seed"] or len(arguments) != 8:
        problems.append(f"{tag}: argv is not §4's list after the launcher: {arguments}")
    if arguments[3] != str(graph.resolve()):
        problems.append(f"{tag}: --graph is not the absolute graph path: {arguments[3]}")
    shape = {
        "launcher": launcher,
        "entry_basename": os.path.basename(entry),
        "argument_count": len(arguments),
        "flags": arguments[2::2],
        "graph": arguments[3],
        "seed": arguments[7],
    }
    return shape, problems


def run_checks(e_star: Path, graph: Path, work: Path) -> dict:
    """The regression.  `work` must be a writable scratch directory."""
    e_star = Path(e_star).resolve()
    graph = Path(graph).resolve()
    work = Path(work)
    (work / "state").mkdir(parents=True, exist_ok=True)
    fixtures = work / "fixtures"

    # The two byte-identical candidates that differ only in the mode bit.
    plain = build_candidate(
        fixtures, "same_bytes_mode_0644", 0o644, declared_exec=None, candidate_id="staging_mode_fixture")
    exec_bit = build_candidate(
        fixtures, "same_bytes_mode_0755", 0o755, declared_exec=None, candidate_id="staging_mode_fixture")
    declared = build_candidate(
        fixtures, "declared_direct_exec", 0o755, declared_exec=[sys.executable],
    )
    self_exec = build_candidate(fixtures, "declared_self_exec", 0o755, declared_exec=[])

    plain_result = evaluate(e_star, plain, graph, work, "mode_0644")
    exec_result = evaluate(e_star, exec_bit, graph, work, "mode_0755")
    declared_result = evaluate(e_star, declared, graph, work, "declared_interpreter")
    self_exec_result = evaluate(e_star, self_exec, graph, work, "declared_self_exec")

    cases: list[dict] = []

    def case(name: str, ok: bool, claim: str, **evidence) -> None:
        cases.append({"name": name, "ok": bool(ok), "claim": claim, **evidence})

    # (1) Required: a candidate with no executable bit must evaluate normally.
    case(
        "no_executable_bit_evaluates",
        plain_result["status"] == "ok" and isinstance(plain_result["cut_edges"], int),
        "a mode-0644 Python candidate with a #! line is evaluated normally (this raised "
        "PermissionError before the fix)",
        result=plain_result,
    )

    # (2) Required: the executable bit must not change the launch, and must not
    #     stack a second interpreter in front of the first.
    shape_plain, problems_plain = launch_shape(plain_result.get("argv"), graph, "mode_0644")
    shape_exec, problems_exec = launch_shape(exec_result.get("argv"), graph, "mode_0755")
    argv_problems = problems_plain + problems_exec
    same_shape = shape_plain == shape_exec and bool(shape_plain)
    case(
        "executable_bit_does_not_change_launch",
        exec_result["status"] == "ok" and plain_result["status"] == "ok" and not argv_problems and same_shape,
        "mode 0644 and mode 0755 of identical bytes launch with the same argv shape, with the "
        "interpreter prefixed exactly once",
        shape_0644=shape_plain,
        shape_0755=shape_exec,
        identical_shape=same_shape,
        problems=argv_problems,
    )

    # Identity is content-only, so both must stamp the same digest.
    same_identity = (
        plain_result["candidate_source_sha256"] == exec_result["candidate_source_sha256"]
    )
    same_score = plain_result["cut_edges"] == exec_result["cut_edges"]
    case(
        "mode_bit_is_not_identity",
        same_identity and same_score,
        "both mode variants carry the same candidate_source_sha256 and the same cut_edges",
        sha256_0644=plain_result["candidate_source_sha256"],
        sha256_0755=exec_result["candidate_source_sha256"],
        cut_0644=plain_result["cut_edges"],
        cut_0755=exec_result["cut_edges"],
    )

    # A declared interpreter prefix is used verbatim, not doubled.
    declared_argv = declared_result.get("argv") or []
    case(
        "declared_exec_prefix_used_once",
        declared_result["status"] == "ok"
        and bool(declared_argv)
        and declared_argv[0] == sys.executable
        and declared_argv.count(sys.executable) == 1,
        "a declared `exec: [<interpreter>]` is used verbatim and never doubled",
        result=declared_result,
    )

    # (3) The declared direct-execution escape hatch: mode must survive staging.
    self_argv = self_exec_result.get("argv") or []
    case(
        "declared_self_exec_preserves_mode",
        self_exec_result["status"] == "ok"
        and bool(self_argv)
        and self_argv[0].endswith("/solution.py")
        and str(fixtures) not in self_argv[0],
        "a candidate declaring `exec: []` is execve'd directly from the STAGED copy (not the "
        "fixture path), so the executable bit survived staging",
        result=self_exec_result,
    )

    return {
        "ok": all(item["ok"] for item in cases),
        "claim": "the candidate launch is a function of the candidate's bytes alone",
        "e_star": str(e_star),
        "graph": str(graph),
        "cases": cases,
    }


def default_graph() -> Path:
    for candidate in (
        HERE / "suite" / "dev" / "G_dev_0001.json",
        HERE / "graphs_tmp" / "tmp_suite" / "dev" / "G_tmp_0001.json",
    ):
        if candidate.is_file():
            return candidate
    raise SystemExit("test_candidate_staging: no dev graph found to evaluate against")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="candidate-staging regression test (D-T1-10)")
    parser.add_argument("--e-star", default=str(DEFAULT_E_STAR))
    parser.add_argument("--graph", default=None)
    parser.add_argument("--work", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    work = Path(args.work) if args.work else Path(tempfile.mkdtemp(prefix="staging-regression-"))
    result = run_checks(Path(args.e_star), Path(args.graph) if args.graph else default_graph(), work)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(f"e_star: {result['e_star']}")
        print(f"graph : {result['graph']}")
        for item in result["cases"]:
            print(f"  {'PASS' if item['ok'] else 'FAIL'}  {item['name']}")
            if not item["ok"]:
                print(f"        {item['claim']}")
                print(f"        evidence: {json.dumps({k: v for k, v in item.items() if k not in ('name','ok','claim')})[:600]}")
        print(f"VERDICT: {'PASS' if result['ok'] else 'FAIL'}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
