#!/usr/bin/env python3
"""C*(T1) conformance: run every fixed candidate through E* and check the verdicts.

This is where the evaluator's *behaviour* is pinned, separately from its source.
It plays two roles:

1. **Regression table.**  Every member of `C*(T1)` is run and reduced to
   `(status, cut_edges, failure.kind)` -- the three values `INTERFACE.md` §6
   decides.  `--freeze` writes that table to `conformance.expected.json`;
   `--check` re-runs the whole set and fails on any drift.  The table is the
   thing a later change to E* has to keep reproducing.
2. **The T1 brief's proofs.**  The six claims the brief requires are checked
   here by execution, not asserted: cwd/PATH independence, determinism,
   failure semantics, network independence, child-environment cleanliness, and
   exact aggregation.  Each probe records the evidence it read.

    python3 conformance.py --freeze     # produce the frozen table
    python3 conformance.py --check      # re-run and compare (exit 0 = no drift)

The suite of graphs is auto-detected: the frozen `suite/dev/` when it exists,
otherwise the task-owned temporary stand-in under `graphs_tmp/`.  Every result
records which one was used.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import test_candidate_staging  # noqa: E402  (the D-T1-10 regression, one implementation)

E_STAR = HERE / "e_star.py"
CANDIDATES = HERE / "candidates"
EXPECTED_PATH = HERE / "conformance.expected.json"
REPORT_PATH = HERE / "conformance.report.json"

SEED = 1337
#: §7's band is [10, 30] s.  The sweep uses its lower edge, so the timeout row
#: costs 2 x tau and every other row is bounded by the same tau.
TAU_S = 10.0

PROXY_NAMES = (
    "http_proxy", "https_proxy", "no_proxy", "all_proxy",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY",
)
#: §4: "不注入任何密钥".  Matched case-insensitively against the child's own dump.
CREDENTIAL_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "CREDENTIAL", "AUTH")
#: §4's environment, verbatim: nothing else may appear in the child.
ALLOWED_ENV_KEYS = {"PATH", "PYTHONDONTWRITEBYTECODE", "HOME", "LANG"}

DECOYS = {
    "http_proxy": "http://poison.invalid:3128",
    "https_proxy": "http://poison.invalid:3128",
    "HTTPS_PROXY": "http://poison.invalid:3128",
    "no_proxy": "localhost",
    "OPENAI_API_KEY": "sk-should-never-reach-the-child",
    "MAXCUT_DECOY_SECRET": "do-not-leak",
    "AWS_SECRET_ACCESS_KEY": "do-not-leak",
}


def canonical_bytes(payload: object) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# targets
# --------------------------------------------------------------------------- #

def target_graph(suite_root: Path) -> dict[str, object]:
    """The graph every row is measured on: the frozen suite when it exists."""
    frozen_root = (HERE / "suite").resolve()
    candidates = [
        (Path(suite_root).expanduser().resolve(), "temporary"),
        (HERE / "graphs_tmp" / "tmp_suite", "temporary"),
    ]
    for root, fallback_label in candidates:
        directory = root / "dev"
        if not directory.is_dir():
            continue
        paths = sorted(directory.glob("*.json"))
        if not paths:
            continue
        path = paths[0].resolve()
        label = "frozen-suite" if frozen_root in path.parents else fallback_label
        return {
            "path": str(path),
            "source": label,
            "graph_id": json.loads(path.read_text(encoding="utf-8"))["graph_id"],
            "sha256": sha256_file(path),
            "graph_set_dir": str(directory),
        }
    raise SystemExit("conformance: no dev graph set found (neither suite/dev nor graphs_tmp/tmp_suite/dev)")


def load_candidate_manifest() -> list[dict[str, object]]:
    manifest = json.loads((CANDIDATES / "manifest.json").read_text(encoding="utf-8"))
    return list(manifest["candidates"])


# --------------------------------------------------------------------------- #
# running E*
# --------------------------------------------------------------------------- #

def run_e_star(
    arguments: list[str],
    *,
    state_dir: Path,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout_s: float = 600.0,
) -> subprocess.CompletedProcess:
    command = [sys.executable, str(E_STAR), *arguments, "--state-dir", str(state_dir)]
    return subprocess.run(
        command, cwd=str(cwd) if cwd else None, env=env,
        capture_output=True, text=True, timeout=timeout_s, check=False,
    )


def sweep(
    *, graph: dict[str, object], candidates: list[dict[str, object]], work: Path, env: dict[str, str],
) -> list[dict[str, object]]:
    """Run every candidate once and reduce it to the §6 verdict triple."""
    rows: list[dict[str, object]] = []
    state_dir = work / "state"
    for entry in candidates:
        candidate_id = str(entry["candidate_id"])
        extra: list[str] = []
        graph_path = Path(str(graph["path"]))
        if entry.get("expected", {}).get("needs_private_graph_copy"):  # type: ignore[union-attr]
            private = work / "private-graphs" / candidate_id
            private.mkdir(parents=True, exist_ok=True)
            graph_path = private / Path(str(graph["path"])).name
            shutil.copy2(Path(str(graph["path"])), graph_path)
        if candidate_id == "c15_error_network_attempt":
            # The closed topology is a precondition of the measurement, so this
            # row asks E* to enforce it rather than trusting the host.
            extra.append("--net-isolate")
        out_path = work / "outcomes" / f"{candidate_id}.outcome.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        completed = run_e_star(
            ["evaluate", "--candidate", str(CANDIDATES / candidate_id), "--graph", str(graph_path),
             "--seed", str(SEED), "--timeout", str(TAU_S), "--out", str(out_path), *extra],
            state_dir=state_dir, env=env,
        )
        if not out_path.is_file():
            raise SystemExit(
                f"conformance: E* produced no Outcome for {candidate_id} "
                f"(exit {completed.returncode}): {completed.stderr[-800:]}"
            )
        outcome = json.loads(out_path.read_text(encoding="utf-8"))
        failure = outcome.get("failure") or {}
        rows.append({
            "candidate_id": candidate_id,
            "kind": entry["kind"],
            "graph_id": outcome["graph_id"],
            "graph_sha256": outcome["graph_sha256"],
            "candidate_source_sha256": outcome["candidate_source_sha256"],
            "manifest_source_sha256": entry["source_sha256"],
            "status": outcome["status"],
            "cut_edges": outcome["cut_edges"],
            "failure_kind": failure.get("kind"),
            "outcome_digest": outcome["canonical_digest"],
            "evaluator_exit_code": completed.returncode,
            "partition_sha256": outcome["determinism"]["canonical_sha256"][0],
            "determinism_identical": outcome["determinism"]["identical"],
            "exit_codes": outcome["interpreted"]["exit_codes"],
        })
    return rows


def compare_rows(frozen: dict[str, object], rows: list[dict[str, object]]) -> list[str]:
    """Compare only the frozen triple plus the candidate identity."""
    problems: list[str] = []
    expected_rows = {str(row["candidate_id"]): row for row in frozen["rows"]}  # type: ignore[index]
    actual_rows = {str(row["candidate_id"]): row for row in rows}
    for candidate_id in sorted(set(expected_rows) | set(actual_rows)):
        if candidate_id not in expected_rows:
            problems.append(f"{candidate_id}: not in the frozen table (new candidate)")
            continue
        if candidate_id not in actual_rows:
            problems.append(f"{candidate_id}: missing from this run")
            continue
        expected, actual = expected_rows[candidate_id], actual_rows[candidate_id]
        for key in ("status", "cut_edges", "failure_kind", "candidate_source_sha256", "evaluator_exit_code"):
            if expected.get(key) != actual.get(key):
                problems.append(f"{candidate_id}: {key} drifted {expected.get(key)!r} -> {actual.get(key)!r}")
    return problems


# --------------------------------------------------------------------------- #
# the proofs
# --------------------------------------------------------------------------- #

def probe_cwd_path(graph: dict[str, object], work: Path) -> dict[str, object]:
    """Proof #1: two working directories, a poisoned PATH and hostile env, one measurement."""
    poisoned = {
        "PATH": "/nonexistent-poison:/also/missing",
        "PYTHONPATH": "/nonexistent-poison-python",
        "HOME": "/nonexistent-poison-home",
        "LANG": "C.UTF-8",
        **DECOYS,
    }
    digests = []
    for index, cwd_name in enumerate(("cwd-alpha", "cwd-beta")):
        cwd = work / cwd_name
        cwd.mkdir(parents=True, exist_ok=True)
        out_path = work / "cwd-path" / f"run{index + 1}.outcome.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        completed = run_e_star(
            ["evaluate", "--candidate", str(CANDIDATES / "c01_ok_high_pc"),
             "--graph", str(graph["path"]), "--seed", str(SEED), "--timeout", str(TAU_S),
             "--out", str(out_path)],
            state_dir=work / "cwd-path" / "state", cwd=cwd, env=poisoned,
        )
        if not out_path.is_file():
            return {"ok": False, "detail": f"no Outcome from cwd {cwd}: {completed.stderr[-400:]}"}
        digests.append({
            "cwd": str(cwd),
            "path_argument": poisoned["PATH"],
            "outcome_sha256": sha256_file(out_path),
            "status": json.loads(out_path.read_text(encoding="utf-8"))["status"],
            "bytes": out_path.stat().st_size,
        })
    identical = len({item["outcome_sha256"] for item in digests}) == 1
    return {
        "ok": identical and all(item["status"] == "ok" for item in digests),
        "claim": "two working directories with a poisoned PATH yield byte-identical Outcome files",
        "runs": digests,
        "byte_identical": identical,
    }


