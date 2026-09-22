"""The ``B_hard`` enforcer: meter ledger + wall clock + evaluator-call counter.

``INTERFACE.md`` §9 fixes the default shape — ``T_wall`` as the design's primary
constraint, ``CEq_max`` and ``N_E,max`` as the pre-registered caps — and
principle (iv) says the budget must be enforceable *where the runtime cannot
lie*.  Every number this enforcer reads therefore comes from a file the
**harness** wrote:

======  ============================  ==========================================
term    read from                     who wrote it
======  ============================  ==========================================
CEq     ``a0/meter`` ledger           the metering proxy, from upstream usage
N_E     harness eval ledger           ``a0/a1/eval_service.py``, one row per E*
T_wall  the harness's own monotonic   the A1 driver
======  ============================  ==========================================

The runtime's own ``cost_usd`` / ``tokens`` fields are diagnostics and are never
read here.  Two failure modes are refused rather than estimated:

* **unmetered** — a ledger row with ``unmetered: true`` (or a missing ledger) means
  the campaign's ``CEq`` is not established.  Continuing would let real spend
  enter the experiment as an unknown, so the enforcer stops the campaign.
* **extra keys** — the enforcer only counts the frozen field set; an unknown
  ``reason`` does not become a zero.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


class BudgetError(RuntimeError):
    """The ledger cannot be read, so the budget cannot be enforced."""


#: `unmetered` reasons that record a *refusal* (the proxy forwarded nothing), as
#: opposed to a *gap* (a call reached the model and its usage was not
#: observable).  `a0/meter/README.md` §2 lists both families; the split matters
#: because only a gap makes the campaign's CEq unknown.
REFUSAL_REASONS = {
    "non_allowlisted_host",
    "host_header_not_allowlisted",
    "path_not_routed",
    "connect_not_supported",
    "attribution_token_mismatch",
}


@dataclass(frozen=True)
class Budget:
    """The hard vector ``(T_wall, N_evaluatorCalls, CEq_max, P_concurrency)``."""

    T_wall_sec: float
    N_eval_max: int
    CEq_max: int
    P_concurrency: int = 1

    def as_dict(self) -> dict:
        return {
            "T_wall_sec": self.T_wall_sec,
            "N_evaluatorCalls": self.N_eval_max,
            "CEq_max": self.CEq_max,
            "P_concurrency": self.P_concurrency,
            "measured_by": {
                "T_wall_sec": "harness monotonic clock",
                "N_evaluatorCalls": "a0/a1/eval_service.py ledger",
                "CEq_max": "a0/meter ledger",
            },
        }


def read_meter_ledger(path: Path, *, campaign_id: Optional[str] = None,
                      arm_id: Optional[str] = None) -> Dict[str, object]:
    """Sum ``CEq`` over the rows that belong to this campaign.

    Attribution is by ledger row, which the metering proxy fixed at ``bind()``
    time (``a0/meter/README.md`` §3) — not by anything the runtime sent.

    ``unmetered`` rows are split in two, because they mean different things:

    * a **refusal** (``non_allowlisted_host``, ``connect_not_supported``, …) is a
      call the proxy declined to forward; nothing was spent, and
      ``a0/meter/README.md`` §4 records it as a *policy* outcome.  It is counted
      and reported but it cannot make a campaign's ``CEq`` unknown.
    * a **gap** (``no_usage_field_in_response``, ``stream_…``, …) is a call that
      did reach the model and whose usage was not observable.  The campaign's
      ``CEq`` is then not established, and the enforcer stops on it.
    """
    path = Path(path)
    rows = 0
    ceq = 0
    gaps: List[dict] = []
    refusals: List[dict] = []
    reasons: Dict[str, int] = {}
    if not path.is_file():
        raise BudgetError(f"meter ledger not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if campaign_id is not None and row.get("campaign_id") != campaign_id:
                continue
            if arm_id is not None and row.get("arm_id") != arm_id:
                continue
            rows += 1
            if row.get("unmetered"):
                entry = {"ts": row.get("ts"), "reason": row.get("reason")}
                reason = str(row.get("reason"))
                reasons[reason] = reasons.get(reason, 0) + 1
                if reason.split(":", 1)[0] in REFUSAL_REASONS:
                    refusals.append(entry)
                else:
                    gaps.append(entry)
                continue
            value = row.get("ceq")
            if value is None:
                gaps.append({"ts": row.get("ts"), "reason": "ceq_null_without_unmetered_flag"})
                continue
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise BudgetError(f"ledger row carries a non-integer ceq: {value!r}")
            ceq += value
    return {
        "ledger": str(path),
        "rows": rows,
        "ceq": ceq,
        "unmetered_rows": len(gaps),
        "unmetered": gaps,
        "refused_rows": len(refusals),
        "refusals": refusals,
        "reasons": reasons,
    }


def read_harness_eval_ledger(path: Path, *, campaign_id: Optional[str] = None) -> Dict[str, object]:
    """Count the harness's own E* invocations for this campaign."""
    path = Path(path)
    if not path.is_file():
        return {"ledger": str(path), "rows": 0, "evaluator_calls": 0, "missing": True}
    rows = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if campaign_id is not None and row.get("campaign_id") != campaign_id:
                continue
            rows += 1
    return {"ledger": str(path), "rows": rows, "evaluator_calls": rows, "missing": False}


