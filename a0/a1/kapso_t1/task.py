"""T1 (Frozen Max-Cut Heuristic Search) as KAPSO is shown it: text, ABI, visibility.

Three things live here and nowhere else:

1. ``T1_PROBLEM`` / ``T1_GOAL`` — the task text KAPSO's problem handler and
   maintainer are given. ``a0/runtimes/kapso/a0_adapter/runtime.py`` holds the
   plumbing task's text as module constants; this module holds T1's, and
   ``runtime_t1.bind_task_text()`` rebinds those two names for the duration of a
   T1 run (see ``a0/a1/kapso_t1/DEVIATIONS.md`` D-KT1-2 — the adapter is another
   workstream's file, so the retarget is done from this side).
2. ``CANDIDATE_ABI`` — ``INTERFACE.md`` §3/§4 exactly: the argv the candidate
   program is run with, the artifact it must write, its exit-code semantics, and
   the determinism rule. It is a declaration that the tree's locator also carries,
   and the dry run checks the two agree.
3. The **visibility rule**: which instances the agent may see. ``INTERFACE.md`` §1
   makes dev visible and eval a hold-out; §12 forbids the eval set entering the
   agent's workspace, context or any path it can read, and forbids using the
   calibration set for any algorithmic selection. ``materialize_dev_graphs`` is the
   executable half of the rule — it copies *only* ``role == "dev"`` instances,
   checks each file's sha256 against the frozen ``suite/manifest.json``, writes a
   sha256 index beside them, and refuses anything else by construction.
   ``scan_for_holdout_bytes`` is the negative check: after materialization, no file
   anywhere in the workspace hashes to an eval or calibration instance.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

#: Where the agent-readable instances land inside KAPSO's workspace. This path is
#: also `evaluation_maintainer.protected_data_paths` in config/mode.maxcut.yaml, so
#: KAPSO hashes it into the evaluator version and voids any node that rewrites it.
DEV_RELATIVE_PATH = "kapso_datasets/maxcut/dev"
DEV_INDEX_NAME = "GRAPHS-DEV.json"

T1_PROBLEM = """\
T1 — frozen Max-Cut heuristic search.

The artifact is a *program*. Write `solution.py` at the repository root, runnable as

    python solution.py --graph <abs path to graph.json> --out <abs path to partition.json> --seed <int>

- It reads a §2 graph: `{"schema":"a0.maxcut.graph/v1","graph_id":…,"family":…,"n":128,
  "edges":[[u,v],…],"generator":…,"notes":…}` — `n = 128`, unit weights, no self-loops,
  no duplicate edges, `u < v`, edges sorted.
- It writes a §3 partition to `--out`, and nowhere else:
  `{"schema":"a0.maxcut.partition/v1","graph_id":"<the graph's id>","assignment":[0,1,…]}`
  with exactly `n` entries, each the integer 0 or 1, in canonical JSON
  (sorted keys, compact separators, one trailing newline).
- Exit codes: 0 = produced something; 20 = the candidate declares its own output
  invalid; 30 = internal error; 40 = refusal. Any other non-zero is an error.
- It must not depend on the working directory, `PATH`, any file other than the graph
  it is given, or the network. It is run with a minimal environment and no network.
- Determinism is part of the contract: the same graph bytes and the same `--seed`
  must produce byte-identical `partition.json`.

The objective is `cut_edges` — the number of edges whose endpoints are in different
sides — recomputed by the harness-owned evaluator from the graph and the partition.
**Do not report a score.** No number the program prints or writes is read; a
`status != ok` is never folded into 0. The number in the experiment's record is the
harness's, always.

Visible data: the 24 development graphs under `kapso_datasets/maxcut/dev/`, indexed by
`kapso_datasets/maxcut/dev/GRAPHS-DEV.json` with each file's sha256. They are
protected inputs: a candidate that rewrites one is not scored on this task at all.
The 24 hold-out `eval` instances and the 12 `calibration` instances are not in this
workspace and must not be sought: `eval` is scored once at the end, and `calibration`
is for measuring resource rates, never for algorithmic selection.

