"""Adversarial checks for the properties E* must have (study §4.2.2).

Every check here is an experiment, not an assertion about the code: each one runs
the real CLI and compares real bytes.

    .venv/bin/python tools/check_invariance.py            # run everything
    .venv/bin/python tools/check_invariance.py --only cwd

Checks:
  cwd        same candidate from three working directories -> identical bytes
  path       poisoned PATH (fake python3/git/gcc) -> identical bytes
  env        hostile caller environment -> identical bytes
  relocate   same content under a different path/name -> identical bytes
  tree       the candidate tree is byte-identical after evaluation
  revert     E*'s state survives `git checkout . && git clean -xfd`
  seedful    at fidelity=full the seed is inert; at fidelity=fast it bites
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PYTHON = ROOT / ".venv" / "bin" / "python"
E_STAR = ROOT / "e_star.py"
WORK = Path(tempfile.gettempdir()) / "e-star-invariance"

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str) -> None:
    RESULTS.append((name, passed, detail))
    print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}", flush=True)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_path(path: Path) -> str:
    return digest(path.read_bytes())


def tree_digest(root: Path) -> str:
    entries = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file():
            entries.append({"path": rel, "sha256": digest_path(path)})
        else:
            entries.append({"path": rel + "/", "sha256": None})
    return digest(json.dumps(entries, sort_keys=True).encode("utf-8"))


def evaluate(
    candidate: Path,
    *,
    out: Path,
    state: Path,
    cwd: Path,
    seed: int = 1337,
    fidelity: str = "full",
    fraction: float | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, bytes, bytes, bytes]:
    command = [
        str(PYTHON),
        str(E_STAR),
        "evaluate",
        "--candidate",
        str(candidate),
        "--seed",
        str(seed),
        "--fidelity",
        fidelity,
        "--out",
        str(out),
        "--state-dir",
        str(state),
    ]
    if fraction is not None:
        command += ["--fraction", str(fraction)]
    completed = subprocess.run(
        command, cwd=str(cwd), env=env, capture_output=True, check=False
    )
    return completed.returncode, completed.stdout, completed.stderr, out.read_bytes()


def fresh(name: str) -> Path:
    path = WORK / name
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def check_cwd() -> None:
    base = fresh("cwd")
    candidate = ROOT / "C_STAR" / "c01_good_hex"
    runs = []
    for label, cwd in (("repo-root", ROOT), ("slash", Path("/")), ("tmp", WORK)):
        out = base / f"{label}.json"
        state = base / f"state-{label}"
        code, stdout, stderr, payload = evaluate(candidate, out=out, state=state, cwd=cwd)
        runs.append((label, code, stdout, payload))
    first = runs[0]
    same = all(item[3] == first[3] for item in runs) and all(item[2] == first[2] for item in runs)
    record(
        "cwd",
        same,
        "identical --out bytes and stdout from " + ", ".join(item[0] for item in runs) +
        f" (sha256 {digest(first[3])[:16]}, exit {first[1]})",
    )


def check_path() -> None:
    base = fresh("path")
    poisoned = base / "poison-bin"
    poisoned.mkdir(parents=True, exist_ok=True)
    for name in ("python", "python3", "git", "gcc", "cc", "sh"):
        script = poisoned / name
        script.write_text("#!/bin/sh\necho 'poisoned tool called' >&2\nexit 111\n", encoding="utf-8")
        script.chmod(0o755)
    candidate = ROOT / "C_STAR" / "c01_good_hex"

    baseline_env = dict(os.environ)
    poisoned_env = dict(os.environ)
    poisoned_env["PATH"] = f"{poisoned}:/nonexistent"

    _, _, _, baseline = evaluate(
        candidate,
        out=base / "baseline.json",
        state=base / "state-baseline",
        cwd=base,
        env=baseline_env,
    )
    _, _, _, poisoned_out = evaluate(
        candidate,
        out=base / "poisoned.json",
        state=base / "state-poisoned",
        cwd=base,
        env=poisoned_env,
    )
    record(
        "path",
        baseline == poisoned_out,
        f"PATH={base}/poison-bin:/nonexistent gave identical --out bytes (sha256 {digest(poisoned_out)[:16]})",
    )


def check_env() -> None:
    base = fresh("env")
    candidate = ROOT / "C_STAR" / "c01_good_hex"
    hostile = dict(os.environ)
    hostile.update(
        {
            "EVE_WORKSPACE_ROOT": "/evil/workspace",
            "EVE_SOLVER_ROOT": "/evil/solver",
            "EVE_EVAL_LOG_ROOT": "/evil/logs",
            "PYTHONPATH": "/evil/site",
            "PYTHONHASHSEED": "12345",
            "CIRCLE_PACKING_RUNTIME_BUDGET_MS": "1",
            "CIRCLE_PACKING_RUNTIME_RUNS": "3",
            "HOME": "/evil/home",
            "TMPDIR": "/evil/tmp",
        }
    )
    _, _, _, baseline = evaluate(
        candidate, out=base / "baseline.json", state=base / "state-a", cwd=base, env=dict(os.environ)
    )
    _, _, _, hostile_out = evaluate(
        candidate, out=base / "hostile.json", state=base / "state-b", cwd=base, env=hostile
    )
    record(
        "env",
        baseline == hostile_out,
        "hostile EVE_*/PYTHONPATH/CIRCLE_PACKING_* environment gave identical --out bytes",
    )


def check_relocate() -> None:
    base = fresh("relocate")
    candidate = ROOT / "C_STAR" / "c01_good_hex"
    copies = []
    for index, name in enumerate(("elsewhere/solution.py", "a-completely-different-name/deep/solution.py")):
        target = base / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(candidate / "solution.py", target)
        copies.append(target)
    _, _, _, baseline = evaluate(
        candidate, out=base / "baseline.json", state=base / "state-0", cwd=base
    )
    digests = [digest(baseline)]
    for index, target in enumerate(copies):
        _, _, _, payload = evaluate(
            target, out=base / f"copy{index}.json", state=base / f"state-c{index}", cwd=base
        )
        digests.append(digest(payload))
    record(
        "relocate",
        len(set(digests)) == 1,
        "the same bytes under three different paths/names gave identical outcomes "
        f"(sha256 {digests[0][:16]})",
    )


def check_tree() -> None:
    base = fresh("tree")
    candidate = base / "candidate"
    shutil.copytree(ROOT / "C_STAR" / "c01_good_hex", candidate)
    before = tree_digest(candidate)
    evaluate(candidate, out=base / "out.json", state=base / "state", cwd=base)
    after = tree_digest(candidate)
    leftovers = [str(p.relative_to(candidate)) for p in candidate.rglob("*") if p.is_file()]
    record(
        "tree",
        before == after and sorted(leftovers) == ["candidate.json", "solution.py"],
        f"candidate tree byte-identical after evaluation, files={sorted(leftovers)}",
    )


def check_revert() -> None:
    base = fresh("revert")
    worktree = base / "worktree"
    worktree.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "C_STAR" / "c01_good_hex" / "solution.py", worktree / "solution.py")
    env = dict(os.environ)
    for command in (
        ["git", "init", "-q", "."],
        ["git", "add", "-A"],
        ["git", "-c", "user.email=e@example.com", "-c", "user.name=e", "commit", "-qm", "init"],
    ):
        subprocess.run(command, cwd=str(worktree), env=env, check=True, capture_output=True)

    state = base / "state"
    out = base / "out.json"
    evaluate(worktree, out=out, state=state, cwd=base)
    state_before = tree_digest(state)
    out_before = digest_path(out)

    # The destructive candidate-worktree operations the protocol warns about.
    subprocess.run(["git", "checkout", "--", "."], cwd=str(worktree), env=env, check=True, capture_output=True)
    subprocess.run(["git", "clean", "-xfd"], cwd=str(worktree), env=env, check=True, capture_output=True)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=str(worktree), env=env, capture_output=True, text=True)

    state_after = tree_digest(state)
    out_after = digest_path(out)
    _, _, _, rerun = evaluate(worktree, out=base / "out2.json", state=base / "state", cwd=base)
    record(
        "revert",
        state_before == state_after and out_before == out_after and digest(rerun) == out_after,
        "state root and --out survived `git checkout . && git clean -xfd`; rerun is "
        f"byte-identical (worktree left clean: {status.stdout.strip()!r})",
    )


def measurement(outcome: dict[str, Any]) -> dict[str, Any]:
    """Everything the seed must not be able to move at full fidelity."""
    return {
        "status": outcome["status"],
        "scored": outcome["scored"],
        "failure_kind": (outcome.get("failure") or {}).get("kind"),
        "objective": outcome["objective"],
        "structure": outcome["structure"],
        "audit": {
            key: value
            for key, value in outcome["validity"]["audit"].items()
            if key not in {"seed"}
        },
        "checks": outcome["validity"]["checks"],
    }


def check_seed() -> None:
    base = fresh("seed")
    seeds = [0, 1, 2, 3, 1337, 7, 11, 42, 99, 4242, 31337, 5]

    full_measurements = {}
    full_samples = set()
    for candidate_id in ("c05_overlapping", "c01_good_hex"):
        candidate = ROOT / "C_STAR" / candidate_id
        for seed in seeds:
            _, _, _, payload = evaluate(
                candidate, out=base / f"{candidate_id}-full-{seed}.json",
                state=base / "state-full", cwd=base, seed=seed,
            )
            outcome = json.loads(payload)
            full_measurements.setdefault(candidate_id, set()).add(
                json.dumps(measurement(outcome), sort_keys=True)
            )
            full_samples.add(tuple(outcome["validity"]["audit"]["sample"]))

    fast_rows = []
    for seed in seeds:
        _, _, _, payload = evaluate(
            ROOT / "C_STAR" / "c05_overlapping",
            out=base / f"fast-{seed}.json",
            state=base / "state-fast",
            cwd=base,
            seed=seed,
            fidelity="fast",
            fraction=0.15,
        )
        outcome = json.loads(payload)
        fast_rows.append(
            (
                seed,
                outcome["status"],
                outcome["validity"]["audit"]["sample"],
                (outcome.get("structure") or {}).get("overlap_count"),
            )
        )
    fast_statuses = {row[1] for row in fast_rows}
    detail = (
        f"full: {len(full_measurements['c05_overlapping'])} distinct measurement(s) for "
        f"c05 and {len(full_measurements['c01_good_hex'])} for c01 over {len(seeds)} seeds, "
        f"samples audited={sorted(full_samples)}; fast(0.15) statuses={sorted(fast_statuses)}; "
        + "; ".join(f"seed {row[0]} -> {row[1]} {row[2]} overlap_count={row[3]}" for row in fast_rows[:4])
    )
    record(
        "seedful",
        len(full_measurements["c05_overlapping"]) == 1
        and len(full_measurements["c01_good_hex"]) == 1
        and full_samples == {tuple(range(26))}
        and len(fast_statuses) > 1,
        detail,
    )


def check_sideeffect() -> None:
    """A candidate that writes files must not be able to write into its own tree."""
    base = fresh("sideeffect")
    candidate = base / "candidate"
    candidate.mkdir(parents=True, exist_ok=True)
    (candidate / "solution.py").write_text(
        '"""Candidate with side effects: writes next to itself and into its cwd."""\n'
        "from pathlib import Path\n"
        "\n"
        "\n"
        "def pack_circles(n: int = 26):\n"
        "    here = Path(__file__).resolve().parent\n"
        "    (here / 'candidate_wrote_here.txt').write_text('mine\\n')\n"
        "    Path('cwd_write.txt').write_text('mine\\n')\n"
        "    return [(0.5, 0.5, 0.5)]\n",
        encoding="utf-8",
    )
    before = tree_digest(candidate)
    state = base / "state"
    evaluate(candidate, out=base / "out.json", state=state, cwd=base)
    after = tree_digest(candidate)
    in_tree = sorted(p.name for p in candidate.iterdir())
    in_state = sorted(
        str(p.relative_to(state)) for p in state.rglob("*") if p.is_file() and p.name.startswith(("candidate_wrote", "cwd_write"))
    )
    record(
        "sideeffect",
        before == after and in_tree == ["solution.py"] and len(in_state) >= 1,
        f"candidate's own writes never touched its tree (files={in_tree}); they landed under "
        f"the state root as {in_state}",
    )


CHECKS = {
    "cwd": check_cwd,
    "path": check_path,
    "env": check_env,
    "relocate": check_relocate,
    "tree": check_tree,
    "revert": check_revert,
    "seedful": check_seed,
    "sideeffect": check_sideeffect,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", action="append", choices=sorted(CHECKS), default=None)
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    names = args.only or list(CHECKS)
    for name in names:
        CHECKS[name]()
    failures = [name for name, passed, _ in RESULTS if not passed]
    print()
    print(f"{len(RESULTS) - len(failures)}/{len(RESULTS)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
