# What an A1 iteration must record for attribution to hold

Rationale is in `SPEC.md` §7. This is the operational checklist. The claim an A1 result is allowed
to make is:

> Δ over the **same declared model route**, under the **same counted budget**.

Nothing stronger. In particular, not "same model weights" — that is frozen as unverifiable
(`RequestedModel.weights_identity.verifiable: false`).

## Per-iteration record

```json
{
  "run_id": "...",
  "iteration": 0,
  "runtime": "kapso|eve|loreley|simpleloop",
  "lane": "claude_code",
  "mrc_star": "dfb9316f60d44d2c3363d755f777f65e0b0a6938fa864518ad077bcc2aa1f78c",
  "model_identity": {
    "declared_route_model": "deepseek-flash",
    "requested_model_id": "deepseek-flash",
    "reported_model_id": "deepseek-flash",
    "reporting_surface": "anthropic_messages",
    "echoed_verbatim": true,
    "note": "echo is not proof of weights; recorded, not trusted"
  },
  "cli": {
    "name": "claude",
    "version": "2.1.278",
    "binary_sha256": "356673de39ab5e9e4d19314c33b2d0b01fa06519a44c3374aa947bfbd71a4049"
  },
  "effective_params": {"max_tokens_per_turn": 32000, "stream": true, "temperature": null},
  "effective_posture": {
    "approval_policy": "...",
    "sandbox_mode": "...",
    "egress_policy": "deny_by_default_hostname_allowlist",
    "network_topology": "docker_internal_plus_dual_homed_allowlist_proxy"
  },
  "prompt": {"system_prompt_sha256": "...", "context_budget_tokens": 200000},
  "eid_star": "664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328",
  "evaluator_outcome_ref": "<score trace event_id>"
}
```

## Non-negotiables

1. **Record `mrc_star` on every turn.** A run that mixes routes (e.g. a `deepseek-v4-pro`
   calibration arm) must record a distinct `mrc_star` per turn; an unrecorded route swap destroys
   attribution.
2. **Record both `requested_model_id` and `reported_model_id`, plus the surface.** They can differ
   on a retired alias, and the surface is what decides which of the two strings you get.
3. **Record the CLI binary hash**, not just the version string — the tool set changed between
   2.1.260 and 2.1.278.
4. **Record the prompt digest actually sent.** It is the largest unfrozen field in the contract;
   `Prompt.system_prompt_sha256` is `null` in the declarations for exactly this reason.
5. **Record effective params and posture as used**, not the declared defaults — a CLI may override
   them (`max_tokens=32000` for a non-`claude-*` id is the known case).
6. **Run under the declared network topology.** The declarations freeze the closed `a0pc-*` route;
   a run made with open egress is not on the declared route.

## Interaction with `B_hard = (T_wall, N_evaluatorCalls, concurrency cap)`

| budget axis | cross-route comparability | what to record |
|---|---|---|
| `T_wall` | **weak** — per-turn latency differs by route (flash ~5.5 s vs pro ~12.6 s on the same task), so a faster route fits more iterations into the same wall clock | record `T_wall` **and** `N_evaluatorCalls` together |
| `N_evaluatorCalls` | **strong** — counts calls to the local frozen `E*`, so it is route-invariant and is the anchor for comparison | this is the denominator to report |
| `concurrency cap` | bounds model spend, where routes diverge most — claude spends ~17.2k input tokens per trivial turn vs codex ~0.8k | record `N_modelCalls`, `T_in`, `T_out`, per-route token counts |

Every `resource` trace event must carry the route (`mrc_star`) so a budget trace can be split by
route; a merged trace silently mixes the two arms' budgets.
