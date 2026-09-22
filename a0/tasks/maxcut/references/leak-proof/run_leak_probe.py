#!/usr/bin/env python3
"""The leak probe: run the hostile candidate in three environments and compare.

    python3 references/leak-proof/run_leak_probe.py [--modes prefix,open,fixed]

Modes
-----
* ``prefix`` -- the *pre-fix* evaluator: `git show <PRE_FIX_REV>:a0/tasks/maxcut/{e_star.py,e_star_child.py}`
  materialised into the work directory.  Nothing is masked and the candidate is
  handed the suite file's own path.  This reproduces the verifier's finding
  (`a0/verify/a1-testbed/REPORT.md` §2c): a candidate that copies the stored
  witness scores exactly `R` on the hold-out.
* ``open``   -- the fixed evaluator with ``--no-fs-isolate``: the candidate now
  gets the reduced view, but the answer stores are still readable.
* ``fixed``  -- the fixed evaluator with its default filesystem isolation.

What is compared is not what the candidate *claims*: it is the `cut_edges` the
harness books from the candidate's artifact (`INTERFACE.md` §4/§5).  `217` on
`G_eval_0001` is the certified optimum, so a booked 217 is a copied answer.

The probe also audits the surrounding filesystem for witness copies that live
outside the repository, since those must be masked or deleted too.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parent.parent
REPO = TASK.parent.parent.parent
E_STAR = TASK / "e_star.py"
CANDIDATE = HERE / "hostile_candidate.py"
GRAPH = TASK / "suite" / "eval" / "G_eval_0001.json"
TARGETS = TASK / "references" / "targets.json"
#: The revision the `prefix` mode reproduces.  Pinned to the commit the leak was
#: found on, not to `HEAD`, so the probe stays reproducible after this work is
#: committed (`a0/verify/a1-testbed` is the verification commit).
PRE_FIX_REV = "4b94503e"

MODES = ("prefix", "open", "fixed")


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, **kwargs)


def prefix_evaluator(work: Path) -> Path:
    """Materialise the pre-fix evaluator (both files) out of git."""
    target = work / "pre-fix"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("e_star.py", "e_star_child.py"):
        blob = run(["git", "-C", str(REPO), "show", f"{PRE_FIX_REV}:a0/tasks/maxcut/{name}"])
        if blob.returncode != 0:
            raise SystemExit(f"cannot read {name} at {PRE_FIX_REV}: {blob.stderr.strip()}")
        (target / name).write_text(blob.stdout)
    return target / "e_star.py"


def plant_decoy() -> dict:
    """Put another candidate's answer where the default state root would hold it.

    The cross-candidate hazard is not hypothetical: `--state-dir` defaults to
    `/tmp/maxcut-e-star-state`, which is shared by every E* invocation on this
    machine, so a candidate that reads it can pick up a better partition than its
    own for the very graph it is being scored on.  The decoy is a *real* stored
    witness, planted at the path a previous run of another candidate would have
    used.
    """
    witness = None
    candidates = sorted((TASK / "references" / "logs" / "partitions").glob(
        f"{GRAPH.stem}__*.partition.json"))
    if candidates:
        witness = candidates[0]
    if witness is None:
        return {"planted": False, "reason": "no stored witness is readable (already sealed?)"}
    target = Path("/tmp/maxcut-e-star-state") / "invocations" / "decoy-candidate" / GRAPH.stem / "run1"
    target.mkdir(parents=True, exist_ok=True)
    destination = target / "partition.json"
    shutil.copyfile(witness, destination)
    return {"planted": True, "witness": witness.name, "path": str(destination)}


def evaluate(mode: str, e_star: Path, work: Path) -> dict:
    """One E* run over the hostile candidate, and the booked verdict."""
    state = work / f"state-{mode}"
    out = work / f"outcome-{mode}.json"
    resources = work / f"resources-{mode}.json"
    command = [
        sys.executable, str(e_star), "evaluate",
        "--candidate", str(CANDIDATE),
        "--graph", str(GRAPH),
        "--seed", "1337", "--timeout", "60",
        "--out", str(out), "--emit-resources", str(resources),
        "--state-dir", str(state),
    ]
    if mode == "open":
        command.append("--no-fs-isolate")
    completed = run(command)
    outcome = json.loads(out.read_text()) if out.is_file() else {}
    dumps = sorted(state.glob("invocations/*/G_eval_0001/run1/partition.json.probe.json"))
    dump = json.loads(dumps[0].read_text()) if dumps else {}
    return {
        "mode": mode,
        "e_star": str(e_star),
        "evaluator_exit": completed.returncode,
        "stderr_tail": completed.stderr[-400:],
        "status": outcome.get("status"),
        "cut_edges": outcome.get("cut_edges"),
        "edges_total": outcome.get("edges_total"),
        "failure_kind": (outcome.get("failure") or {}).get("kind"),
        "candidate_graph_sha256": outcome.get("candidate_graph_sha256"),
        "graph_sha256": outcome.get("graph_sha256"),
        "probe": dump,
    }


PRUNE = {".git", "site-packages", "node_modules", "__pycache__", ".venv", ".venv-pin",
         ".venv-tools", ".cache", ".npm", ".cargo", ".rustup", ".nvm", "pgdata",
         "redis-data", ".uvcache"}


def witness_audit() -> dict:
    """Every copy of an eval witness on this machine, outside the repository.

    The needles are the stored witnesses' own values: the assignment vector
    serialised compactly, and the `+/-1` spelling MQLib prints.  Both are
    whitespace-free, so an indented, re-spaced or line-wrapped copy still hits
    after the file is normalised.  `ripgrep` does the text pass when it is
    installed (one pass over the whole tree per needle file); the fallback is a
    Python walk of the same roots, with dependency trees pruned and a size cap.
    A *compressed* copy is not detected by either, and is reported as residual
    risk rather than as a hit.
    """
    needles = []
    for path in sorted((TASK / "references" / "logs" / "partitions").glob("G_eval_*.partition.json")):
        document = json.loads(path.read_text())
        assignment = document["assignment"]
        for spelling in (
            json.dumps(assignment, separators=(",", ":")),
            " ".join("1" if value else "-1" for value in assignment),
        ):
            needles.append(("".join(spelling.split()), path.name, document["graph_id"]))
    if not needles:
        return {"skipped": "the witness store is empty (already sealed?)", "hits": []}

    roots = ["/home/ebt", "/tmp", "/var/tmp", "/opt", "/srv", "/root"]
    engine = "python-walk"
    hits: list[dict] = []
    files_scanned = 0
    skipped_inside_repo = 0
    if shutil.which("rg"):
        engine = "ripgrep"
        pattern_file = Path(tempfile.mkdtemp(prefix="leak-needles-")) / "needles.txt"
        pattern_file.write_text("\n".join(needle for needle, _name, _gid in needles) + "\n")
        prunes = []
        for name in sorted(PRUNE):
            prunes += ["--glob", f"!**/{name}/**"]
        result = run(["rg", "-F", "-f", str(pattern_file), "-l", "--no-messages", "--hidden",
                      "--no-ignore", "--max-filesize", "2M", *prunes, *roots])
        by_needle = {needle: (name, gid) for needle, name, gid in needles}
        candidates = [Path(line) for line in result.stdout.splitlines()]
        outside = [path for path in candidates if not str(path).startswith(str(REPO))]
        for path in outside:
            try:
                flat = "".join(path.read_text(encoding="utf-8", errors="ignore").split())
            except OSError:
                continue
            files_scanned += 1
            for needle, (name, gid) in by_needle.items():
                if needle in flat:
                    hits.append({"path": str(path), "witness": name, "graph_id": gid})
                    break
        skipped_inside_repo = len(candidates) - len(outside)
    else:
        for root in roots:
            base = Path(root)
            if not base.is_dir():
                continue
            for directory, subdirs, files in os.walk(base, followlinks=False):
                subdirs[:] = [name for name in subdirs if name not in PRUNE]
                for name in files:
                    path = Path(directory) / name
                    if str(path).startswith(str(REPO)):
                        continue
                    try:
                        if not path.is_file() or path.stat().st_size > 2_000_000:
                            continue
                        text = path.read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        continue
                    files_scanned += 1
                    flat = "".join(text.split())
                    for needle, witness_name, graph_id in needles:
                        if needle in flat:
                            hits.append({"path": str(path), "witness": witness_name,
                                         "graph_id": graph_id})
                            break
    summary = {"needles": len(needles), "engine": engine, "roots": roots,
               "files_scanned": files_scanned, "hits": hits}
    if engine == "ripgrep":
        summary["hits_inside_repository"] = skipped_inside_repo
    return summary




def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--modes", default=",".join(MODES))
    parser.add_argument("--work", default=None)
    parser.add_argument("--out", default=str(HERE / "out_leak_probe.json"))
    parser.add_argument("--skip-audit", action="store_true")
    args = parser.parse_args(argv)

    work = Path(args.work) if args.work else Path(tempfile.mkdtemp(prefix="leak-probe-"))
    work.mkdir(parents=True, exist_ok=True)
    targets = json.loads(TARGETS.read_text())
    reference = targets["graphs"]["G_eval_0001"]

    result = {
        "graph": str(GRAPH),
        "reference": {"R": reference["R"], "OPT": reference["OPT"],
                      "opt_certified": reference["opt_certified"]},
        "runs": [],
    }
    if not args.skip_audit:
        result["witness_audit"] = witness_audit()

    result["state_root_decoy"] = plant_decoy()
    pre_fix = None
    for mode in [item for item in args.modes.split(",") if item]:
        if mode == "prefix":
            if pre_fix is None:
                pre_fix = prefix_evaluator(work)
            evaluator = pre_fix
        elif mode == "fixed":
            evaluator = E_STAR
        elif mode == "open":
            evaluator = E_STAR
        else:
            raise SystemExit(f"unknown mode {mode!r}")
        result["runs"].append(evaluate(mode, evaluator, work))

    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")

    reference_opt = reference["OPT"] if reference["opt_certified"] else reference["R"]
    print(f"graph {GRAPH.name}: R={reference['R']} OPT={reference['OPT']} |E|="
          f"{json.loads(GRAPH.read_text())['edges'].__len__()}")
    for run in result["runs"]:
        booked = run["cut_edges"]
        verdict = "COPIED THE ANSWER" if booked == reference_opt else (
            "no answer recovered" if booked is not None else f"no score ({run['status']})")
        print(f"  {run['mode']:7s} status={run['status']!s:8s} cut_edges={booked} "
              f"recovered_from={run['probe'].get('recovered_from')} -> {verdict}")
        for name, value in sorted((run["probe"].get("attempts") or {}).items()):
            print(f"      {name:32s} {value}")
    if "witness_audit" in result:
        audit = result["witness_audit"]
        if audit.get("skipped"):
            print(f"  witness audit: skipped -- {audit['skipped']}")
        else:
            print(f"  witness audit ({audit['engine']}): {audit['needles']} needles, "
                  f"{len(audit['hits'])} copies outside {REPO}")
            for hit in audit["hits"]:
                print(f"      {hit['path']}  ({hit['witness']})")
    print(f"raw output: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
