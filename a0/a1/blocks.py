"""The randomised complete block scheduler, with block-level invalidation.

**Why blocks.**  ``a0/A1-REQUIREMENTS.md`` §4.3 asks for an execution order in
which service-side drift, load and time become a *block* effect rather than a
*runtime* effect.  The device is a randomised complete block: one block contains
exactly one campaign per arm, the arms are ordered inside the block by a seeded
shuffle, and blocks are the unit of replication.

**Why invalidation is block-level.**  An outage — a relay interruption, a
restart that removes a container, an arm that lost its model lane mid-block — is
a property of the *window*, not of the arm that happened to be running when it
hit.  Re-running only the interrupted campaign would leave the other arms'
numbers measured under a different service condition, which is exactly the
confound the block exists to remove.  So the whole block is discarded and
re-run; a partially completed block never contributes to :math:`\\Delta`.

The schedule is a pure function of ``(blocks, arms, replicates, seed)``, so the
frozen order can be recomputed by a third party from the contract alone.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .causal import CampaignID

#: Per-campaign outcomes the scheduler understands.
COMPLETE = "complete"
OUTAGE = "outage"
INVALIDATED = "invalidated"
PENDING = "pending"


@dataclass
class CampaignRecord:
    campaign_id: CampaignID
    status: str = PENDING
    evidence: Dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "campaign": self.campaign_id.as_dict(),
            "status": self.status,
            "evidence": self.evidence,
        }


@dataclass
class Block:
    block_id: str
    order: List[str] = field(default_factory=list)   # arm ids, in execution order
    records: Dict[str, CampaignRecord] = field(default_factory=dict)
    invalidated: bool = False
    invalidation_reason: Optional[str] = None

    @property
    def complete(self) -> bool:
        return (not self.invalidated) and self.records and all(
            record.status == COMPLETE for record in self.records.values()
        )

    def as_dict(self) -> dict:
        return {
            "block_id": self.block_id,
            "order": self.order,
            "invalidated": self.invalidated,
            "invalidation_reason": self.invalidation_reason,
            "complete": self.complete,
            "records": {arm: record.as_dict() for arm, record in sorted(self.records.items())},
        }


class BlockError(RuntimeError):
    """A scheduling request that would break the design."""


def plan_blocks(
    *,
    task_id: str,
    arms: Iterable[str],
    blocks: int,
    replicates: int = 1,
    seed: int,
) -> List[Block]:
    """Build the frozen execution plan.

    ``blocks`` blocks, each containing every arm once per replicate; the arm
    order inside each block is drawn from ``random.Random(seed)`` so the order is
    reproducible from the contract and cannot be chosen after seeing a result.
    """
    arms = sorted(arms)
    if not arms:
        raise BlockError("no arms")
    if blocks < 1 or replicates < 1:
        raise BlockError("blocks and replicates must be positive")
    rng = random.Random(seed)
    planned: List[Block] = []
    for index in range(blocks):
        block_id = f"B{index:03d}"
        block = Block(block_id=block_id)
        for replicate in range(replicates):
            order = list(arms)
            rng.shuffle(order)
            for arm in order:
                campaign = CampaignID(
                    task_id=task_id,
                    block_id=block_id,
                    arm_id=arm,
                    replicate_id=f"R{replicate:03d}",
                )
                if campaign.key in block.records:
                    raise BlockError(
                        f"block {block_id} would contain {campaign.key} twice: a complete "
                        "block has exactly one campaign per (arm, replicate)"
                    )
                block.records[campaign.key] = CampaignRecord(campaign_id=campaign)
                # `order` holds campaign keys, so `schedule()` is a plain walk.
                block.order.append(campaign.key)
        planned.append(block)
    return planned


@dataclass
class BlockScheduler:
    """Holds the plan and applies the two transitions: complete, and invalidate."""

    task_id: str
    blocks: List[Block]
    events: List[dict] = field(default_factory=list)

    @classmethod
    def build(cls, *, task_id: str, arms: Iterable[str], blocks: int, replicates: int,
              seed: int) -> "BlockScheduler":
        return cls(
            task_id=task_id,
            blocks=plan_blocks(task_id=task_id, arms=arms, blocks=blocks,
                               replicates=replicates, seed=seed),
        )

    # -- lookups ----------------------------------------------------------
    def block_of(self, campaign_key: str) -> Block:
        for block in self.blocks:
            if campaign_key in block.records:
                return block
        raise BlockError(f"unknown campaign {campaign_key!r}")

    def schedule(self) -> List[str]:
        """The frozen order, skipping invalidated or finished blocks."""
        order: List[str] = []
        for block in self.blocks:
            if block.invalidated:
                continue
            for key in block.order:
                order.append(key)
        return order

    # -- transitions ------------------------------------------------------
    def complete(self, campaign_key: str, *, evidence: Optional[dict] = None) -> dict:
        block = self.block_of(campaign_key)
        if block.invalidated:
            raise BlockError(f"block {block.block_id} is invalidated; {campaign_key} is not runnable")
        record = block.records[campaign_key]
        record.status = COMPLETE
        record.evidence = dict(evidence or {})
        event = {"event": "complete", "campaign": campaign_key, "block": block.block_id}
        self.events.append(event)
        return event

    def outage(self, campaign_key: str, *, reason: str, detail: str = "") -> dict:
        """An outage invalidates the **whole block**, not just this campaign."""
        block = self.block_of(campaign_key)
        record = block.records[campaign_key]
        record.status = OUTAGE
        record.evidence = {"reason": reason, "detail": detail}
        if not block.invalidated:
            block.invalidated = True
            block.invalidation_reason = f"{reason} (hit {block.block_id} during {campaign_key})"
        for key, other in block.records.items():
            if other.status == PENDING:
                other.status = INVALIDATED
        for key in block.order:
            if block.records[key].status not in (OUTAGE, INVALIDATED):
                # A campaign that had already completed inside an invalidated
                # block is marked too: its number was measured in a window that
                # the design has declared unusable, so it must not be reused.
                block.records[key].status = INVALIDATED
        event = {
            "event": "block_invalidated",
            "block": block.block_id,
            "triggered_by": campaign_key,
            "reason": reason,
            "detail": detail,
            "invalidated_campaigns": list(block.order),
        }
        self.events.append(event)
        return event

    def rerun_block(self, block_id: str, *, new_block_id: str) -> Block:
        """A fresh block with the same arms, to replace an invalidated one.

        The replacement is a *new* block, not a repair of the old one: the
        window has moved, so its campaigns are new units with new ids and the
        invalidated block keeps its record of why it was discarded.
        """
        source = next((block for block in self.blocks if block.block_id == block_id), None)
        if source is None:
            raise BlockError(f"unknown block {block_id!r}")
        if not source.invalidated:
            raise BlockError(f"block {block_id!r} was not invalidated; refusing to rerun it")
        arms = sorted({record.campaign_id.arm_id for record in source.records.values()})
        replacement = plan_blocks(
            task_id=self.task_id, arms=arms, blocks=1, replicates=1,
            seed=abs(hash((block_id, new_block_id))) % (2**31),
        )[0]
        replacement.block_id = new_block_id
        remapped: Dict[str, CampaignRecord] = {}
        order_map: Dict[str, str] = {}
        for key in replacement.order:
            old = replacement.records[key]
            campaign = CampaignID(
                task_id=self.task_id,
                block_id=new_block_id,
                arm_id=old.campaign_id.arm_id,
                replicate_id=old.campaign_id.replicate_id,
            )
            remapped[campaign.key] = CampaignRecord(campaign_id=campaign)
            order_map[key] = campaign.key
        replacement.records = remapped
        replacement.order = [order_map[key] for key in replacement.order]
        self.blocks.append(replacement)
        self.events.append({
            "event": "block_rerun",
            "replaces": block_id,
            "new_block": new_block_id,
        })
        return replacement

    # -- reporting --------------------------------------------------------
    def status(self) -> dict:
        usable = [block for block in self.blocks if block.complete]
        return {
            "schema": "a0.a1.block_schedule/v1",
            "task_id": self.task_id,
            "blocks": [block.as_dict() for block in self.blocks],
            "planned_campaigns": sum(len(block.records) for block in self.blocks),
            "usable_blocks": [block.block_id for block in usable],
            "invalidated_blocks": [block.block_id for block in self.blocks if block.invalidated],
            "events": self.events,
            "delta_admissible": bool(usable) and all(
                len(block.records) == len({r.campaign_id.arm_id for r in block.records.values()})
                for block in usable
            ),
        }

    def write(self, path: Path) -> None:
        Path(path).write_text(json.dumps(self.status(), indent=1, sort_keys=True) + "\n",
                              encoding="utf-8")
