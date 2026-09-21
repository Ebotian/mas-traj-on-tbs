#!/usr/bin/env python3
"""Execution/load attestation for a real E* invocation.

Wraps the frozen CLI (`a0/tasks/circle-packing/e_star.py evaluate ...`) without
touching `a0/tasks/**`, and emits a canonical JSON attestation that splits the
declared evaluator identity from the identity of the thing that actually ran:

    EID_semantic  = the frozen five-component EID*, recomputed at run time from
                    the inputs present on disk
    EID_execution = H(EID_semantic, dependencies, runtime, loaded artifacts,
                      environment, candidate actually evaluated)

Three processes are launched, all with the interpreter that runs this script:

  1. the authoritative invocation, byte-for-byte the command the conformance
     runner and the adapters use (`python e_star.py evaluate ...`);
  2. the capture invocation, the same argv through `_bootstrap.py`, so that the
     interpreter's own `exec`/`import`/`open`/`subprocess` events are recorded;
  3. a child probe, importing `e_star_child.py` under the exact environment E*
     hands its child, so the child side of the evaluator is attested too.

If (1) and (2) do not produce the same canonical Outcome, the attestation says
so: the capture is then not representative of the invocation, and the verifier
fails the realization check rather than papering over it.

Usage:

    python attest.py --candidate a0/tasks/circle-packing/C_STAR/c01_good_hex \\
        [--seed 1337] [--fidelity full] [--fraction 1.0] [--n 26] [--runs 5] \\
        [--runtime-budget-ms 250.0] [--timeout-s 120.0] \\
        [--evaluator a0/tasks/circle-packing/e_star.py] [--adapter NAME] \\
        [--out-dir a0/attestation/out] [--attestation-out PATH]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import attest_lib as lib  # noqa: E402

REPO_ROOT = HERE.parent.parent
BOOTSTRAP = HERE / "_bootstrap.py"
DEFAULT_EVALUATOR = Path("a0/tasks/circle-packing/e_star.py")
DEFAULT_EID_INPUTS = Path("a0/tasks/circle-packing/EID_INPUTS.json")
DEFAULT_SPEC = Path("a0/tasks/circle-packing/plumbing.contract.proposed.json")
DEFAULT_REFERENCE_TABLE = Path("a0/tasks/circle-packing/E_STAR.json")

SYSTEM_PATH_PREFIXES = ("/dev/", "/proc/", "/sys/", "/etc/", "/usr/lib/", "/usr/share/", "/usr/local/lib/")


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #

def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_command(argv, *, cwd=None, env=None, timeout=600) -> dict:
    started = time.time()
    completed = subprocess.run(
        [str(item) for item in argv],
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return {
        "argv": [str(item) for item in argv],
        "returncode": completed.returncode,
        "stdout": completed.stdout.decode("utf-8", "replace"),
        "stderr": completed.stderr.decode("utf-8", "replace"),
        "wall_seconds": round(time.time() - started, 6),
    }


def parse_state_dir(stderr: str):
    for line in reversed(stderr.splitlines()):
        if "state_dir=" in line:
            tail = line.split("state_dir=", 1)[1]
            path = tail.split(" ", 1)[0].strip()
            if path:
                return path
    return None


PID_DIR = re.compile(r"/pid\d+")


def normalize_child_argv(argv):
    """The child command E* spawns, with the pid-bearing run directory masked.

    The pid is per-process by construction, so leaving it in the identity
    payload would make the execution identity a run id.
    """
    if not argv:
        return None
    return [PID_DIR.sub("/pid<pid>", str(item)) for item in argv]


def installed_distributions(prefixes) -> list[dict]:
    """Third-party distributions present in the attested interpreter's prefixes.

    Read as files (`*.dist-info`), never imported, so this reflects the
    environment the evaluator had rather than this tool's own.
    """
    found = {}
    for prefix in prefixes:
        if not prefix:
            continue
        base = Path(prefix)
        for candidate in (base / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages",
                          base / "lib" / "site-packages", base / "Lib" / "site-packages"):
            if not candidate.is_dir():
                continue
            for entry in sorted(candidate.iterdir()):
                if not (entry.name.endswith(".dist-info") or entry.name.endswith(".egg-info")):
                    continue
                metadata = entry / "METADATA"
                found[entry.name] = {
                    "dist_info": entry.name,
                    "site_packages": lib.rel_to(candidate, REPO_ROOT),
                    "sha256": lib.sha256_file(metadata)["sha256"] if metadata.is_file() else None,
                }
    return [found[key] for key in sorted(found)]


def import_evalcontract(path: Path):
    spec = importlib.util.spec_from_file_location("a0_attest_evalcontract", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# loaded-artifact classification
# --------------------------------------------------------------------------- #

def runtime_prefixes(runtime: dict) -> list[str]:
    prefixes = [runtime.get("sys_base_prefix"), runtime.get("sys_prefix"),
                runtime.get("sys_base_exec_prefix"), runtime.get("sys_exec_prefix")]
    return [p for p in prefixes if p]


def classify_path(path: str, *, runtime: dict, roots: dict) -> str:
    resolved = os.path.realpath(path)
    for label, prefix in (("state_dir", roots.get("state_dir")),
                          ("candidate_set", roots.get("candidate_set")),
                          ("evaluator_root", roots.get("evaluator_root")),
                          ("repo", roots.get("repo")),
                          ):
        if prefix and lib.is_under(resolved, prefix):
            return label
    for prefix in runtime_prefixes(runtime):
        if lib.is_under(resolved, prefix):
            return "runtime"
    if resolved.startswith(SYSTEM_PATH_PREFIXES) or resolved.startswith("/tmp/"):
        return "system_or_tmp"
    return "other"


def build_artifact_records(capture: dict, *, declared_files: dict,
                           entry_path: Path) -> list[dict]:
    """One record per loaded module that is, or stands in for, a declared
    evaluator source file.

    Membership is decided by the *declared* file set (`e_star.py`,
    `e_star_child.py`), never by a directory prefix: the evaluator's own
    directory also contains `.venv/`, and a prefix rule would both hide a
    shadowing module dropped next to `e_star.py` and flood this table with
    site-packages entries.
    """
    exec_index: dict[tuple, str] = {}
    for event in capture["exec_events"]:
        key = (os.path.realpath(event["co_filename"]), event["co_name"])
        exec_index[key] = event["code_sha256"]

    by_basename = {}
    for rel, digest in declared_files.items():
        by_basename.setdefault(Path(rel).name, (rel, digest))

    same_interpreter = os.path.realpath(sys.executable) == capture["runtime"]["executable_realpath"]
    records = []
    for module in capture["modules"]:
        origin = module.get("origin")
        if not origin or origin in ("built-in", "frozen"):
            continue
        resolved = os.path.realpath(origin)
        is_entry = os.path.realpath(str(entry_path)) == resolved
        declared_rel, declared_sha = by_basename.get(Path(resolved).name, (None, None))
        if not (is_entry or declared_rel is not None):
            continue
        loaded_code = exec_index.get((resolved, "<module>"))
        fresh = lib.fresh_compile_digest(resolved) if same_interpreter else None
        records.append(
            {
                "name": module["name"],
                "origin": lib.rel_to(resolved, REPO_ROOT),
                "origin_absolute": resolved,
                "origin_kind": module["origin_kind"],
                "loader": module["loader"],
                "file_sha256": module.get("sha256"),
                "file_size": module.get("size"),
                "loaded_code_sha256": loaded_code,
                "fresh_compile_sha256": fresh,
                "bytecode_matches_source": (None if (loaded_code is None or fresh is None)
                                            else loaded_code == fresh),
                "pyc_path": lib.rel_to(module["cached"], REPO_ROOT) if module.get("cached") else None,
                "pyc_sha256": module.get("cached_sha256"),
                "loaded_from_cache_path": bool(module.get("cached")),
                "declared_path": declared_rel,
                "declared_sha256": declared_sha,
                "declared_match": (None if declared_sha is None else declared_sha == module.get("sha256")),
                "is_entry": is_entry,
                "entry_is_the_declared_entry": is_entry and declared_rel is not None,
                "loaded_by_harness_before_hook": bool(module.get("pre_existing")),
            }
        )
    records.sort(key=lambda item: item["name"])
    return records


def build_foreign_modules(capture: dict, *, runtime: dict, declared_paths: set,
                          harness_dir) -> dict:
    """Modules loaded from outside the runtime's own trees and the declared sources.

    This is the field that answers "the runtime imported a different module": a
    module bound to a name the evaluator uses, whose bytes come from somewhere
    the study never declared.  There is deliberately no exemption for the
    evaluator's own directory -- a module dropped next to `e_star.py` is found
    first on `sys.path` and must show up here.  Only the capture harness's own
    files are exempt, by exact path, and they are named rather than dropped.
    """
    harness_paths = {os.path.realpath(item) for item in (harness_dir or [])}
    foreign = []
    harness_modules = []
    for module in capture["modules"]:
        origin = module.get("origin")
        if not origin or origin in ("built-in", "frozen"):
            continue
        resolved = os.path.realpath(origin)
        if resolved in harness_paths:
            harness_modules.append({"name": module["name"], "origin": resolved})
            continue
        if any(lib.is_under(resolved, prefix) for prefix in runtime_prefixes(runtime)):
            continue
        if resolved in declared_paths:
            continue
        foreign.append(
            {
                "name": module["name"],
                "origin": resolved,
                "origin_kind": module["origin_kind"],
                "sha256": module.get("sha256"),
                "size": module.get("size"),
                "loaded_by_harness_before_hook": bool(module.get("pre_existing")),
            }
        )
    foreign.sort(key=lambda item: item["name"])
    harness_modules.sort(key=lambda item: item["name"])
    return {"foreign_modules": foreign, "harness_modules": harness_modules}


def build_shadowing_hazards(capture: dict, *, runtime: dict) -> list[dict]:
    """Hazards implied by `sys.path` alone, independent of import order.

    Any entry ahead of the runtime's own stdlib that holds a top-level module or
    package whose name collides with a stdlib top-level name can silently
    replace that name.  Reported whether or not this run happened to import it.
    """
    stdlib_dir = Path(runtime["sys_base_prefix"]) / "lib" / f"python{runtime['version'].rsplit('.', 1)[0]}"
    if not stdlib_dir.is_dir():
        return []
    stdlib_names = set()
    for entry in stdlib_dir.iterdir():
        if entry.name.startswith("_") or entry.name in ("site-packages", "lib-dynload", "config"):
            continue
        if entry.is_dir() or entry.suffix in (".py", ".so"):
            stdlib_names.add(entry.name.split(".")[0])
    hazards = []
    for position, entry in enumerate(capture["runtime"]["sys_path"]):
        if not entry:
            base = Path(capture["cwd"])
        else:
            base = Path(entry)
        try:
            inside_runtime = lib.is_under(str(base), runtime["sys_prefix"]) or lib.is_under(
                str(base), runtime["sys_base_prefix"]
            )
        except OSError:
            inside_runtime = False
        if inside_runtime or not base.is_dir():
            continue
        try:
            children = sorted(base.iterdir())
        except OSError:
            continue
        for child in children:
            stem = child.name.split(".")[0]
            if stem not in stdlib_names or child.name.startswith("_"):
                continue
            hazards.append(
                {"sys_path_index": position, "sys_path_entry": str(base), "shadows": stem,
                 "path": str(child)}
            )
    hazards.sort(key=lambda item: (item["sys_path_index"], item["shadows"]))
    return hazards


def summarize_open_events(capture: dict, *, runtime: dict, roots: dict) -> dict:
    buckets: dict[str, int] = {}
    outside = []
    for event in capture["open_events"]:
        category = classify_path(event["path"], runtime=runtime, roots=roots)
        buckets[category] = buckets.get(category, 0) + 1
        if category == "other":
            outside.append(event["path"])
    return {"by_category": dict(sorted(buckets.items())), "outside_all_known_roots": sorted(set(outside))}


# --------------------------------------------------------------------------- #
# dependent environment
# --------------------------------------------------------------------------- #

def build_dependencies(capture: dict, *, repo_root: Path, eid_inputs: dict) -> dict:
    runtime = capture["runtime"]
    pyvenv = Path(runtime["sys_prefix"]) / "pyvenv.cfg"
    pyvenv_record = None
    content = {}
    if pyvenv.is_file():
        text = pyvenv.read_text(encoding="utf-8")
        pyvenv_record = {"path": lib.rel_to(pyvenv, repo_root), **lib.sha256_file(pyvenv)}
        for line in text.splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                content[key.strip()] = value.strip()
    distributions = installed_distributions([runtime["sys_prefix"], runtime["sys_base_prefix"]])
    declared_lock = None
    for record in (
        eid_inputs.get("components", {}).get("DependencyLock", {}).get("canonical_material", {}).get("records", [])
    ):
        if isinstance(record, dict) and record.get("kind") == "raw" and record.get("lock"):
            declared_lock = {
                "path": record["lock"],
                "declared_sha256": record.get("sha256"),
                "declared_size": record.get("size"),
            }
    if declared_lock:
        live_path = repo_root / "a0" / declared_lock["path"]
        if live_path.is_file():
            declared_lock["live_sha256"] = lib.sha256_file(live_path)["sha256"]
            declared_lock["matches"] = declared_lock["declared_sha256"] == declared_lock["live_sha256"]

    native = []
    for module in capture["modules"]:
        if module.get("origin_kind") != "extension" or not module.get("origin"):
            continue
        native.append({"module": module["name"], "path": os.path.realpath(module["origin"]),
                       "sha256": module.get("sha256"), "size": module.get("size")})
    native.sort(key=lambda item: item["module"])

    environment_material = {
        "interpreter_sha256": runtime["executable_sha256"],
        "interpreter_version": runtime["version"],
        "bytecode_magic_hex": runtime["bytecode_magic_hex"],
        "pyvenv_cfg": pyvenv_record,
        "pyvenv_cfg_content": content,
        "native_dependency_digest": lib.domain_digest(
            f"{lib.DOMAIN}/native_dependencies", lib.canonical_json(native)
        ),
        "container_image": None,
        "host_only_reason": (
            "E* is invoked on the host by this wrapper; no container image is involved in the "
            "evaluated process, so no image digest exists to record. A containerized invocation "
            "must pass the image id explicitly (see FIELDS.md, dependencies.container_image)."
        ),
    }
    return {
        "kind": "host_venv",
        "container_image": None,
        "interpreter_sha256": runtime["executable_sha256"],
        "interpreter_size": runtime["executable_size"],
        "pyvenv_cfg": pyvenv_record,
        "pyvenv_cfg_content": content,
        "distributions": distributions,
        "declared_lock": declared_lock,
        "native_dependencies": native,
        "native_dependency_digest": environment_material["native_dependency_digest"],
        "environment_digest": lib.domain_digest(
            f"{lib.DOMAIN}/environment", lib.canonical_json(environment_material)
        ),
    }


def build_environment(capture: dict, child_capture: dict | None, config_value: dict) -> dict:
    policy = config_value.get("environment_policy", {})
    captured = {name: entry["value"] if entry["set"] else None
                for name, entry in capture["environment"].items()}
    child_env = None
    if capture["popen_events"]:
        child_env = capture["popen_events"][0].get("env")
    checks = []
    if child_env is not None:
        expectations = {
            "PATH": policy.get("path"),
            "PYTHONPATH": policy.get("pythonpath"),
            "PYTHONHASHSEED": policy.get("pythonhashseed"),
            "PYTHONDONTWRITEBYTECODE": policy.get("pythondontwritebytecode"),
            "PYTHONNOUSERSITE": policy.get("pythonnousersite"),
        }
        for name, expected in expectations.items():
            actual = child_env.get(name)
            checks.append(
                {"name": f"child_environment.{name}", "expected": expected, "actual": actual,
                 "passed": actual == expected}
            )
    specified = [name for name, value in captured.items() if value not in (None, "")]
    return {
        "allowlist": sorted(capture["environment"].keys()),
        "values": captured,
        "behaviour_affecting_set": sorted(
            name for name in specified if name.startswith("PYTHON") or name in ("VIRTUAL_ENV", "PATH", "HOME", "TMPDIR")
        ),
        "unspecified_by_contract": (
            "E*'s own process environment is not specified by the frozen Config (only the child "
            "environment is), so every value here is recorded for comparison rather than checked "
            "against a declared value."
        ),
        "child_environment": child_env,
        "child_policy_checks": checks,
        "child_policy_ok": all(item["passed"] for item in checks) if checks else None,
        "child_probe": {
            "module": child_capture["module_path"] if child_capture else None,
            "applied_environment_override": child_capture.get("environment_override_applied")
            if child_capture
            else None,
        },
    }


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="attest.py", description=__doc__.splitlines()[0])
    parser.add_argument("--candidate", required=True, help="candidate directory or solution.py")
    parser.add_argument("--evaluator", default=str(DEFAULT_EVALUATOR), help="frozen E* entry file")
    parser.add_argument("--adapter", default=None, help="adapter id this run is attributed to")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--eid-inputs", default=str(DEFAULT_EID_INPUTS))
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument("--reference-table", default=str(DEFAULT_REFERENCE_TABLE))
    parser.add_argument("--out-dir", default=str(HERE / "out"))
    parser.add_argument("--state-root", default=None,
                        help="E* state root; defaults to <out-dir>/e-star-state")
    parser.add_argument("--attestation-out", default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--fidelity", choices=("full", "fast"), default=None)
    parser.add_argument("--fraction", type=float, default=None)
    parser.add_argument("--n", type=int, default=None)
    parser.add_argument("--runs", type=int, default=None)
    parser.add_argument("--runtime-budget-ms", type=float, default=None)
    parser.add_argument("--timeout-s", type=float, default=None)
    parser.add_argument("--keep-work", action="store_true", help="do not delete the scratch dir")
    parser.add_argument("--env", action="append", default=None, metavar="KEY=VALUE",
                        help="extra environment for the evaluator subprocesses only (repeatable); "
                             "this tool's own process is never affected")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    evaluator = (repo_root / args.evaluator).resolve() if not os.path.isabs(args.evaluator) else Path(args.evaluator)
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    state_root = Path(args.state_root).resolve() if args.state_root else out_dir / "e-star-state"

    reference = read_json(repo_root / args.reference_table)
    eid_inputs = read_json(repo_root / args.eid_inputs)
    spec_path = (repo_root / args.spec).resolve()
    theta = dict(reference["canonical_theta_e"])
    for key, value in (("seed", args.seed), ("fidelity", args.fidelity), ("fraction", args.fraction),
                       ("n", args.n), ("runs", args.runs), ("runtime_budget_ms", args.runtime_budget_ms),
                       ("timeout_s", args.timeout_s)):
        if value is not None:
            theta[key] = value

    candidate = Path(args.candidate)
    candidate = (repo_root / candidate) if not candidate.is_absolute() else candidate
    candidate = candidate.resolve()
    if candidate.is_dir():
        solution = candidate / "solution.py"
    else:
        solution, candidate = candidate, candidate.parent
    if not solution.is_file():
        raise lib.AttestError(f"candidate solution not found: {solution}")

    candidate_set = (repo_root / "a0/tasks/circle-packing/C_STAR").resolve()
    candidate_id = candidate.name

    evaluator_root = evaluator.parent
    roots = {
        "repo": repo_root,
        "evaluator_root": str(evaluator_root),
        "candidate_set": str(candidate_set),
        "state_dir": str(state_root),
    }

    scratch = Path(tempfile.mkdtemp(prefix="a0-attest-"))
    authority_out = scratch / "authority.outcome.json"
    capture_out = scratch / "capture.outcome.json"
    capture_json = scratch / "capture.json"
    probe_json = scratch / "child_probe.json"
    env_file = scratch / "child.env"

    evaluator_argv = [
        "evaluate",
        "--candidate", str(candidate),
        "--seed", str(theta["seed"]),
        "--fidelity", str(theta["fidelity"]),
        "--fraction", repr(float(theta["fraction"])),
        "--n", str(theta["n"]),
        "--runs", str(theta["runs"]),
        "--runtime-budget-ms", repr(float(theta["runtime_budget_ms"])),
        "--timeout-s", repr(float(theta["timeout_s"])),
        "--out", str(authority_out),
        "--state-dir", str(state_root),
    ]

    python = sys.executable
    env_overrides = {}
    for item in args.env or []:
        key, _, value = item.partition("=")
        env_overrides[key] = value
    subject_env = dict(os.environ)
    subject_env.update(env_overrides)
    recorded_overrides = {
        key: (value if not any(token in value for token in ("sk-", "ghp_", "AIza", "Bearer "))
              else "<redacted:secret-shaped>")
        for key, value in sorted(env_overrides.items())
    }

    authority = run_command([python, str(evaluator), *evaluator_argv], cwd=repo_root, env=subject_env)
    authority_outcome = read_json(authority_out) if authority_out.is_file() else None

    capture_argv = [
        "evaluate",
        "--candidate", str(candidate),
        "--seed", str(theta["seed"]),
        "--fidelity", str(theta["fidelity"]),
        "--fraction", repr(float(theta["fraction"])),
        "--n", str(theta["n"]),
        "--runs", str(theta["runs"]),
        "--runtime-budget-ms", repr(float(theta["runtime_budget_ms"])),
        "--timeout-s", repr(float(theta["timeout_s"])),
        "--out", str(capture_out),
        "--state-dir", str(state_root),
    ]
    capture_run = run_command(
        [python, str(BOOTSTRAP), "run", "--evaluator", str(evaluator), "--capture", str(capture_json),
         "--", *capture_argv],
        cwd=repo_root,
        env=subject_env,
    )
    capture = read_json(capture_json) if capture_json.is_file() else None
    if capture is None:
        raise lib.AttestError(
            f"capture harness produced no document (rc={capture_run['returncode']}): "
            f"{capture_run['stderr'][-500:]}"
        )
    capture_outcome = read_json(capture_out) if capture_out.is_file() else None

    child_probe = None
    if capture["popen_events"] and capture["popen_events"][0].get("env") is not None:
        child = capture["popen_events"][0]
        env_file.write_text(
            "\n".join(f"{key}={value}" for key, value in sorted(child["env"].items())),
            encoding="utf-8",
        )
        probe = run_command(
            [python, str(BOOTSTRAP), "probe-import", "--module-path", str(evaluator_root / "e_star_child.py"),
             "--env-file", str(env_file), "--cwd", str(child.get("cwd") or scratch),
             "--capture", str(probe_json)],
            cwd=repo_root,
            env=subject_env,
        )
        if probe_json.is_file():
            child_probe = read_json(probe_json)

    # -- semantic identity, recomputed from the inputs actually on disk ------
    evalcontract = import_evalcontract(repo_root / "a0/contract/evalcontract.py")
    spec = read_json(spec_path)
    live_contract = evalcontract.build_contract(spec, spec_path, None)
    live_components = {name: live_contract["components"][name]["digest"] for name in lib.COMPONENTS}
    live_eid = live_contract["eid_star"]
    declared_components = {
        name: eid_inputs["components"][name]["digest"] for name in lib.COMPONENTS
    }
    declared_eid = eid_inputs["eid_star"]
    frozen_eid = lib.FROZEN_EID_STAR

    # -- declared evaluator source files ------------------------------------
    src_component = eid_inputs["components"]["EvaluatorSource"]["canonical_material"]
    declared_files = {}
    for record in src_component["records"]:
        rel = f"{src_component['root']}/{record['path']}"
        declared_files[lib.rel_to(repo_root / "a0" / rel, repo_root)] = record["sha256"]
    declared_evaluator_entry = lib.rel_to(evaluator, repo_root)

    # -- candidate ---------------------------------------------------------
    declared_data = {}
    declared_candidate = None
    for record in eid_inputs["components"]["DataManifest"]["canonical_material"]["records"]:
        data = record.get("data")
        if not data:
            continue
        rel = lib.rel_to(repo_root / "a0" / data, repo_root)
        declared_data[rel] = record["sha256"]
        if rel == lib.rel_to(solution, repo_root):
            declared_candidate = {"source": "EID_INPUTS.DataManifest", "sha256": record["sha256"],
                                  "size": record["size"]}
    disk_hash = lib.sha256_file(solution)
    executed_copy = None
    observed_state_dir = parse_state_dir(authority["stderr"])
    if observed_state_dir:
        candidate_copy = Path(observed_state_dir) / "candidate" / "solution.py"
        if candidate_copy.is_file():
            executed_copy = candidate_copy
    executed_hash = lib.sha256_file(executed_copy) if executed_copy else None
    outcome_source_sha = ((authority_outcome or {}).get("candidate") or {}).get("source_sha256")

    candidate_block = {
        "id": candidate_id,
        "is_member_of_C_STAR": lib.is_under(str(solution), str(candidate_set)),
        "solution_path": lib.rel_to(solution, repo_root),
        "declared": declared_candidate,
        "disk_sha256": disk_hash["sha256"],
        "disk_size": disk_hash["size"],
        "executed_copy_sha256": executed_hash["sha256"] if executed_hash else None,
        "executed_copy_path": lib.rel_to(executed_copy, repo_root) if executed_copy else None,
        "outcome_source_sha256": outcome_source_sha,
        "checks": {
            "declared_equals_disk": None if not declared_candidate
            else declared_candidate["sha256"] == disk_hash["sha256"],
            "declared_equals_outcome": None if (not declared_candidate or not outcome_source_sha)
            else declared_candidate["sha256"] == outcome_source_sha,
            "disk_equals_executed_copy": None if not executed_hash
            else disk_hash["sha256"] == executed_hash["sha256"],
        },
    }

    # every file of the candidate set, hashed as it really is, and flagged by
    # whether the evaluator actually opened it
    opened_paths = {os.path.realpath(event["path"]) for event in capture["open_events"]}
    data_files = []
    for entry in sorted(candidate.iterdir()):
        if not entry.is_file():
            continue
        rel = lib.rel_to(entry, repo_root)
        digest = lib.sha256_file(entry)
        declared_sha = declared_data.get(rel)
        data_files.append(
            {
                "path": rel,
                "kind": "file",
                "sha256": digest["sha256"],
                "size": digest["size"],
                "declared_sha256": declared_sha,
                "declared_match": None if declared_sha is None else declared_sha == digest["sha256"],
                "opened_by_evaluator": os.path.realpath(entry) in opened_paths,
            }
        )
    candidate_block["files"] = data_files

    # -- theta / reference comparison ---------------------------------------
    theta_key = {key: theta[key] for key in ("seed", "fidelity", "fraction", "n", "runs",
                                            "runtime_budget_ms", "timeout_s")}
    reference_row = None
    for row in reference.get("candidates", []):
        if row.get("candidate_id") == candidate_id:
            reference_row = row
    reference_active = bool(
        reference_row
        and theta_key == {key: reference["canonical_theta_e"][key] for key in theta_key}
        and theta["fidelity"] == "full"
    )

    def outcome_digest(doc):
        return (doc or {}).get("canonical_digest")

    routes_agree = (
        authority_outcome is not None
        and capture_outcome is not None
        and lib.canonical_json(authority_outcome) == lib.canonical_json(capture_outcome)
    )

    # -- payload ------------------------------------------------------------
    declared_paths = {os.path.realpath(repo_root / rel) for rel in declared_files}
    evaluator_sources = build_artifact_records(
        capture, declared_files=declared_files, entry_path=evaluator
    )
    child_sources = (
        build_artifact_records(child_probe, declared_files=declared_files,
                               entry_path=evaluator_root / "e_star_child.py")
        if child_probe
        else []
    )
    harness_paths = {os.path.realpath(__file__), os.path.realpath(BOOTSTRAP)}
    foreign_result = build_foreign_modules(
        capture, runtime=capture["runtime"], declared_paths=declared_paths,
        harness_dir=harness_paths,
    )
    foreign = foreign_result["foreign_modules"]
    child_foreign = (
        build_foreign_modules(child_probe, runtime=child_probe["runtime"],
                              declared_paths=declared_paths, harness_dir=harness_paths)
        if child_probe
        else {"foreign_modules": [], "harness_modules": []}
    )
    hazards = build_shadowing_hazards(capture, runtime=capture["runtime"])
    open_summary = summarize_open_events(capture, runtime=capture["runtime"], roots=roots)

    dependencies = build_dependencies(capture, repo_root=repo_root, eid_inputs=eid_inputs)
    config_value = eid_inputs["components"]["Config"]["canonical_material"]["value"]
    environment = build_environment(capture, child_probe, config_value)

    runtime_block = {
        "executable": capture["runtime"]["executable"],
        "executable_realpath": capture["runtime"]["executable_realpath"],
        "executable_sha256": capture["runtime"]["executable_sha256"],
        "version": capture["runtime"]["version"],
        "implementation": capture["runtime"]["implementation"],
        "cache_tag": capture["runtime"]["cache_tag"],
        "bytecode_magic_hex": capture["runtime"]["bytecode_magic_hex"],
        "version_full": capture["runtime"]["version_full"],
        "hexversion": capture["runtime"]["hexversion"],
        "api_version": capture["runtime"]["api_version"],
        "sys_prefix": capture["runtime"]["sys_prefix"],
        "sys_base_prefix": capture["runtime"]["sys_base_prefix"],
        "flags": capture["runtime"]["flags"],
        "platform": capture["runtime"]["platform"],
        "sys_path": capture["runtime"]["sys_path"],
    }

    payload = {
        "schema": lib.SCHEMA_PAYLOAD,
        "task": live_contract.get("task"),
        "eid_semantic": live_eid,
        "eid_semantic_components": live_components,
        "declared_component_digests": declared_components,
        "eid_semantic_declared": declared_eid,
        "eid_semantic_matches_declared": live_eid == declared_eid,
        "declared_eid_star_frozen": frozen_eid,
        "review_formula_semantic_4c": lib.review_formula_semantic(live_components),
        "invocation": {
            "mode": "authoritative-script + capture-import",
            "adapter_id": args.adapter,
            "evaluator_entry": lib.rel_to(evaluator, repo_root),
            "evaluator_entry_sha256": lib.sha256_file(evaluator)["sha256"],
            "theta_e": theta_key,
            "candidate_id": candidate_id,
            "cwd": lib.rel_to(os.getcwd(), repo_root),
            "env_overrides_for_the_evaluator": recorded_overrides,
        },
        "evaluator_execution": {
            "routes_agree": routes_agree,
            "authoritative_route": {
                "returncode": authority["returncode"],
                "outcome_canonical_digest": outcome_digest(authority_outcome),
                "status": (authority_outcome or {}).get("status"),
                "objective_value": ((authority_outcome or {}).get("objective") or {}).get("value"),            },
            "capture_route": {
                "returncode": capture_run["returncode"],
                "harness_exit_code": capture.get("exit_code"),
                "outcome_canonical_digest": outcome_digest(capture_outcome),
                "status": (capture_outcome or {}).get("status"),
                "objective_value": ((capture_outcome or {}).get("objective") or {}).get("value"),
            },
            "self_reported_evaluator_source_sha256": (authority_outcome or {}).get(
                "evaluator_source_sha256"
            ),
            "self_reported_interpreter": (authority_outcome or {}).get("interpreter"),
            "reference_table_row_expected_status": (reference_row or {}).get(
                "expected_status_at_theta_e_star"
            ),
            "reference_table_row_expected_digest": (reference_row or {}).get("canonical_digest"),
            "reference_comparison_applicable": reference_active,
            "reference_comparison_matches": (
                None if not reference_active
                else outcome_digest(authority_outcome) == (reference_row or {}).get("canonical_digest")
            ),
            "outcome_status": (authority_outcome or {}).get("status"),
        },
        "candidate": candidate_block,
        "runtime": runtime_block,
        "dependencies": dependencies,
        "environment": environment,
        "loaded_artifacts": {
            "declared_source_paths": sorted(declared_files),
            "declared_evaluator_entry": declared_evaluator_entry,
            "evaluator_sources": evaluator_sources,
            "evaluator_child_sources": child_sources,
            "foreign_modules": foreign + [
                item for item in child_foreign["foreign_modules"] if item not in foreign
            ],
            "harness_modules": foreign_result["harness_modules"] + child_foreign["harness_modules"],
            "shadowing_hazards": hazards,
            "opens_by_category": open_summary["by_category"],
            "opens_outside_all_known_roots": open_summary["outside_all_known_roots"],
            "child_argv_normalized": normalize_child_argv(
                capture["popen_events"][0]["argv"] if capture["popen_events"] else None
            ),
        },
    }

    eid_exec = lib.eid_execution(payload)

    observations = {
        "generated_by": "a0/attestation/attest.py",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "attestation_tool_interpreter": sys.executable,
        "attestation_tool_interpreter_matches_captured": (
            os.path.realpath(sys.executable) == capture["runtime"]["executable_realpath"]
        ),
        "scratch_dir": str(scratch),
        "state_root": str(state_root),
        "authoritative_route": authority,
        "capture_route": capture_run,
        "child_probe_route": child_probe,
        "module_count": len(capture["modules"]),
        "module_index_digest": lib.domain_digest(
            f"{lib.DOMAIN}/module_index",
            lib.canonical_json(
                sorted(
                    [module["name"], module.get("origin_kind"), module.get("origin") or "",
                     module.get("sha256") or ""]
                    for module in capture["modules"]
                )
            ),
        ),
        "modules_loaded_by_the_evaluator": sorted(
            module["name"] for module in capture["modules"] if not module.get("pre_existing")
        ),
        "harness_floor_modules": len(capture["pre_existing_modules"]),
        "exec_event_count": len(capture["exec_events"]),
        "open_event_count": len(capture["open_events"]),
        "import_event_count": len(capture["import_events"]),
        "socket_events": capture["socket_events"],
        "truncated": capture["truncated"],
        "declared_component_digests": declared_components,
        "live_component_digests": live_components,
        "components_match_declared": {
            name: declared_components[name] == live_components[name] for name in lib.COMPONENTS
        },
        "evalcontract_path": lib.rel_to(repo_root / "a0/contract/evalcontract.py", repo_root),
        "evalcontract_sha256": lib.sha256_file(repo_root / "a0/contract/evalcontract.py")["sha256"],
        "spec_path": lib.rel_to(spec_path, repo_root),
        "spec_sha256": lib.sha256_file(spec_path)["sha256"],
    }

    document = {
        "schema": lib.SCHEMA_ATTESTATION,
        "task": live_contract.get("task"),
        "eid_execution": eid_exec,
        "eid_semantic": live_eid,
        "eid_semantic_components": live_components,
        "declared_eid_star": declared_eid,
        "frozen_eid_star": frozen_eid,
        "payload": payload,
        "observations": observations,
    }
    attestation_out = Path(args.attestation_out).resolve() if args.attestation_out else (
        out_dir / f"attestation.{candidate_id}.{theta['fidelity']}.json"
    )
    attestation_out.parent.mkdir(parents=True, exist_ok=True)
    attestation_out.write_bytes(lib.canonical_json(document) + b"\n")

    if not args.keep_work:
        shutil.rmtree(scratch, ignore_errors=True)

    print(f"EID_semantic  {live_eid}")
    print(f"EID_execution {eid_exec}")
    print(f"declared EID* {declared_eid}  (frozen {frozen_eid})")
    print(f"semantic == declared: {live_eid == declared_eid} | frozen: {live_eid == frozen_eid}")
    print(f"routes agree: {routes_agree} | foreign modules: "
          f"{len(foreign) + len(child_foreign['foreign_modules'])}"
          f" | shadowing hazards: {len(hazards)}")
    print(f"wrote {attestation_out}")
    if not routes_agree:
        print("WARNING: the authoritative CLI route and the capture route disagree; "
              "the attestation is not representative of the invocation", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except lib.AttestError as exc:
        print(f"attest: {exc}", file=sys.stderr)
        raise SystemExit(2)