def probe_environment(graph: dict[str, object], work: Path) -> dict[str, object]:
    """Proof #5: read the child's environment from inside the child."""
    out_path = work / "env" / "c20.outcome.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, **DECOYS}
    completed = run_e_star(
        ["evaluate", "--candidate", str(CANDIDATES / "c20_env_probe"), "--graph", str(graph["path"]),
         "--seed", str(SEED), "--timeout", str(TAU_S), "--out", str(out_path)],
        state_dir=work / "env" / "state", env=env,
    )
    dump_path = Path(str(out_path) + ".env_probe.json")
    if not dump_path.is_file():
        # The candidate writes its dump beside *its* --out (the artifact path E*
        # hands it inside the private run directory), not beside E*'s Outcome.
        found = sorted(glob.glob(str(work / "env" / "state" / "**" / "partition.json.env_probe.json"),
                                 recursive=True))
        if not found:
            return {"ok": False, "detail": f"the probe wrote no environment dump: {completed.stderr[-400:]}"}
        dump_path = Path(found[-1])
    dump = json.loads(dump_path.read_text(encoding="utf-8"))
    observed = dump["environ"]
    present_proxies = sorted(name for name in PROXY_NAMES if name in observed)
    suspicious = sorted(
        name for name in observed
        if any(marker in name.upper() for marker in CREDENTIAL_MARKERS)
    )
    leaked_decoys = sorted(name for name in DECOYS if name in observed)
    unexpected = sorted(set(observed) - ALLOWED_ENV_KEYS)
    return {
        "ok": not present_proxies and not suspicious and not leaked_decoys and not unexpected,
        "claim": "the child environment is exactly §4's set: no proxy variable, no credential, nothing inherited",
        "observed_keys": sorted(observed),
        "observed_values": observed,
        "proxy_variables_present": present_proxies,
        "credential_like_names_present": suspicious,
        "decoy_variables_from_the_parent": leaked_decoys,
        "keys_outside_§4": unexpected,
        "parent_env_had_decoys": sorted(DECOYS),
        "child_cwd": dump["cwd"],
        "child_argv": dump["argv"],
    }


