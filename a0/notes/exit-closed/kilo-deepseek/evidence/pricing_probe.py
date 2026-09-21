"""Run Loreley's own pricing path for a DeepSeek kilo_cli usage event.

Question: does LLM_USAGE_PRICING_JSON price a DeepSeek kilo event, or does the
kilo_cli branch in price_usage_event() short-circuit before the table is read?
"""
from decimal import Decimal
import json

from loreley.core.usage.pricing import price_usage_event, load_pricing_table, match_price_rule
from loreley.core.usage.events import LLMUsageEventPayload
from loreley.config import Settings

DEEPSEEK_ENTRY = {
    "version": "deepseek-probe",
    "prices": [
        {
            "provider": "loreley-openai-compatible",
            "model": "deepseek-v4-pro",
            "api_surface": "kilo_run",
            "input_usd_per_1m": "0.28",
            "cached_input_usd_per_1m": "0.028",
            "output_usd_per_1m": "0.42",
        },
        {
            "provider": "loreley-openai-compatible",
            "model": "deepseek-v4-pro",
            "input_usd_per_1m": "0.28",
            "cached_input_usd_per_1m": "0.028",
            "output_usd_per_1m": "0.42",
        },
    ],
}

settings = Settings(llm_usage_pricing_json=json.dumps(DEEPSEEK_ENTRY))
table = load_pricing_table(settings=settings)
print("pricing table loaded:", table.version, "rules:", len(table.rules))

# Exactly the shape kilo produced: source=kilo_cli, api_surface=kilo_run,
# cost 0 from the DB, non-zero tokens.
event = LLMUsageEventPayload(
    source="kilo_cli",
    phase="coding",
    provider="loreley-openai-compatible",
    model="deepseek-v4-pro",
    api_surface="kilo_run",
    input_tokens=8401,
    cached_input_tokens=25216,
    output_tokens=192,
    reasoning_output_tokens=30,
    total_tokens=11344,
    cost_usd=Decimal("0"),
    cost_source="unpriced",
)
print("\ninput  event:", event.cost_usd, event.cost_source)

priced = price_usage_event(event, settings=settings)
print("after price_usage_event:", priced.cost_usd, "|", priced.cost_source, "|", repr(priced.pricing_version))

rule = match_price_rule(table, event)
print("\nDoes a matching rule EXIST in the table? ->", rule)
print("(if a rule exists but the cost stays None/unpriced, the kilo_cli early")
print(" return is what blocked pricing, not a missing rule)")

# Control: the same counters through a non-kilo source/surface. If this prices
# correctly, the table and the rule are fine and the kilo_cli branch is the
# sole reason the DeepSeek event stays unpriced.
control = LLMUsageEventPayload(
    source="openai_compat",
    phase="coding",
    provider="loreley-openai-compatible",
    model="deepseek-v4-pro",
    api_surface="chat_completions",
    input_tokens=8401,
    cached_input_tokens=25216,
    output_tokens=192,
    total_tokens=11344,
    cost_usd=None,
    cost_source="unpriced",
)
priced_control = price_usage_event(control, settings=settings)
print("\nCONTROL (source=openai_compat):", priced_control.cost_usd, "|",
      priced_control.cost_source, "|", repr(priced_control.pricing_version))
