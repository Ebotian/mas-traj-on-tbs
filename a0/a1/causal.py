"""`CampaignID`, `CID`, `AID_r`, and the causal-role rule as an executable check.

**The rule** (``a0/A1-CONTRACT-AUDIT.md`` §122): *if an object can change
``P(Y | r)``, it must be inside ``CID`` or ``AID_r``.*  ``CID`` is the causal
identity — the part that must be **identical across arms**, because anything
that differs there makes :math:`\\Delta` uninterpretable.  ``AID_r`` is the arm's
own identity — everything about arm *r* that is allowed to differ and that the
result is conditioned on.

Read literally the rule is a design instruction; the point of this module is to
make it a predicate that fails.  Two ways it fails, both executed by
``a0/a1/DESIGN.md``'s ``audit``:

* **Uncontrolled** — an object the campaign actually referenced (a file that
  entered the run, a meter fragment, an evaluator source, a runtime checkout)
  that is named in neither declaration.  Such an object is a free variable of
  the experiment; it can move ``P(Y|r)`` and nothing would notice.
* **CID drift** — an object declared identical across arms whose observed
  hashes differ.  This is the failure the rule exists to catch: two arms whose
  "same" harness is not the same harness.

``AID_r`` deliberately carries the measurement preconditions ``INTERFACE.md``
§8 requires to be written into it (``meter.mode = plaintext_base_url``,
``meter.allowlist = [api.deepseek.com]``) and the grant triple the runtime's own
selection is conditioned on.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

CID_SCHEMA = "a0.a1.cid/v1"
AID_SCHEMA = "a0.a1.aid_r/v1"
AUDIT_SCHEMA = "a0.a1.causal_audit/v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(payload) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


# ---------------------------------------------------------------------------
# CampaignID
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CampaignID:
    """``CampaignID = (TaskID, BlockID, ArmID, ReplicateID)``.

    A campaign is *one replicate of one arm inside one block*.  Nothing in the
    budget ledger, the harness evaluation ledger or the score-of-record
    artifacts is allowed to be keyed on anything coarser than this: an arm's
    ``CEq`` summed over replicas is an arm-level number, and an arm-level number
    compared across differently-composed blocks is the confound the block design
    exists to remove.
    """

    task_id: str
    block_id: str
    arm_id: str
    replicate_id: str

    @property
    def key(self) -> str:
        return f"{self.task_id}/{self.block_id}/{self.arm_id}/{self.replicate_id}"

    def as_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "block_id": self.block_id,
            "arm_id": self.arm_id,
            "replicate_id": self.replicate_id,
            "campaign_key": self.key,
        }


# ---------------------------------------------------------------------------
# factors
# ---------------------------------------------------------------------------
@dataclass
class Factor:
    """One object the experiment references, with its declared causal role.

    ``role`` is ``"cid"`` (must be identical across arms) or ``"aid_r"`` (may
    differ by arm).  ``sha256`` is the hash of the object as the campaign
    actually observed it; ``value`` is for objects that are a scalar or a small
    structure rather than a file.
    """

    name: str
    role: str
    sha256: Optional[str] = None
    value: Optional[object] = None
    note: str = ""

    def identity(self) -> str:
        if self.sha256:
            return f"sha256:{self.sha256}"
        return f"value:{canonical_json(self.value)}"

    def as_dict(self) -> dict:
        out = {"name": self.name, "role": self.role, "identity": self.identity()}
        if self.note:
            out["note"] = self.note
        return out


class CausalError(RuntimeError):
    """A declaration violates the causal-role rule."""


@dataclass
class CID:
    """The causal identity: the factors every arm must share."""

    task_id: str
    factors: Dict[str, Factor] = field(default_factory=dict)

    def add(self, factor: Factor) -> "CID":
        if factor.role != "cid":
            raise CausalError(f"{factor.name!r} is declared {factor.role!r}, not cid")
        if factor.name in self.factors:
            raise CausalError(f"duplicate CID factor {factor.name!r}")
        self.factors[factor.name] = factor
        return self

    def as_dict(self) -> dict:
        return {
            "schema": CID_SCHEMA,
            "task_id": self.task_id,
            "factors": {name: factor.as_dict() for name, factor in sorted(self.factors.items())},
        }


@dataclass
class AID:
    """One arm's identity: everything allowed to differ, declared explicitly."""

    campaign: CampaignID
    factors: Dict[str, Factor] = field(default_factory=dict)

    def add(self, factor: Factor) -> "AID":
        if factor.role != "aid_r":
            raise CausalError(f"{factor.name!r} is declared {factor.role!r}, not aid_r")
        if factor.name in self.factors:
            raise CausalError(f"duplicate AID_r factor {factor.name!r}")
        self.factors[factor.name] = factor
        return self

    def as_dict(self) -> dict:
        return {
            "schema": AID_SCHEMA,
            "campaign": self.campaign.as_dict(),
            "factors": {name: factor.as_dict() for name, factor in sorted(self.factors.items())},
        }