def probe_failure_semantics(rows: list[dict[str, object]]) -> dict[str, object]:
    """Proof #3: a non-ok status never contributes a number, and never a zero."""
    violations = []
    for row in rows:
        status, cut = row["status"], row["cut_edges"]
        if status == "ok":
            if not isinstance(cut, int) or isinstance(cut, bool):
                violations.append(f"{row['candidate_id']}: ok with non-integer cut_edges {cut!r}")
        else:
            if cut is not None:
                violations.append(f"{row['candidate_id']}: {status} with cut_edges {cut!r} (must be null)")
            if not row["failure_kind"]:
                violations.append(f"{row['candidate_id']}: {status} with no failure.kind")
        if row["status"] != "ok" and row["cut_edges"] == 0:
            violations.append(f"{row['candidate_id']}: {status} reported as 0")
    by_status: dict[str, list[str]] = {}
    for row in rows:
        by_status.setdefault(str(row["status"]), []).append(str(row["candidate_id"]))
    return {
        "ok": not violations,
        "claim": "cut_edges is null for every invalid/error/timeout row and never 0",
        "non_ok_rows": {k: v for k, v in by_status.items() if k != "ok"},
        "ok_rows": by_status.get("ok", []),
        "violations": violations,
    }


def probe_determinism(rows: list[dict[str, object]], graph: dict[str, object], work: Path) -> dict[str, object]:
    """Proof #2: a seeded candidate reproduces its partition bytes; an unseeded one does not."""
    evidence = {}
    for candidate_id, expectation in (
        ("c01_ok_high_pc", "identical"),
        ("c13_error_non_deterministic", "different"),
    ):
        outcome_paths = []
        for index in (1, 2):
            out_path = work / "determinism" / f"{candidate_id}.{index}.outcome.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            run_e_star(
                ["evaluate", "--candidate", str(CANDIDATES / candidate_id), "--graph", str(graph["path"]),
                 "--seed", str(SEED), "--timeout", str(TAU_S), "--out", str(out_path)],
                state_dir=work / "determinism" / "state",
            )
            outcome_paths.append(json.loads(out_path.read_text(encoding="utf-8")))
        sha = [item["determinism"]["canonical_sha256"] for item in outcome_paths]
        evidence[candidate_id] = {
            "expectation": expectation,
            "partition_canonical_sha256": sha,
            "identical": sha[0] == sha[1],
            "statuses": [item["status"] for item in outcome_paths],
            "failure_kinds": [(item["failure"] or {}).get("kind") for item in outcome_paths],
        }
    ok = (
        evidence["c01_ok_high_pc"]["identical"] is True
        and evidence["c13_error_non_deterministic"]["identical"] is False
        and all(status == "error" for status in evidence["c13_error_non_deterministic"]["statuses"])
        and evidence["c13_error_non_deterministic"]["failure_kinds"] == ["non_deterministic"] * 2
    )
    return {
        "ok": ok,
        "claim": "two full evaluations of the same (candidate bytes, graph bytes, seed) either agree byte-for-byte or are recorded non_deterministic",
        "evidence": evidence,
    }


