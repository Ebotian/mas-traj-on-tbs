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
import sys
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


# --------------------------------------------------------------------------------------
# the measurement envelope (external review D3) for the fixtures
#
# A fixture is a test double, so it plays the adapter's side of the protocol: it reads the
# envelope the runner handed it (`A0_ENVELOPE`, or `--envelope`), echoes the per-candidate
# measurement token, and attests the evaluator bytes, candidate bytes and behaviour digest it
# used. The `--envelope` flag exists so a fixture can also be driven by hand.

ENVELOPE_ENV = "A0_ENVELOPE"
E_ENVELOPE = A0 / "envelope"


def envelope_module():
    """Import `a0/envelope/envelope.py` by path: the fixtures use the checker's own code."""
    if str(E_ENVELOPE) not in sys.path:
        sys.path.insert(0, str(E_ENVELOPE))
    import envelope as envelope_mod  # noqa: PLC0415

    return envelope_mod


def envelope_from_flags(flags: dict):
    """The envelope the runner handed this adapter, or None when none was handed over."""
    path = flags.get("envelope") or os.environ.get(ENVELOPE_ENV) or None
    if not path:
        return None
    candidate = Path(path)
    if not candidate.is_file():
        return None
    return json.loads(candidate.read_text())


def frozen_outcome(candidate_id: str) -> dict:
    """The frozen Outcome payload for one member of C* (the table is the harness's own record)."""
    table = json.loads(E_STAR_TABLE.read_text())
    for entry in table["candidates"]:
        if entry["candidate_id"] == candidate_id:
            return entry.get("outcome") or {}
    return {}


def measurement_block(candidate_id: str, *, envelope, measured_candidate_sha256=None,
                      outcome: dict | None = None, identity: str = "own",
                      overrides: dict | None = None) -> dict:
    """Build the row's measurement attestation -- the adapter's side of the D3 protocol.

    `identity="own"` attests what this fixture really did (the honest template); `identity="omit"`
    emits the token with no identity material at all (the omission fault). Every other fault is
    injected through `overrides` with a *real* value -- another evaluator's source digest computed
    from its bytes, another candidate's measured sha256 -- never a fabricated string, so the
    self-test shows the checker rejecting an attack, not a typo.
    """
    env_mod = envelope_module()
    token = env_mod.token_for(envelope or {}, candidate_id) if envelope else None
    block = {
        "schema": env_mod.SCHEMA_ATTESTATION,
        "oid": (token or {}).get("oid"),
        "harness_run_id": (envelope or {}).get("harness_run_id"),
        "nonce": (envelope or {}).get("nonce"),
        "note": (
            "the fixture plays the adapter's side of the measurement-token protocol (external review D3)"
            if token else "no envelope was handed to this adapter, so no token could be echoed"
        ),
    }
    if identity != "omit":
        block.update(
            {
                "eid_star": (envelope or {}).get("eid_star"),
                "evaluator_source_sha256": env_mod.evaluator_source_digest(E_STAR_SCRIPT.parent),
                "candidate_sha256": measured_candidate_sha256,
                "behaviour_digest": env_mod.behaviour_digest(outcome) if outcome else None,
                "interpreter": (outcome or {}).get("interpreter"),
                "theta_e": (outcome or {}).get("theta_e"),
            }
        )
    if overrides:
        block.update(overrides)
    return block
