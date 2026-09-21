"""Construct every declared lane in-process (NO model call, NO file edits).

For each agent in agents.yaml: try to import the adapter module, then build it
with a minimal CodingAgentConfig and report the exception type/message.
Nothing here calls generate_code(), so no API budget is spent.
"""
import importlib, traceback
from kapso.core.agent_manifest import load_agent_manifest
from kapso.execution.coding_agents.base import CodingAgentConfig
from kapso.execution.coding_agents.factory import CodingAgentFactory

manifest = load_agent_manifest()
print("default_agent =", manifest["default_agent"])
for name, info in manifest["agents"].items():
    mod_path, cls_name = info["adapter_module"], info["adapter_class"]
    row = {"lane": name, "module": mod_path}
    try:
        mod = importlib.import_module(mod_path)
        cls = getattr(mod, cls_name)
        row["import"] = "ok"
    except Exception as e:
        print(f"{name:18s} import   FAIL  {type(e).__name__}: {e}")
        continue
    spec = dict(info.get("agent_specific") or {})
    if name == "oss_claude_code":
        spec["base_url"] = "https://example.invalid/inference"
        spec["auth_token_env"] = "A0_PROBE_TOKEN"
    cfg = CodingAgentConfig(
        agent_type=name,
        model=info.get("default_model", "m"),
        debug_model=info.get("default_debug_model", "m"),
        workspace="",
        agent_specific=spec,
    )
    try:
        obj = cls(cfg)
        caps = obj.get_capabilities()
        print(f"{name:18s} build    OK    capabilities={caps}")
    except Exception as e:
        print(f"{name:18s} build    FAIL  {type(e).__name__}: {str(e)[:160]}")