def probe_network(graph: dict[str, object], work: Path) -> dict[str, object]:
    """Proof #4 plus §10's network row, measured in a route-less namespace."""
    if shutil.which("unshare") is None:
        return {"ok": False, "detail": "`unshare` is not available; the closed topology cannot be reached"}
    results = {}
    for candidate_id in ("c01_ok_high_pc", "c15_error_network_attempt"):
        out_path = work / "network" / f"{candidate_id}.outcome.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            ["unshare", "-rn", sys.executable, str(E_STAR), "evaluate",
             "--candidate", str(CANDIDATES / candidate_id), "--graph", str(graph["path"]),
             "--seed", str(SEED), "--timeout", str(TAU_S), "--out", str(out_path),
             "--state-dir", str(work / "network" / "state")],
            capture_output=True, text=True, check=False,
        )
        outcome = json.loads(out_path.read_text(encoding="utf-8"))
        results[candidate_id] = {
            "status": outcome["status"],
            "cut_edges": outcome["cut_edges"],
            "failure_kind": (outcome["failure"] or {}).get("kind"),
            "evaluator_exit_code": completed.returncode,
        }
    # The oracle: the same candidate's verdict with the network present.
    open_path = work / "network" / "c15_open_topology.outcome.json"
    run_e_star(
        ["evaluate", "--candidate", str(CANDIDATES / "c15_error_network_attempt"),
         "--graph", str(graph["path"]), "--seed", str(SEED), "--timeout", str(TAU_S), "--out", str(open_path)],
        state_dir=work / "network" / "open-state",
    )
    open_outcome = json.loads(open_path.read_text(encoding="utf-8"))
    return {
        "ok": (
            results["c01_ok_high_pc"]["status"] == "ok"
            and results["c15_error_network_attempt"]["status"] == "error"
            and results["c15_error_network_attempt"]["failure_kind"] == "candidate_refused"
        ),
        "claim": "inside `unshare -rn` a normal candidate still scores ok, and the network-reaching "
                 "candidate cannot run and refuses",
        "closed_topology": results,
        "open_topology_reference": {
            "status": open_outcome["status"],
            "cut_edges": open_outcome["cut_edges"],
            "failure_kind": (open_outcome["failure"] or {}).get("kind"),
        },
        "note": "the open-topology row is recorded for contrast only; it is never a measurement row",
    }