@dataclass
class BudgetEnforcer:
    """Evaluates the three terms before a campaign continues to the next step."""

    budget: Budget
    meter_ledger: Path
    harness_eval_ledger: Path
    campaign_id: str
    arm_id: str
    started_at: float = field(default_factory=time.monotonic)
    evaluator_calls_seen: int = 0
    checks: List[dict] = field(default_factory=list)

    def snapshot(self) -> dict:
        meter = read_meter_ledger(self.meter_ledger, campaign_id=self.campaign_id,
                                  arm_id=self.arm_id)
        evals = read_harness_eval_ledger(self.harness_eval_ledger,
                                         campaign_id=self.campaign_id)
        return {
            "T_wall_sec": time.monotonic() - self.started_at,
            "CEq": meter["ceq"],
            "CEq_rows": meter["rows"],
            "unmetered_rows": meter["unmetered_rows"],
            "unmetered": meter["unmetered"],
            "refused_rows": meter["refused_rows"],
            "refusals": meter["refusals"],
            "reasons": meter["reasons"],
            "N_evaluatorCalls": evals["evaluator_calls"],
            "meter_ledger_missing": not Path(self.meter_ledger).is_file(),
            "harness_eval_ledger_missing": bool(evals["missing"]),
        }

    def check(self, *, label: str = "") -> dict:
        """Return the verdict. ``within=False`` means the caller must stop."""
        state = self.snapshot()
        self.evaluator_calls_seen = int(state["N_evaluatorCalls"])
        stopped: Optional[str] = None
        detail = ""

        if state["unmetered_rows"] > 0:
            # Fail closed: a campaign whose spend is not fully established cannot
            # claim a budget. The rows are returned so the reason is auditable.
            stopped = "budget_exhausted:unmetered_model_call"
            detail = (
                f"{state['unmetered_rows']} ledger row(s) carry no usage; CEq is not "
                f"established. reasons={sorted(state['reasons'])}"
            )
        elif state["T_wall_sec"] > self.budget.T_wall_sec:
            stopped = "budget_exhausted:T_wall_sec"
            detail = f"{state['T_wall_sec']:.3f}s > {self.budget.T_wall_sec}s"
        elif state["CEq"] > self.budget.CEq_max:
            stopped = "budget_exhausted:CEq_max"
            detail = f"{state['CEq']} > {self.budget.CEq_max}"
        elif state["N_evaluatorCalls"] > self.budget.N_eval_max:
            stopped = "budget_exhausted:N_evaluatorCalls"
            detail = f"{state['N_evaluatorCalls']} > {self.budget.N_eval_max}"

        verdict = {
            "schema": "a0.a1.budget_check/v1",
            "label": label,
            "campaign_id": self.campaign_id,
            "arm_id": self.arm_id,
            "budget": self.budget.as_dict(),
            "observed": state,
            "within": stopped is None,
            "stopped_because": stopped,
            "detail": detail,
        }
        self.checks.append(verdict)
        return verdict