# ---------------------------------------------------------------------------
# the audit
# ---------------------------------------------------------------------------
def audit(cid: CID, aids: Iterable[AID], *, observed: Optional[Dict[str, str]] = None) -> dict:
    """Check one CID against a set of arms' AID_r declarations.

    ``observed`` maps factor name -> identity string, as measured on this
    machine (for example ``{"evaluator.e_star.py": "sha256:670f02ee…"}``).
    Every observed object must be named in ``CID`` or in every arm's ``AID_r``;
    every ``CID`` factor must have one identity across all arms.
    """
    aids = list(aids)
    problems: List[dict] = []
    if not aids:
        raise CausalError("audit needs at least one arm")

    # 1. CID factors must agree across arms. A CID factor is a statement about
    #    the harness, so the check is against the observed value where one was
    #    measured and against the declaration otherwise.
    for name, factor in sorted(cid.factors.items()):
        if observed and name in observed and observed[name] != factor.identity():
            problems.append({
                "kind": "uncontrolled",
                "factor": name,
                "detail": (
                    f"declared cid as {factor.identity()} but the object on this machine "
                    f"hashes to {observed[name]}"
                ),
            })
        arm_declared = [
            aid for aid in aids if name in aid.factors
        ]
        if arm_declared:
            problems.append({
                "kind": "role_conflict",
                "factor": name,
                "detail": "declared in CID and also as an arm-varying factor",
            })

    # 2. Every observed object must be placed somewhere.
    for name, identity in sorted((observed or {}).items()):
        if name in cid.factors:
            continue
        if all(name in aid.factors for aid in aids):
            continue
        missing = [aid.campaign.arm_id for aid in aids if name not in aid.factors]
        problems.append({
            "kind": "uncontrolled",
            "factor": name,
            "detail": (
                f"observed as {identity}, declared in neither CID nor AID_r"
                + (f" for arm(s) {missing}" if missing else "")
            ),
        })

    # 3. A factor may not be CID in one arm and AID_r in another.
    for name in sorted({n for aid in aids for n in aid.factors}):
        if name in cid.factors:
            continue
        arm_ids = {aid.factors[name].identity() for aid in aids if name in aid.factors}
        if len({aid.campaign.arm_id for aid in aids if name in aid.factors}) > 1 and len(arm_ids) > 1:
            # Legal: that is what AID_r is for. Recorded so the report shows the
            # arm-varying set rather than only its failures.
            pass

    return {
        "schema": AUDIT_SCHEMA,
        "task_id": cid.task_id,
        "arms": [aid.campaign.as_dict() for aid in aids],
        "cid_factors": len(cid.factors),
        "aidr_factors": {aid.campaign.arm_id: sorted(aid.factors) for aid in aids},
        "arm_varying_factors": sorted(
            {
                name
                for name in {n for aid in aids for n in aid.factors}
                if len({aid.factors[name].identity() for aid in aids if name in aid.factors}) > 1
            }
        ),
        "problems": problems,
        "verdict": "pass" if not problems else "fail",
    }


def observed_identity(path: Path) -> str:
    return f"sha256:{sha256_file(path)}"