def probe_process_group(work: Path) -> dict[str, object]:
    """§7: the SIGKILL goes to the process group, so a forked grandchild dies too.

    A finite wait would only show that the sentinel had not been written *yet*.
    The candidate's grandchild therefore free-runs a heartbeat instead of
    sleeping a fixed time, and the proof is that the count stops changing once
    the verdict has been taken.
    """
    import time as _time

    beats = sorted(glob.glob(str(work / "**" / "*orphan_heartbeat*"), recursive=True))
    before = {path: len(Path(path).read_text(encoding="utf-8").splitlines()) for path in beats}
    _time.sleep(3.0)
    after = {
        path: (len(Path(path).read_text(encoding="utf-8").splitlines()) if Path(path).is_file() else None)
        for path in beats
    }
    frozen = {path: before[path] for path in beats if before[path] == after.get(path)}
    return {
        "ok": bool(beats) and set(before) == set(frozen) and all(count > 0 for count in before.values()),
        "claim": "c19's forked grandchild keeps a heartbeat file growing while it lives; after tau no "
                 "heartbeat file changes any more, so the whole process group was killed",
        "heartbeat_files": beats,
        "beats_at_verdict": before,
        "beats_3s_later": after,
        "stopped": sorted(frozen),
    }


def probe_exact_aggregation(work: Path) -> dict[str, object]:
    """Proof #6: the rational result, next to what float summation would have said."""
    sets = {"A": HERE / "graphs_tmp" / "float_tie_A", "B": HERE / "graphs_tmp" / "float_tie_B"}
    results: dict[str, object] = {}
    for name, suite_root in sets.items():
        state_dir = work / "aggregate" / f"state-{name}"
        out_path = work / "aggregate" / f"aggregate-{name}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        completed = run_e_star(
            ["aggregate", "--candidate", str(CANDIDATES / "c21_ok_parity_probe"),
             "--graph-set", "dev", "--suite-root", str(suite_root), "--out", str(out_path),
             "--seed", str(SEED), "--timeout", str(TAU_S)],
            state_dir=state_dir,
        )
        aggregate = json.loads(out_path.read_text(encoding="utf-8"))
        per_graph = []
        for outcome_path in sorted(glob.glob(str(state_dir / "aggregate" / "*" / "*.outcome.json"))):
            outcome = json.loads(Path(outcome_path).read_text(encoding="utf-8"))
            per_graph.append((outcome["graph_id"], outcome["cut_edges"], outcome["edges_total"]))
        cuts = [cut for _, cut, _ in per_graph]
        edges = [total for _, _, total in per_graph]
        results[name] = {
            "suite_root": str(suite_root),
            "counts": aggregate["counts"],
            "score_exact": aggregate["score_exact"],
            "per_graph": per_graph,
            "sum_cut_edges": sum(cuts),
            "sum_edges_total": sum(edges),
            "edges_per_graph_equal": len(set(edges)) == 1,
            "evaluator_exit_code": completed.returncode,
            # The float that a naive implementation would report.  Written here,
            # independently of E*, precisely so it is not the thing being tested.
            "naive_float_mean_of_ratios": sum(c / e for c, e in zip(cuts, edges)) / len(cuts),
        }
    exact = {name: Fraction(data["score_exact"]["numerator"], data["score_exact"]["denominator"])
             for name, data in results.items()}
    float_values = {name: data["naive_float_mean_of_ratios"] for name, data in results.items()}
    exact_equal = exact["A"] == exact["B"]
    float_equal = float_values["A"] == float_values["B"]
    return {
        "ok": exact_equal and not float_equal,
        "claim": "two graph sets whose exact scores are the same rational are reported EQUAL, while "
                 "float summation over the same edges ranks one of them strictly higher",
        "sets": results,
        "exact": {name: f"{value.numerator}/{value.denominator}" for name, value in exact.items()},
        "exact_equal": exact_equal,
        "naive_float": float_values,
        "naive_float_equal": float_equal,
        "naive_float_would_rank": (
            None if float_equal else ("A" if float_values["A"] > float_values["B"] else "B")
        ),
        "why_this_is_a_real_difference": (
            "within each set every graph has the same |E|, so the mean of per-graph rates is "
            "mathematically identical to sum(cut)/sum(edges); the residual difference is float error "
            "alone, and it is enough to invert an exact tie"
        ),
    }