Budget: tau = 10 s of wall clock per graph (the harness SIGKILLs the process group at
tau, which is recorded as `timeout`, not as a score). Aim well below it — the
calibrated p99 is what tau was derived from.
"""

T1_GOAL = (
    "Evolve `solution.py`, a deterministic max-cut heuristic over the frozen T1 "
    "instance suite: given any §2 graph (`--graph`) it must emit a §3 partition "
    "(`--out`) within tau = 10 s, maximizing the harness-measured `cut_edges` on the "
    "unseen eval instances. The result must be a function of the graph bytes and "
    "`--seed` alone. `kapso_datasets/maxcut/dev/` holds the instances the agent may "
    "read; the eval and calibration instances are not part of the campaign."
)

#: `INTERFACE.md` §4, as a machine-readable declaration. The tree's locator carries
#: the same block; the dry run asserts the two are equal, so the text above and the
#: registered configuration cannot drift apart silently.
CANDIDATE_ABI: Dict[str, Any] = {
    "entry": "solution.py",
    "argv": [
        "python", "solution.py",
        "--graph", "<abs path to the §2 graph.json>",
        "--out", "<abs path to write the §3 partition.json>",
        "--seed", "<int>",
    ],
    "input": {"schema": "a0.maxcut.graph/v1", "read_only": True},
    "artifact": {"schema": "a0.maxcut.partition/v1", "file": "partition.json"},
    "exit_codes": {
        "0": "the candidate believes it produced output; the harness still decides",
        "20": "the candidate declares its own output invalid",
        "30": "the candidate's internal error",
        "40": "the candidate refuses to run",
        "other_non_zero": "recorded as `error` with the original code",
    },
    "timeout": "not an exit code: at tau the harness SIGKILLs the process group",
    "environment": {
        "network": "none",
        "home_cwd": "a private scratch directory",
        "python_dont_write_bytecode": "1",
        "proxy_variables": "cleared",
    },
    "determinism": "INTERFACE.md §6 rule 4: canonical partition bytes identical over two runs",
    "self_reported_score": "forbidden and unread (INTERFACE.md §12)",
    "source": "a0/tasks/maxcut/INTERFACE.md §3-§4, §6",
}

SCORE_SEMANTICS = {
    "authoritative_field": "cut_edges",
    "type": "integer",
    "direction": "maximize",
    "failure_semantics": (
        "invalid/error/timeout carry cut_edges: null — never 0; a legitimate 0 is 0"
    ),
    "aggregate": "fractions.Fraction over integers; the display field cut_fraction is never compared",
    "measured_by": "the harness-owned evaluator E* (a0/tasks/maxcut/e_star.py), outside the session",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_suite_manifest(suite_root: Path) -> Dict[str, Any]:
    path = Path(suite_root) / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "a0.maxcut.suite.manifest/v1":
        raise RuntimeError(f"unexpected suite manifest schema {manifest.get('schema')!r}")
    return manifest


def instances_by_role(suite_root: Path, role: str) -> List[Dict[str, Any]]:
    """The frozen instances of one role, each with its path and recorded sha256."""
    suite_root = Path(suite_root)
    manifest = load_suite_manifest(suite_root)
    rows = [row for row in manifest["graphs"] if row.get("role") == role]
    return [
        {
            "graph_id": row["graph_id"],
            "family": row["family"],
            "stratum": row.get("stratum"),
            "n": row["n"],
            "edges": row["edges"],
            "path": str(suite_root / row["path"]),
            "relative_path": row["path"],
            "graph_sha256": row["graph_sha256"],
        }
        for row in rows
    ]


def materialize_dev_graphs(workspace_dir: Path, suite_root: Path,
                           dest_relative: str = DEV_RELATIVE_PATH) -> Dict[str, Any]:
    """Copy the 24 dev instances into the workspace, sha256-checked, and index them.

    Only `role == "dev"` rows are considered: `instances_by_role` selects them from
    the frozen manifest, and every copied byte is re-hashed and compared with the
    manifest's own digest before the index is written. An empty or short dev set is a
    failure, not a quietly smaller workspace.
    """
    workspace_dir = Path(workspace_dir).resolve()
    suite_root = Path(suite_root).resolve()
    dest = workspace_dir / dest_relative
    rows = instances_by_role(suite_root, "dev")
    if len(rows) != 24:
        raise RuntimeError(
            f"the dev role holds {len(rows)} instances, not 24; refusing to materialize a "
            "workspace whose visible set is not the frozen one"
        )
    dest.mkdir(parents=True, exist_ok=True)
    members = []
    for row in rows:
        source = Path(row["path"])
        actual = sha256_file(source)
        if actual != row["graph_sha256"]:
            raise RuntimeError(
                f"{row['graph_id']}: sha256 {actual} != the frozen manifest's "
                f"{row['graph_sha256']}"
            )
        target = dest / source.name
        shutil.copyfile(source, target)
        members.append({
            "graph_id": row["graph_id"],
            "family": row["family"],
            "stratum": row["stratum"],
            "n": row["n"],
            "edges": row["edges"],
            "file": target.name,
            "sha256": actual,
        })
    index = {
        "schema": "a0.kapso_t1.dev_index/v1",
        "role": "dev",
        "visible_to_the_agent": True,
        "count": len(members),
        "source_manifest": "a0/tasks/maxcut/suite/manifest.json",
        "source_manifest_sha256": sha256_file(suite_root / "manifest.json"),
        "note": (
            "These are the only instances the agent may read (INTERFACE.md §1). The "
            "eval and calibration instances are not in this workspace."
        ),
        "members": sorted(members, key=lambda item: item["graph_id"]),
    }
    (dest / DEV_INDEX_NAME).write_text(
        json.dumps(index, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "dest": str(dest),
        "dest_relative": dest_relative,
        "index": str(dest / DEV_INDEX_NAME),
        "count": len(members),
        "members": index["members"],
        "source_manifest_sha256": index["source_manifest_sha256"],
    }


def scan_for_holdout_bytes(workspace_dir: Path, suite_root: Path) -> List[Dict[str, str]]:
    """Every workspace file whose bytes are an eval/calibration instance, if any.

    The negative form of the visibility rule: it does not check that dev is present,
    it checks that *no hold-out instance is reachable* anywhere under the workspace,
    including under a renamed file.
    """
    workspace_dir = Path(workspace_dir)
    holdout = {}
    for role in ("eval", "calibration"):
        for row in instances_by_role(Path(suite_root), role):
            holdout[row["graph_sha256"]] = f"{role}:{row['graph_id']}"
    hits = []
    for path in sorted(workspace_dir.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            digest = sha256_file(path)
        except OSError:
            continue
        if digest in holdout:
            hits.append({"path": str(path), "instance": holdout[digest]})
    return hits


def holdout_digests(suite_root: Path) -> Dict[str, str]:
    """sha256 -> "<role>:<graph_id>" for eval and calibration, for reporting."""
    out = {}
    for role in ("eval", "calibration"):
        for row in instances_by_role(Path(suite_root), role):
            out[row["graph_sha256"]] = f"{role}:{row['graph_id']}"
    return out
