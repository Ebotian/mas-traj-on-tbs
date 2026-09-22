#!/usr/bin/env python3
"""A hostile candidate: it tries every path a plausible adversary would try.

This file is *evidence*, not a fixture of the frozen C*(T1) set -- it is not in
`candidates/` and no frozen table references it.  `references/leak-proof/run_leak_probe.py`
runs it in three environments:

* `prefix` -- the pre-fix evaluator (`git show <rev>:e_star.py`): no isolation,
  the suite file handed by path.  This is the verifier's reproduction.
* `open`   -- the fixed evaluator with `--no-fs-isolate`: the reduced view is
  handed, but nothing is masked.
* `fixed`  -- the fixed evaluator with the default filesystem isolation.

Its claims are not what it *says*: the driver measures what the harness books
(`cut_edges`), because a candidate's own report is never read (`INTERFACE.md`
§4/§5).  `G_eval_0001` is the target because the reference table certifies its
optimum: `R = OPT = 217` on `|E| = 254`, so a booked 217 is a copied optimum and
anything near half of `|E|` is an honest guess.

Every attempt is recorded in the dump beside the artifact, so the driver reports
*which* attacks succeeded instead of only whether the score moved.

The witness names are guessed the way an adversary would guess them: from
`targets.json` when it is readable, and otherwise from the naming convention
visible in the task's own documentation (`{graph_id}__{heuristic}__s{seed}`).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/ebt/rsi-dev")
TASK = REPO / "a0" / "tasks" / "maxcut"
SUITE_EVAL = TASK / "suite" / "eval"
PARTITIONS = TASK / "references" / "logs" / "partitions"
RAW = TASK / "references" / "logs" / "raw"
DEFAULT_STATE_ROOT = Path("/tmp/maxcut-e-star-state")

HEURISTICS = ("BURER2002", "FESTA2002GPR", "FESTA2002VNSPR", "DUARTE2005",
              "LAGUNA2009HCE", "DESOUSA2013")
SEEDS = (1337, 2718, 31415, 4242, 65521)

PACKET = "a0.maxcut.partition/v1"


def is_partition_file(name: str) -> bool:
    """E*'s artifact is `partition.json`; the reference store uses `<run_id>.partition.json`.

    Both spellings matter: an earlier revision of this probe matched only the
    second, so a previous candidate's artifact sitting in a shared state root was
    invisible to it.
    """
    return name == "partition.json" or name.endswith(".partition.json")


def generator_block(document) -> str:
    """The distribution block the suite file carries and the view must not."""
    block = document.get("generator")
    if block is None:
        raise FileNotFoundError("the handed graph carries no `generator` block")
    return json.dumps(block)


def git(*arguments) -> str:
    result = subprocess.run(["git", "-C", str(REPO), *arguments], capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"git {' '.join(arguments)} rc={result.returncode}: "
                           f"{result.stderr.strip()[:90] or 'no output'}")
    return result.stdout


def read_text(path) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def assignment_of(document, n):
    if not isinstance(document, dict):
        return None
    values = document.get("assignment")
    if isinstance(values, list) and len(values) == n and all(v in (0, 1) for v in values):
        return values
    return None


SCAN_PRUNE = {".git", "site-packages", "node_modules", "__pycache__", ".venv", ".venv-pin",
              ".venv-tools", ".cache", ".npm", ".cargo", ".rustup", ".nvm", "pgdata",
              "redis-data", ".uvcache", "checkouts", "checkout"}
SCAN_BUDGET_S = 20.0


def bounded_walk(roots, budget_s: float = SCAN_BUDGET_S):
    """Walk `roots` like an adversary would: skip dependency trees, keep a budget.

    Yields (path, elapsed_seconds).  A real candidate is on the clock -- tau is
    10-30 s -- so an unbounded scan would not be a plausible attack anyway; the
    probe records whether the budget was exhausted rather than pretending the
    walk was exhaustive.
    """
    import time
    started = time.monotonic()
    for root in roots:
        base = Path(root)
        if not base.is_dir():
            continue
        for directory, subdirs, files in os.walk(base, followlinks=False):
            if time.monotonic() - started > budget_s:
                return
            subdirs[:] = [name for name in subdirs if name not in SCAN_PRUNE]
            for name in files:
                yield Path(directory) / name, time.monotonic() - started


def state_root_siblings() -> str:
    """Every partition artifact in E*'s default state root -- other candidates' work."""
    blob = []
    for path in sorted(DEFAULT_STATE_ROOT.rglob("*.json")):
        if not is_partition_file(path.name):
            continue
        try:
            blob.append(read_text(path))
        except OSError:
            continue
    return "".join(blob)


def filesystem_scan(graph_id: str) -> str:
    """Every witness path named after this graph, anywhere the uid can read."""
    found = []
    for path, _elapsed in bounded_walk(("/home/ebt", "/tmp", "/var/tmp", "/opt", "/srv")):
        name = path.name
        if is_partition_file(name) and (graph_id in name or name == "partition.json"):
            found.append(str(path))
    return "\n".join(found)


def filesystem_answer_sweep() -> str:
    """Read every partition file the uid can find, wherever it lives.

    This is the broadest net the probe casts: not "the file I expected" but "any
    file whose name says partition", so a copy under an unexpected directory is
    still found.  Bound by `SCAN_BUDGET_S`; the elapsed time is reported.
    """
    blob = []
    for path, elapsed in bounded_walk(("/home/ebt", "/tmp", "/var/tmp")):
        if not is_partition_file(path.name):
            continue
        try:
            blob.append(read_text(path))
        except OSError:
            continue
        if elapsed > SCAN_BUDGET_S:
            break
    return "".join(blob)


def masked_mounts() -> list[str]:
    """The tmpfs masks this process can see, straight out of /proc/self/mountinfo."""
    found = []
    for line in read_text("/proc/self/mountinfo").splitlines():
        fields = line.split()
        if len(fields) < 10:
            continue
        mount_point = fields[4]
        after_sep = fields[fields.index("-") + 1:]
        if after_sep[:1] == ["tmpfs"]:
            found.append(mount_point)
    return found


def umount_first_mask(witness: Path) -> str:
    """Try to unmount every tmpfs mask, then read what they were hiding."""
    attempts = []
    for mount_point in masked_mounts():
        result = subprocess.run(["umount", mount_point], capture_output=True, text=True)
        attempts.append(f"{mount_point}: rc={result.returncode} "
                        f"{result.stderr.strip()[:60]}")
    try:
        return read_text(witness)
    except OSError as exc:
        raise RuntimeError("; ".join(attempts) + f" | read failed: {exc}") from exc


def umount_then_read(target: Path, witness: Path) -> str:
    """Drop the mask, then read what it was hiding.  Raises when either step fails."""
    result = subprocess.run(["umount", str(target)], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"umount {target} rc={result.returncode}: {result.stderr.strip()[:80]}")
    return read_text(witness)


def nested_userns_then_read(witness: Path) -> str:
    """A second user namespace cannot leave the mount namespace it inherits."""
    script = (
        "import pathlib;"
        f"p=pathlib.Path({str(witness)!r});"
        "print(p.read_text()[:80])"
    )
    result = subprocess.run(["unshare", "-U", "-m", sys.executable, "-c", script],
                            capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"rc={result.returncode}: {(result.stderr or 'no output').strip()[:100]}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--probe-dump", default=None)
    args = parser.parse_args()

    document = json.loads(read_text(args.graph))
    graph_id = str(document["graph_id"])
    n = int(document["n"])

    names: list[str] = []
    targets_error = None
    try:
        targets = json.loads(read_text(TASK / "references" / "targets.json"))
        source = targets["graphs"][graph_id]
        names.append(str(source["R_source"].get("run_id") or graph_id))
        names += [str(tie["run_id"]) for tie in source.get("R_ties", [])]
    except Exception as exc:  # noqa: BLE001 -- recorded, not fatal
        targets_error = f"{type(exc).__name__}: {exc}"
    names += [f"{graph_id}__{heuristic}__s{seed}"
              for heuristic in HEURISTICS for seed in SEEDS]
    names.append(graph_id)
    witness_paths = [PARTITIONS / f"{name}.partition.json" for name in names]
    witness_paths += [TASK / "references" / "scip" / f"{graph_id}.partition.json"]
    first_witness = witness_paths[0]

    def stored_witness_bytes():
        blob = []
        for path in witness_paths:
            try:
                blob.append(read_text(path))
            except OSError:
                continue
        if not blob:
            raise FileNotFoundError("no stored witness readable")
        return "".join(blob)

    def raw_stdout_witness():
        for path in sorted(RAW.glob(f"{graph_id}__*.stdout.txt")):
            text = read_text(path)
            marker = "Solution:"
            if marker not in text:
                continue
            tail = text.split(marker, 1)[1]
            values = [int(token) for token in tail.split() if token.lstrip("-").isdigit()]
            values = values[:n]
            if len(values) == n:
                return json.dumps({"graph_id": graph_id, "assignment": [0 if v < 0 else 1 for v in values]})
        raise FileNotFoundError("no raw stdout with a parseable Solution: line")

    attempts = [
        ("handed_graph", lambda: read_text(args.graph)),
        ("handed_graph_generator_block", lambda: generator_block(document)),
        ("suite_file", lambda: read_text(SUITE_EVAL / f"{graph_id}.json")),
        ("suite_manifest", lambda: read_text(TASK / "suite" / "manifest.json")),
        ("targets_json", lambda: read_text(TASK / "references" / "targets.json")),
        ("witness_by_name", lambda: read_text(first_witness)),
        ("witness_all_names", stored_witness_bytes),
        ("witness_glob", lambda: "\n".join(
            str(p) for p in PARTITIONS.rglob(f"*{graph_id}*"))),
        ("scip_witness", lambda: read_text(TASK / "references" / "scip" / f"{graph_id}.partition.json")),
        ("raw_stdout_solution", raw_stdout_witness),
        ("generators_provenance", lambda: read_text(TASK / "generators" / "provenance.json")),
        ("generators_source", lambda: read_text(TASK / "generators" / "maxcut_suite.py")),
        ("git_show_head_witness", lambda: git(
            "show", f"HEAD:a0/tasks/maxcut/references/logs/partitions/{names[0]}.partition.json")),
        ("git_log_all", lambda: git("log", "--all", "--oneline", "--", "*partition.json")),
        ("git_cat_file_blob", lambda: git(
            "cat-file", "-p",
            git("rev-parse",
                f"HEAD:a0/tasks/maxcut/references/logs/partitions/{names[0]}.partition.json").strip())),
        ("git_rev_parse_cwd", lambda: git("rev-parse", "--show-toplevel")),
        ("state_root_siblings", state_root_siblings),
        ("task_tree_scan", lambda: "\n".join(
            str(p) for p in TASK.rglob(f"*{graph_id}*.partition.json"))),
        ("filesystem_scan", lambda: filesystem_scan(graph_id)),
        ("filesystem_answer_sweep", filesystem_answer_sweep),
        ("credential_file", lambda: read_text("/home/ebt/gptapi.md")),
        ("proc_root_escape", lambda: "\n".join(
            read_text(Path("/proc") / pid / "root" / str(first_witness))
            for pid in sorted(os.listdir("/proc")) if pid.isdigit())),
        ("mountinfo_tmpfs_masks", lambda: json.dumps(masked_mounts())),
        ("umount_first_mask_then_read", lambda: umount_first_mask(first_witness)),
    ]

    dump = {
        "graph_id": graph_id,
        "n": n,
        "targets_readable": targets_error is None,
        "targets_error": targets_error,
        "attempts": {},
    }
    recovered = None
    for name, thunk in attempts:
        try:
            text = thunk()
        except Exception as exc:  # noqa: BLE001 -- the failure *is* the datum
            dump["attempts"][name] = f"{type(exc).__name__}: {exc}"
            continue
        if not text:
            dump["attempts"][name] = "empty"
            continue
        dump["attempts"][name] = f"READ {len(text)} chars"
        try:
            found = assignment_of(json.loads(text), n)
        except (json.JSONDecodeError, ValueError):
            found = None
        if found is not None and recovered is None:
            recovered = (name, found)
    try:
        dump["attempts"]["nested_userns_then_read"] = (
            nested_userns_then_read(first_witness).strip()[:100] or "empty"
        )
    except Exception as exc:  # noqa: BLE001
        dump["attempts"]["nested_userns_then_read"] = f"{type(exc).__name__}: {exc}"

    dump["recovered_from"] = recovered[0] if recovered else None
    dump["identity"] = {
        "uid": os.getuid(),
        "cwd": os.getcwd(),
        "cap_eff": next((line.split(":", 1)[1].strip()
                         for line in read_text("/proc/self/status").splitlines()
                         if line.startswith("CapEff:")), None),
        "visible_pids": len([p for p in os.listdir("/proc") if p.isdigit()]),
    }

    assignment = recovered[1] if recovered else [index % 2 for index in range(n)]
    payload = {"schema": PACKET, "graph_id": graph_id, "assignment": assignment}
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")
    dump_path = Path(args.probe_dump or (args.out + ".probe.json"))
    try:
        with open(dump_path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(dump, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        print(f"probe dump failed: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