def probe_float_tie(rows: list[dict[str, object]]) -> dict[str, object]:
    """§10's byte-different numerical tie pair."""
    by_id = {str(row["candidate_id"]): row for row in rows}
    a, b = by_id["c04_tie_a_pc_optimum"], by_id["c05_tie_b_pc_complement"]
    return {
        "ok": a["cut_edges"] == b["cut_edges"] and a["partition_sha256"] != b["partition_sha256"],
        "claim": "c04 and c05 are an exact integer tie with different partition bytes",
        "c04": {"cut_edges": a["cut_edges"], "partition_sha256": a["partition_sha256"]},
        "c05": {"cut_edges": b["cut_edges"], "partition_sha256": b["partition_sha256"]},
    }


def probe_ordered_pair(rows: list[dict[str, object]]) -> dict[str, object]:
    by_id = {str(row["candidate_id"]): row for row in rows}
    high, low = by_id["c01_ok_high_pc"], by_id["c02_ok_low_baseline"]
    return {
        "ok": high["cut_edges"] > low["cut_edges"] and low["cut_edges"] > 0,
        "claim": "the ok-high and ok-low rows are separated by an integer margin, with the low row a real number",
        "high": high["cut_edges"],
        "low": low["cut_edges"],
        "margin": high["cut_edges"] - low["cut_edges"],
    }


def probe_legitimate_zero(rows: list[dict[str, object]]) -> dict[str, object]:
    by_id = {str(row["candidate_id"]): row for row in rows}
    zero = by_id["c03_ok_zero_all_one_side"]
    return {
        "ok": zero["status"] == "ok" and zero["cut_edges"] == 0,
        "claim": "a genuine zero is reported as 0 and a failure is reported as null; the two are distinguishable",
        "c03": {"status": zero["status"], "cut_edges": zero["cut_edges"]},
    }


