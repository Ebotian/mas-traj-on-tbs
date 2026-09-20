"""Build `EID_INPUTS.json`: the five canonical inputs of the plumbing EID*.

`EID* = H(EvaluatorSource, DependencyLock, DataManifest, Config, MetricDefinition)`
is owned by `a0/contract/evalcontract.py` (a parallel workstream).  This tool
does not re-implement the hashing scheme: it imports that module, feeds it the
inputs for *this* evaluator (E* -- `e_star.py` + `e_star_child.py`, the frozen
`C_STAR/` candidate set, the two pinned upstream repositories), and records

  * the spec document in its exact `a0.evalcontract.spec/v1` shape,
  * the canonical material that each component hashes (records + digests),
  * the resulting `EID*` and the exact commands that produced it.

    .venv/bin/python tools/build_eid_inputs.py --write
    .venv/bin/python tools/build_eid_inputs.py --check

Later, when an artifact changes (a candidate edited, the evaluator edited, an
upstream pin moved), the recomputation yields a new `EID*`, which is the intended
behaviour of the protocol (`plan:509`).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
A0 = ROOT.parents[1]
CONTRACT_DIR = A0 / "contract"
CONTRACT_MODULE = CONTRACT_DIR / "evalcontract.py"
SPEC_PATH = ROOT / "plumbing.contract.proposed.json"
EID_PATH = ROOT / "plumbing.EID.proposed.json"
INPUTS_PATH = ROOT / "EID_INPUTS.json"
PYTHON = ROOT / ".venv" / "bin" / "python"

UPSTREAM_REFERENCE_FILES = [
    "tasks/circle-packing/upstream/loreley/examples/circle_packing_env/evaluate.py",
    "tasks/circle-packing/upstream/loreley/examples/circle_packing_env/local_eval.py",
    "tasks/circle-packing/upstream/loreley/examples/circle_packing_env/README.md",
    "tasks/circle-packing/upstream/loreley/examples/evol_circle_packing.py",
    "tasks/circle-packing/upstream/circle-packing/README.md",
    "tasks/circle-packing/upstream/circle-packing/loreley.program.md",
    "tasks/circle-packing/upstream/circle-packing/solution.py",
    "tasks/circle-packing/upstream/circle-packing/pyproject.toml",
    "tasks/circle-packing/upstream/circle-packing/scripts/local_eval.py",
]

UPSTREAM_PINS = [
    {
        "upstream_repo": "github.com/NeapolitanIcecream/loreley",
        "commit": "4c3759208e6b908f90716488ac3eec3dceaaf397",
        "pinned_at": "a0/tasks/circle-packing/upstream/loreley",
        "role": "provides the plumbing task definition and the authoritative evaluator plugin",
    },
    {
        "upstream_repo": "github.com/NeapolitanIcecream/circle-packing",
        "commit": "b91c0906c9f676eb661990d881144909d99f2d72",
        "pinned_at": "a0/tasks/circle-packing/upstream/circle-packing",
        "role": "problem statement, objective, baseline solution.py",
    },
]


def load_contract_module():
    # Never leave bytecode behind in another workstream's directory.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("a0_contract_evalcontract", CONTRACT_MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def candidate_set_files() -> list[str]:
    """The machine-readable candidate set: solutions, per-candidate records, manifest.

    Prose (README.md) is deliberately excluded so that editing documentation does
    not move EID*, while editing a candidate or its declaration does.
    """
    out = []
    for path in sorted((ROOT / "C_STAR").rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.name == "README.md":
            continue
        out.append(str(path.relative_to(A0)))
    return out


def build_spec() -> dict[str, Any]:
    return {
        "schema": "a0.evalcontract.spec/v1",
        "task": "circle-packing-plumbing",
        "base": "../../",
        "note": (
            "EID* inputs for the plumbing task, as produced by the circle-packing "
            "workstream. EvaluatorSource is the frozen evaluator itself (e_star.py + "
            "e_star_child.py); DataManifest carries the frozen candidate set C* and the "
            "two pinned upstream repositories."
        ),
        "components": {
            "EvaluatorSource": {
                "root": "tasks/circle-packing",
                "include": ["e_star.py", "e_star_child.py"],
                "exclude": ["**/*.tmp"],
            },
            "DependencyLock": {
                "files": [
                    {"path": "tasks/circle-packing/requirements.lock", "kind": "raw"}
                ],
                "entries": [
                    {
                        "python": "3.12.11",
                        "implementation": "CPython",
                        "third_party_packages": [],
                        "note": "E* and every candidate of C* import the standard library only",
                    }
                ],
            },
            "DataManifest": {
                "files": candidate_set_files()
                + UPSTREAM_REFERENCE_FILES
                + ["tasks/circle-packing/tools/good_packing_26.json"],
                "entries": UPSTREAM_PINS
                + [
                    {
                        "candidate_set_id": "C*",
                        "produced_by": "a0/tasks/circle-packing/tools/build_c_star.py",
                        "status": "published",
                        "manifest": "tasks/circle-packing/C_STAR/manifest.json",
                    },
                    {
                        "reference_table": "tasks/circle-packing/E_STAR.json",
                        "note": "derived artifact (E* applied to C*); deliberately not hashed into EID*, hash it separately for provenance",
                    },
                ],
            },
            "Config": {
                "value": {
                    "task": "circle-packing-plumbing",
                    "evaluator": {
                        "cli": "e_star.py evaluate --candidate <path> --seed <S> [--fidelity full|fast] [--fraction F] --out <json>",
                        "exit_codes": {"ok": 0, "invalid": 2, "error": 3},
                        "outcome_is_multi_field": True,
                        "scalarization_owner": "F_r",
                    },
                    "theta_e_canonical": {
                        "seed": 1337,
                        "fidelity": "full",
                        "fraction": 1.0,
                        "n": 26,
                        "runs": 5,
                        "runtime_budget_ms": 250.0,
                        "timeout_s": 120.0,
                    },
                    "theta_e_fast_example": {
                        "seed": 1337,
                        "fidelity": "fast",
                        "fraction": 0.15,
                        "n": 26,
                        "runs": 5,
                        "runtime_budget_ms": 250.0,
                        "timeout_s": 120.0,
                    },
                    "theta_e_semantics": {
                        "seed": "draws the deterministic audit subsample; inert at fidelity=full",
                        "fidelity": "full audits every item; fast audits a seeded decimation",
                        "fraction": "fast-tier audit fraction in (0, 1]; forced to 1.0 at fidelity=full",
                        "defaults_source": "KAPSO: evaluation_maintainer.subsample_seed=1337, fidelity.py:247 eval_fast_fraction=0.15",
                    },
                    "evaluator_constants": {
                        "epsilon": 1e-09,
                        "runtime_runs_default": 5,
                        "runtime_budget_ms_default": 250.0,
                        "unit_square": [0.0, 1.0],
                    },
                    "conformance": {"epsilon": {"kind": "abs", "value": 1e-09, "unit": "sum_radii"}},
                    "environment_policy": {
                        "child_env_specified_by_evaluator": True,
                        "path": "",
                        "pythonpath": "",
                        "pythonhashseed": "0",
                        "pythonnousersite": "1",
                        "pythondontwritebytecode": "1",
                        "private_home_tmpdir_cwd": True,
                        "allow_network": False,
                    },
                    "cwd_independence": {
                        "required": True,
                        "note": "candidate source is executed as a private copy below E*'s state root; scores never depend on caller cwd or PATH",
                    },
                    "revert_safety": {
                        "required": True,
                        "note": "E* writes only below --state-dir and --out; never inside a candidate worktree",
                    },
                }
            },
            "MetricDefinition": {
                "value": {
                    "name": "sum_radii",
                    "direction": "maximize",
                    "unit": "radius_sum (length in the unit square, n=26)",
                    "definition": (
                        "sum of the radii of the circles returned by pack_circles(n=26), "
                        "accumulated in returned order with CPython's sum()"
                    ),
                    "outcome_fields": [
                        "sum_radii",
                        "packing_density",
                        "num_circles",
                        "overlap_count",
                        "min_gap",
                        "min_boundary_margin",
                    ],
                    "validity_gates": [
                        "count_equals_n",
                        "radius_positive_check",
                        "bounds_check",
                        "overlap_check",
                        "determinism_check",
                        "runtime_budget_check",
                    ],
                    "failure_semantics": (
                        "when status != ok the objective is null, never 0.0; the adapter "
                        "must not coerce a missing objective into a score"
                    ),
                    "scalarization_owner": "F_r",
                    "implementation": [
                        "tasks/circle-packing/e_star.py::structure_fields",
                        "upstream/circle-packing/loreley.program.md:8-10",
                        "upstream/circle-packing/README.md:19-27",
                        "upstream/loreley/examples/circle_packing_env/evaluate.py:133-145",
                    ],
                    "known_upstream_discrepancy": (
                        "evaluate.py (the plugin Loreley's worker actually loads) and "
                        "scripts/local_eval.py differ by one ULP in sum_radii because the "
                        "latter accumulates in a loop while the former uses sum(); E* "
                        "mirrors evaluate.py, verified bit-for-bit by tools/crosscheck_upstream.py"
                    ),
                }
            },
        },
    }


def run_contract_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [str(PYTHON), str(CONTRACT_MODULE), *args],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def build() -> dict[str, Any]:
    spec = build_spec()
    SPEC_PATH.write_text(json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    compute = run_contract_cli(
        "compute", "--spec", str(SPEC_PATH), "--out", str(EID_PATH)
    )
    if compute.returncode != 0:
        print(compute.stdout)
        print(compute.stderr, file=sys.stderr)
        raise SystemExit(f"evalcontract.py compute failed with rc={compute.returncode}")
    document = json.loads(EID_PATH.read_text(encoding="utf-8"))

    verify = run_contract_cli(
        "verify", "--eid-file", str(EID_PATH), "--spec", str(SPEC_PATH)
    )

    inputs = {
        "schema": "a0.tasks.circle-packing.eid_inputs/v1",
        "task": "circle-packing-plumbing",
        "hash_scheme_owner": "a0/contract/evalcontract.py",
        "note": (
            "The five canonical inputs of EID* for this task, in the exact shape "
            "a0/contract/evalcontract.py consumes. `evalcontract_spec` is a drop-in "
            "replacement for a0/contract/plumbing.contract.json; `components` below is "
            "the canonical material that spec hashes, as produced by that module."
        ),
        "evalcontract_spec": spec,
        "proposed_spec_path": "a0/tasks/circle-packing/plumbing.contract.proposed.json",
        "eid_star": document["eid_star"],
        "eid_star_derivation": document["eid_star_derivation"],
        "components": {
            name: {
                "kind": document["components"][name]["kind"],
                "digest": document["components"][name]["digest"],
                "canonical_material": {
                    key: value
                    for key, value in document["components"][name].items()
                    if key in {"root", "include", "records", "value", "metric_name", "direction"}
                },
            }
            for name in ("EvaluatorSource", "DependencyLock", "DataManifest", "Config", "MetricDefinition")
        },
        "upstream_pins": UPSTREAM_PINS,
        "commands": {
            "compute": (
                ".venv/bin/python /home/ebt/rsi-dev/a0/contract/evalcontract.py compute "
                "--spec plumbing.contract.proposed.json --out plumbing.EID.proposed.json"
            ),
            "verify": (
                ".venv/bin/python /home/ebt/rsi-dev/a0/contract/evalcontract.py verify "
                "--eid-file plumbing.EID.proposed.json --spec plumbing.contract.proposed.json"
            ),
            "observed_compute_stdout": compute.stdout.strip(),
            "observed_verify": {
                "returncode": verify.returncode,
                "stdout": verify.stdout.strip(),
                "stderr": verify.stderr.strip(),
            },
            "observed_recompute": (
                ".venv/bin/python /home/ebt/rsi-dev/a0/contract/evalcontract.py recompute "
                "--eid-file plumbing.EID.proposed.json"
            ),
        },
        "recommendations_for_contract_owner": [
            "a0/contract/plumbing.contract.json currently points EvaluatorSource at "
            "upstream/circle-packing/scripts (local_eval.py); the frozen evaluator for this "
            "study is e_star.py + e_star_child.py, which is what `evalcontract_spec` declares.",
            "That spec's Config says seed is inapplicable and fraction is fixed at 1.0; "
            "protocol plan:513-523 makes the seed an evaluator input (theta_E = seed, fidelity, "
            "fraction) and requires the triple to be recorded per attempt, so the seed is "
            "applicable and defaults to 1337.",
            "adapter_contract.md §4 parses `target_metrics[sum_radii]` from local_eval.py's "
            "stdout. E*'s contract is `--out <json>` with objective.value plus status, exit "
            "code 0/2/3, and objective=null on failure. local_eval.py cannot express "
            "invalid/error or the audit fields, and it is the file that differs from the "
            "plugin by one ULP.",
            "adapter_contract.md §3 points --candidate-set at a `candidates/` directory; this "
            "workstream's directory is C_STAR/ (C_STAR/manifest.json now follows "
            "a0.candidateset/v1), so the flag value is "
            "a0/tasks/circle-packing/C_STAR/manifest.json.",
            "DataManifest's {\"candidate_set\": \"C*\", \"status\": \"pending\"} placeholder can "
            "move to published: C_STAR/ exists and every file is hashed in this document.",
        ],
    }
    return inputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    payload = build()
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not INPUTS_PATH.is_file():
            print("EID_INPUTS.json is missing")
            return 1
        if INPUTS_PATH.read_text(encoding="utf-8") == text:
            print("EID_INPUTS.json is stable: rerun produced byte-identical output")
            return 0
        print("EID_INPUTS.json DIFFERS from a fresh rebuild")
        return 1
    INPUTS_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {INPUTS_PATH} ({len(text.encode('utf-8'))} bytes)")
    print(f"EID* = {payload['eid_star']}")
    observed = payload["commands"]["observed_verify"]
    print(f"verify: rc={observed['returncode']} {observed['stdout']} {observed['stderr']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
