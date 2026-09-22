"""A1 orchestration: harness-owned evaluation, causal identity, budget, blocks.

Nothing in this package is a runtime.  It is the *harness* side of A1:

* ``eval_service``  — the process that owns every ``E*`` invocation and authors
  the ``Outcome`` the runtime under test consumes;
* ``causal``        — ``CampaignID``, ``CID`` / ``AID_r`` and the causal-role
  rule as an executable predicate;
* ``budget``        — the ``B_hard`` enforcer (meter ledger + wall clock +
  evaluator-call counter), fail-closed;
* ``blocks``        — the randomised complete block scheduler with block-level
  invalidation on outage;
* ``meter_runner``  — one metering proxy listener per campaign, and the ledger
  read side;
* ``topology``      — the closed topology (``unshare -rn`` + a unix-socket hop
  to the host's metering proxy) and its egress probes.

``a0/a1/DEVIATIONS.md`` records every interpretation of ``INTERFACE.md`` made
here; ``a0/a1/DESIGN.md`` is the wiring report.
"""