def probe_inflation_attempt(rows: list[dict[str, object]], graph: dict[str, object]) -> dict[str, object]:
    """Constraint (ii): rewriting the input cannot buy a score."""
    by_id = {str(row["candidate_id"]): row for row in rows}
    row = by_id["c18_ok_inflation_attempt"]
    edges = json.loads(Path(str(graph["path"])).read_text(encoding="utf-8"))["edges"]
    n = json.loads(Path(str(graph["path"])).read_text(encoding="utf-8"))["n"]
    assignment = [index % 2 for index in range(n)]
    true_cut = sum(1 for u, v in edges if assignment[u] != assignment[v])
    inflated = true_cut + true_cut  # the candidate doubles every cut edge
    return {
        "ok": row["cut_edges"] == true_cut and row["cut_edges"] != inflated,
        "claim": "c18 doubles every cut edge in graph.json mid-run and restores the original bytes; the "
                 "measured cut is the true one, recomputed from the harness's frozen copy",
        "measured_cut_edges": row["cut_edges"],
        "recomputed_from_the_frozen_graph": true_cut,
        "what_the_doctored_file_would_have_said": inflated,
        "graph_sha256_unchanged": sha256_file(Path(str(graph["path"]))) == graph["sha256"],
    }


def probe_input_tampering_detected(rows: list[dict[str, object]]) -> dict[str, object]:
    by_id = {str(row["candidate_id"]): row for row in rows}
    row = by_id["c17_error_input_tampered"]
    return {
        "ok": row["status"] == "error" and row["failure_kind"] == "input_tampered" and row["cut_edges"] is None,
        "claim": "c17 rewrites its input and leaves it rewritten; E* reports the change and emits no number",
        "c17": {"status": row["status"], "failure_kind": row["failure_kind"], "cut_edges": row["cut_edges"]},
    }


def probe_candidate_staging(graph: dict[str, object], work: Path) -> dict[str, object]:
    """D-T1-10 regression, run as part of the standing conformance.

    Asserting the defect stays fixed in the *live* tree is the whole point: the
    defect was a launch decision made from a file attribute the candidate's
    identity does not cover, and no amount of reading the source reliably catches
    a recurrence.  The implementation lives in `test_candidate_staging.py` so
    there is one copy; this is a second entry point, not a second test.
    """
    result = test_candidate_staging.run_checks(
        E_STAR, Path(str(graph["path"])), work / "staging-regression",
    )
    return {
        "ok": bool(result["ok"]),
        "claim": result["claim"],
        "implementation": "test_candidate_staging.py (run standalone with `--e-star <path>`)",
        "cases": [
            {"name": item["name"], "ok": item["ok"], "claim": item["claim"]} for item in result["cases"]
        ],
    }


