# PROPOSED patch — admit a DeepSeek id to the seed-portfolio lane

Status: **proposal only. Loreley's source was NOT modified** (verified: `git status` in the
checkout is clean; this file lives in `a0/notes/exit-closed/kilo-deepseek/`).

## The blocker, precisely

The seed-portfolio lane is gated on a **hardcoded model id**, in **two** places, not one:

| # | Site | Code |
|---|---|---|
| 1 | `loreley/preflight.py:397` | `if model.rsplit("/", 1)[-1] != "gpt-5.6-sol":` → `CheckResult(..., "fail", "initial seed portfolio contract is pinned to gpt-5.6-sol ...")` |
| 2 | `loreley/scheduler/seed_portfolios.py:147` | `if model.rsplit("/", 1)[-1] != "gpt-5.6-sol":` → `raise SeedPortfolioStateError(...)` |

The audit cited only #1. **#2 is the harder one**: it is a *runtime* raise on the request-build
path, so patching preflight alone would let a campaign start and then die inside the scheduler.

Both compare only the **last `/`-segment**, so `openai/gpt-5.6-sol` and `gpt-5.6-sol` both pass;
a DeepSeek id (`loreley-openai-compatible/deepseek-v4-pro`) fails both.

## Minimal change

Make the pinned contract a setting, defaulting to today's literal so **no existing behaviour or
test changes**. 15 lines of diff, no new module, no behaviour change unless the env var is set.

```diff
--- a/loreley/config.py
+++ b/loreley/config.py
@@ -425,6 +425,10 @@ class Settings(BaseSettings):
     worker_seed_portfolio_model: str = Field(
         default="openai/gpt-5.6-sol",
         alias="WORKER_SEED_PORTFOLIO_MODEL",
     )
+    worker_seed_portfolio_model_contract: str = Field(
+        default="gpt-5.6-sol",
+        alias="WORKER_SEED_PORTFOLIO_MODEL_CONTRACT",
+    )
     worker_seed_portfolio_reasoning_effort: Literal[
         "low", "medium", "high", "xhigh", "max"
     ] = Field(
@@ -1196,6 +1200,9 @@ class Settings(BaseSettings):
         "worker_seed_portfolio_model": settings.worker_seed_portfolio_model,
+        "worker_seed_portfolio_model_contract": (
+            settings.worker_seed_portfolio_model_contract
+        ),
         "worker_seed_portfolio_reasoning_effort": (
             settings.worker_seed_portfolio_reasoning_effort
         ),

--- a/loreley/preflight.py
+++ b/loreley/preflight.py
@@ -394,13 +394,16 @@ def check_seed_portfolio_planner(settings: Settings) -> list[CheckResult]:
             )
         ]
-    if model.rsplit("/", 1)[-1] != "gpt-5.6-sol":
+    contract_model = str(
+        settings.worker_seed_portfolio_model_contract or "gpt-5.6-sol"
+    ).strip()
+    if model.rsplit("/", 1)[-1] != contract_model:
         return [
             CheckResult(
                 "seed_portfolio_planner",
                 "fail",
-                "initial seed portfolio contract is pinned to gpt-5.6-sol "
+                f"initial seed portfolio contract is pinned to {contract_model} "
                 f"(configured={model!r})",
             )
         ]

--- a/loreley/scheduler/seed_portfolios.py
+++ b/loreley/scheduler/seed_portfolios.py
@@ -144,10 +144,13 @@ class SeedPortfolioPlanner:
     ) -> SeedPortfolioPlanningRequest:
         route = dict(resolve_effective_routes(self.settings)["seed_portfolio"])
         model = str(route.get("model") or "").strip()
-        if model.rsplit("/", 1)[-1] != "gpt-5.6-sol":
+        contract_model = str(
+            self.settings.worker_seed_portfolio_model_contract or "gpt-5.6-sol"
+        ).strip()
+        if model.rsplit("/", 1)[-1] != contract_model:
             raise SeedPortfolioStateError(
-                "the initial seed portfolio contract is pinned to gpt-5.6-sol "
+                f"the initial seed portfolio contract is pinned to {contract_model} "
                 f"(configured={model!r})"
             )
```

Enable with:

```bash
WORKER_SEED_PORTFOLIO_MODEL=loreley-openai-compatible/deepseek-v4-pro \
WORKER_SEED_PORTFOLIO_MODEL_CONTRACT=deepseek-v4-pro
```

## Why this shape and not another

* **Default is unchanged**, so `tests/test_preflight_campaign_program.py:80`
  (`assert "gpt-5.6-sol" in results[0].details`) still passes by construction, and every
  existing test at `tests/core/worker/test_agent_backends.py:1810`,
  `tests/core/test_seed_portfolio.py:129`, `tests/scheduler/test_seed_portfolios.py:53`
  keeps working.
* The settings-dump at `config.py:1191-1206` feeds the request fingerprint, so the contract
  model must be added there too (done above) — otherwise two different contract models would
  fingerprint identically and a restart could silently reuse a mismatched artifact.
* Not used: weakening the check to "warn". The two call sites are a *contract* (the paper's
  seed-portfolio treatment is validated against a specific planner model), so silently
  admitting any id would falsify the treatment record. An explicit env var keeps the
  deviation visible in config and in the fingerprint.
* Not used: a `Literal[...]` allowlist. The correct id is only known at deploy time; a
  `str` + explicit env var is the smaller, more honest change.

## Residual risk to state in the study record

Admitting a DeepSeek planner changes the seed-portfolio treatment's model. Any campaign run
this way is **not** comparable to the `gpt-5.6-sol` baseline without saying so explicitly in
the report — this patch removes a *technical* blocker, it does not establish equivalence.
