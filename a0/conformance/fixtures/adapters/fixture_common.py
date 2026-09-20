"""Shared plumbing for the conformance fixtures.

These fixtures are **test doubles**, not runtime adapters: they exist so that
`a0/conformance/selftest.py` can prove that the A0.1 checker actually rejects a non-conformant
adapter. `reference_adapter.py` is honest (it really executes `E*` through the frozen CLI and
is the template a real adapter should follow); `deviant.py` injects one named fault per mode.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
A0 = HERE.parents[2]  # fixtures/adapters -> fixtures -> conformance -> a0
TASK = A0 / "tasks" / "circle-packing"
C_STAR_MANIFEST = TASK / "C_STAR" / "manifest.json"
E_STAR_SCRIPT = TASK / "e_star.py"
E_STAR_PYTHON = TASK / ".venv" / "bin" / "python"
E_STAR_TABLE = TASK / "E_STAR.json"
FR_DECLARATION = A0 / "contract" / "fr" / "scalar.json"

THETA_KEYS = ("seed", "fidelity", "fraction", "n", "runs", "runtime_budget_ms", "timeout_s")

# F6: a fixture is a test double, so it must not leave directories in the study tree. Its scratch
# root is `$A0_FIXTURE_RUN_ROOT` when the caller (selftest.py, or conformance.py driving the control
# rows) names one it will clean up, and otherwise a fresh system temp directory -- never a path
# inside `a0/conformance/out/`, which is the deliverable's artifact area.
SCRATCH_ENV = "A0_FIXTURE_RUN_ROOT"
_SCRATCH_ROOT = {}


def scratch_root() -> Path:
    if "root" not in _SCRATCH_ROOT:
        override = os.environ.get(SCRATCH_ENV)
        root = Path(override) if override else Path(tempfile.mkdtemp(prefix="a0-fixture-runs-"))
        root.mkdir(parents=True, exist_ok=True)
        _SCRATCH_ROOT["root"] = root
    return _SCRATCH_ROOT["root"]


def read_args(argv):
    """Flag/value reader: the runner appends `<subcommand> --flag value ...` to our base argv."""
    positional, flags = [], {}
    i = 0
    while i < len(argv):
        token = argv[i]
        if token.startswith("--"):
            name = token[2:]
            if "=" in name:
                name, value = name.split("=", 1)
            else:
                value = argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith("--") else "true"
                i += 1
            flags[name] = value
        else:
            positional.append(token)
        i += 1
    return positional, flags


def parse_theta(text: str) -> dict:
    theta = {}
    for part in (text or "").split(","):
        if not part.strip():
            continue
        key, _, value = part.partition("=")
        key, value = key.strip(), value.strip()
        if value == "true":
            value = True
        elif value == "false":
            value = False
        else:
            for cast in (int, float):
                try:
                    value = cast(value)
                    break
                except ValueError:
                    continue
        theta[key] = value
    return theta


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def canonical_file_digest(path: Path) -> str:
    return hashlib.sha256(canonical_json(json.loads(Path(path).read_text()))).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def eid_r_declaration(eid_star: str, runtime: str, adapter: str) -> dict:
    """A recomputable EID_r -> EID* mapping: a domain-separated digest a third party can redo."""
    domain = f"a0/fixture/{adapter}/v1/EID_r"
    payload = {"eid_star": eid_star, "runtime": runtime}
    value = hashlib.sha256(domain.encode("ascii") + b"\x00" + canonical_json(payload)).hexdigest()
    return {
        "value": value,
        "native_scheme": "none",
        "mapping_mode": "adapter_declared_injection",
        "derives_from_eid_star": eid_star,
        "declarations_verbatim_from": eid_star,
        "declaration": (
            f"{adapter} has no native evaluator identity; EID_r is a domain-separated digest over "
            "(eid_star, runtime) so that it is a function of EID* alone."
        ),
        "recomputable": True,
        "derivation": {"algorithm": "sha256", "domain": domain, "payload_canonical": canonical_json(payload).decode("ascii")},
    }


def frozen_theta(default: dict) -> dict:
    theta = dict(default)
    return theta


def write_out(path, doc) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def reference_rows_from_sweep() -> list:
    """The runner's own frozen sweep -- used only by the deviant fixture as ground truth to corrupt."""
    doc = json.loads((A0 / "conformance" / "reference.json").read_text())
    return doc["fresh_sweep"]["rows"]