def probe_identity(rows: list[dict[str, object]]) -> dict[str, object]:
    mismatched = [
        row["candidate_id"] for row in rows
        if row["candidate_source_sha256"] != row["manifest_source_sha256"]
    ]
    return {
        "ok": not mismatched,
        "claim": "the candidate bytes E* measured are the bytes C*(T1) froze",
        "mismatched": mismatched,
        "count": len(rows),
    }


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="run C*(T1) through E* and check the frozen verdicts")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--freeze", action="store_true", help="write conformance.expected.json")
    mode.add_argument("--check", action="store_true", help="compare against the frozen table (default)")
    parser.add_argument("--suite-root", default=str(HERE / "suite"))
    parser.add_argument("--work", default=None, help="scratch root for this run")
    parser.add_argument("--report", default=str(REPORT_PATH))
    args = parser.parse_args(list(argv) if argv is not None else None)

    work = Path(args.work) if args.work else Path(tempfile.mkdtemp(prefix="maxcut-conformance-"))
    work.mkdir(parents=True, exist_ok=True)
    graph = target_graph(Path(args.suite_root))
    candidates = load_candidate_manifest()
    eval_env = {**os.environ, **DECOYS}

    rows = sweep(graph=graph, candidates=candidates, work=work, env=eval_env)

    table = {
        "schema": "a0.maxcut.conformance.expected/v1",
        "candidate_set": "C*(T1)",
        "graph_source": graph["source"],
        "graph": {"path": graph["path"], "graph_id": graph["graph_id"], "sha256": graph["sha256"]},
        "seed": SEED,
        "timeout_s": TAU_S,
        "net_isolate_rows": ["c15_error_network_attempt"],
        "rows": [
            {key: row[key] for key in
             ("candidate_id", "kind", "status", "cut_edges", "failure_kind",
              "candidate_source_sha256", "evaluator_exit_code")}
            for row in rows
        ],
    }

    probes = {
        "p1_cwd_path_independence": probe_cwd_path(graph, work),
        "p2_determinism": probe_determinism(rows, graph, work),
        "p3_failure_semantics": probe_failure_semantics(rows),
        "p4_network_independence": probe_network(graph, work),
        "p5_child_environment": probe_environment(graph, work),
        "p6_exact_aggregation": probe_exact_aggregation(work),
        "p7_candidate_staging": probe_candidate_staging(graph, work),
    }
    checks = {
        "c_identity": probe_identity(rows),
        "c_ordered_pair": probe_ordered_pair(rows),
        "c_tie_pair": probe_float_tie(rows),
        "c_legitimate_zero": probe_legitimate_zero(rows),
        "c_process_group": probe_process_group(work),
        "c_inflation_attempt": probe_inflation_attempt(rows, graph),
        "c_input_tampering_detected": probe_input_tampering_detected(rows),
    }

    drift: list[str] = []
    table_note = ""
    if args.freeze:
        EXPECTED_PATH.write_bytes(canonical_bytes(table))
        table_note = f"froze {len(rows)} rows to {EXPECTED_PATH.name}"
    else:
        if not EXPECTED_PATH.is_file():
            print(f"conformance: no frozen table at {EXPECTED_PATH}; run --freeze first", file=sys.stderr)
            return 2
        frozen = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
        if frozen["graph"]["sha256"] != graph["sha256"]:
            # The table is a statement about one graph's bytes; comparing verdicts
            # across two different graphs would be a false alarm, so say so.
            table_note = (
                f"frozen table is for {frozen['graph']['graph_id']} "
                f"({frozen['graph']['sha256'][:16]}…); this run used {graph['graph_id']} "
                f"({graph['sha256'][:16]}…) -- rows not compared"
            )
        else:
            drift = compare_rows(frozen, rows)
            table_note = "no drift" if not drift else f"{len(drift)} drifted rows"

    failed = [name for name, result in {**probes, **checks}.items() if not result.get("ok")]
    report = {
        "schema": "a0.maxcut.conformance.report/v1",
        "graph": graph,
        "seed": SEED,
        "timeout_s": TAU_S,
        "candidate_count": len(rows),
        "rows": rows,
        "probes": probes,
        "checks": checks,
        "drift": drift,
        "failed": failed,
        "table": table_note,
        "verdict": "PASS" if not failed and not drift else "FAIL",
        "work_dir": str(work),
    }
    Path(args.report).write_bytes(canonical_bytes(report))

    print(f"graph            : {graph['graph_id']} ({graph['source']}, sha256 {graph['sha256'][:16]}…)")
    print(f"candidates       : {len(rows)}")
    print(f"rows             : {table_note}")
    for name, result in {**probes, **checks}.items():
        print(f"  {'PASS' if result.get('ok') else 'FAIL'}  {name}")
    for problem in drift:
        print(f"  drift: {problem}", file=sys.stderr)
    print(f"report           : {args.report}")
    print(f"VERDICT: {report['verdict']}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
