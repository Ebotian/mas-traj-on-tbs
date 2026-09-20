#!/usr/bin/env python3
"""Execute KAPSO's real coding-agent adapters to dump the argv each lane uses.

Run with the pinned KAPSO checkout on PYTHONPATH (see run_probes.sh):

    PYTHONPATH=/home/ebt/kapso_ck/kapso/src <venv>/bin/python seam_kapso_argv.py

No model call and no campaign is started: `_exec_command` (codex) and
`_build_command` (claude) are pure functions of the adapter's
`agent_specific` spec, which is exactly what `agents.yaml` ships.

What it establishes:

1. The codex lane's default is `--sandbox danger-full-access` plus `--search`
   (live web search), i.e. both a Bash side door and a web-search front door
   are open by default.
2. The claude lane's default is `--dangerously-skip-permissions` with `Bash`
   in its allowed tool list, and the adapter itself reports
   `capabilities()["sandbox"] == False`.
3. A ONE-KEY code change (`agent_specific.sandbox = "workspace-write"`,
   `web_search: False`) does produce a closed codex-lane argv -- so the
   protocol's claim "KAPSO has no lane-level sandbox parameter" is not
   accurate at the adapter level; it is KAPSO's *strategy* that never passes
   one (see evidence in VERDICTS.md).
"""

from __future__ import annotations

import json
from pathlib import Path

from kapso.execution.coding_agents.adapters.claude_code_agent import ClaudeCodeCodingAgent
from kapso.execution.coding_agents.adapters.codex_agent import CodexCodingAgent
from kapso.execution.coding_agents.base import CodingAgentConfig

KAPSO_ROOT = Path("/home/ebt/kapso_ck/kapso")


def agents_yaml_specs() -> dict[str, dict]:
    """Read the shipped per-lane defaults straight out of agents.yaml."""
    text = (KAPSO_ROOT / "src/kapso/execution/coding_agents/agents.yaml").read_text(
        encoding="utf-8"
    )
    import yaml  # KAPSO depends on PyYAML

    doc = yaml.safe_load(text) or {}
    lanes = doc.get("agents", doc)
    return {
        lane: body
        for lane, body in lanes.items()
        if isinstance(body, dict) and "agent_specific" in body
    }


def main() -> int:
    print("### KAPSO seam probe: argv built by KAPSO's own adapters")

    specs = agents_yaml_specs()
    print("\n--- shipped agent_specific defaults from agents.yaml ---")
    for lane in ("codex", "claude_code"):
        spec = specs.get(lane, {})
        specific = spec.get("agent_specific", {})
        print(f"{lane}: agent_specific={json.dumps(specific, sort_keys=True)}")

    print("\n--- codex lane, as KAPSO ships it ---")
    codex_spec = specs.get("codex", {}).get("agent_specific", {})
    cfg = CodingAgentConfig(
        agent_type="codex",
        model=codex_spec.get("default_model", "gpt-5.6-sol"),
        debug_model=codex_spec.get("default_debug_model", "gpt-5.6-sol"),
        agent_specific={
            k: v
            for k, v in codex_spec.items()
            if k in {"effort", "timeout", "sandbox", "web_search"}
        }
        | {"web_search": True},  # the implementation/ideation lanes set this knob
    )
    codex_agent = CodexCodingAgent(cfg)
    print(f"codex lane sandbox={codex_agent._sandbox!r} web_search={codex_agent._web_search!r}")
    print(f"codex lane argv (fresh session): {codex_agent._exec_command('gpt-5.6-sol', '/tmp/last')}")

    print("\n--- codex lane after a one-key code change (hypothetical closure) ---")
    closed_cfg = CodingAgentConfig(
        agent_type="codex",
        model="gpt-5.6-sol",
        debug_model="gpt-5.6-sol",
        agent_specific={"effort": "xhigh", "timeout": 3600,
                        "sandbox": "workspace-write", "web_search": False},
    )
    closed_agent = CodexCodingAgent(closed_cfg)
    print(f"codex lane sandbox={closed_agent._sandbox!r} web_search={closed_agent._web_search!r}")
    print(f"codex lane argv: {closed_agent._exec_command('gpt-5.6-sol', '/tmp/last')}")

    print("\n--- claude lane, as KAPSO ships it ---")
    claude_spec = specs.get("claude_code", {}).get("agent_specific", {})
    claude_cfg = CodingAgentConfig(
        agent_type="claude_code",
        model=claude_spec.get("default_model", "claude-opus-4-5"),
        debug_model=claude_spec.get("default_debug_model", "claude-opus-4-5"),
        agent_specific={"allowed_tools": claude_spec.get("allowed_tools", ["Bash"])},
    )
    try:
        claude_agent = ClaudeCodeCodingAgent(claude_cfg)
    except Exception as exc:  # noqa: BLE001 - some versions require more config
        print(f"claude adapter construction failed: {type(exc).__name__}: {exc}")
        return 1
    argv = claude_agent._build_command("claude-opus-4-5")
    print(f"claude lane argv: {argv}")
    print(f"claude lane allowed tools: {claude_agent._allowed_tools}")
    print(f"claude lane disallowed tools: {claude_agent._disallowed_tools}")
    print(f"claude lane capabilities: {claude_agent.get_capabilities()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
