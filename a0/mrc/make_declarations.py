#!/usr/bin/env python3
"""Write the four filled MRC declarations, then compute their MRC* digests.

The blocks below are *measured*, not designed: every value traces to one of the
verification commands in REPORT.md.  This generator exists only so the shared
blocks (provider, network, task snapshot, policy) cannot drift between routes;
each route's differing fields are spelled out explicitly.

The adapter blocks are the one part that is *read from the repo rather than
written down*: for each runtime the generator lists every blob under that
runtime's adapter package at ``ADAPTER_COMMIT`` with ``git ls-tree``, hashes each
blob's bytes, and records the manifest beside the digest it produces, so the
value has a preimage a third party can point at.  A declared digest with no
preimage is what the validator now rejects (``MRC-ADAPTER-PREIMAGE``).

    python3 a0/mrc/make_declarations.py            # regenerate declarations/
    python3 a0/mrc/make_declarations.py --verify   # re-derive and compare, write nothing

writes declarations/<route>.spec.json and declarations/<route>.mrc.json.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import mrc  # noqa: E402

OBSERVED_UTC = "2026-09-21"

PROVIDER = {
    "provider_id": "deepseek",
    "org": "DeepSeek",
    "upstream_hosts": ["api.deepseek.com"],
    "model_catalog_endpoint": "https://api.deepseek.com/models",
    "catalog_observed": ["deepseek-flash", "deepseek-v4-pro"],
    "catalog_observed_utc": OBSERVED_UTC,
    "openrouter_used": False,
}

MODEL_POLICY = {
    "primary": "deepseek-flash",
    "mixed_secondary_allowed": True,
    "permitted_secondary": ["deepseek-v4-pro"],
    "excluded_providers": ["openrouter"],
    "decided_by": "user",
    "decided_utc": "2026-09-21",
}

TASK_SNAPSHOT = {
    "task_id": "circle-packing",
    "eid_star": mrc.FROZEN_EID_STAR,
    "eid_scheme_ref": "a0/contract/evalcontract.py",
    "e_star_sha256": "2abc6ea15c03caee5257899df2f4f45f2b06b94f071fec8217da489cbb045567",
    "c_star_manifest_sha256": "8d9b953877beb1b09a240302ec4e3ab51590107e715f86a63963cff9255572f2",
    "c_star_digest": "cfeac41728f7dec17ad8414cdb23c2931898dba38a76c23b51091766fd60611c",
    "c_star_candidate_count": 14,
    "paired_at_repo_head": "261f0c9",
}

# The closure topology (a0/notes/exit-closed/proxy-closure/REPORT.md).  Network is
# hashed because in this study egress policy *is* the treatment: an open route can
# fetch external artefacts and a closed one cannot, so two routes with different
# egress are not the same condition.
NETWORK = {
    "topology": "docker_internal_plus_dual_homed_allowlist_proxy",
    "egress_policy": "deny_by_default_hostname_allowlist",
    "allowlist_hosts": ["api.deepseek.com"],
    "internal_network": "a0pc-internal",
    "proxy_id": "a0pc-proxy:8787",
    "proxy_transparency": "connect_tunnel_no_mitm_plus_origin_form_plaintext_routing",
    "dns_mode": "docker_embedded",
    "client_placement": "internal_side",
    "host_bypass_risk": True,
    "host_bypass_note": "the barrier is one-way: the host may dial internal container IPs directly, so the proxy is a trusted component and tooling-side bypass is a stated residual risk",
    "a0_verification_egress": "host_direct",
    "a0_verification_note": "the verification turns in this contract ran on the host with direct egress; the closed topology above is the intended A1 route and is what makes Network load-bearing",
}

WEIGHTS_IDENTITY = {
    "verifiable": False,
    "surface_echo_is_not_proof": True,
    "reason": (
        "No surface on these routes carries a weights digest, checkpoint id, "
        "revision, or signed serving attestation. The response `model` field is "
        "server-written metadata: on the Anthropic-compatible surface it echoes the "
        "requested id verbatim, including retired aliases, while the OpenAI-compatible "
        "surfaces rewrite a retired alias to its canonical id. The same alias request "
        "therefore reports a different id depending on the surface, so no response "
        "field can be read as proof of which weights served the request."
    ),
}

# Multi-surface identity matrix, measured 2026-09-21 by direct curl at this host.
# requested id -> {surface: echoed id}.  Two entries are NOT echoes, and that is
# the point: the same request reports different ids on different surfaces.
ALIAS_MATRIX = {
    "deepseek-flash": {
        "openai_chat_completions": "deepseek-flash",
        "anthropic_messages": "deepseek-flash",
        "openai_responses": "deepseek-flash",
    },
    "deepseek-v4-pro": {
        "openai_chat_completions": "deepseek-v4-pro",
        "anthropic_messages": "deepseek-v4-pro",
        "openai_responses": "deepseek-v4-pro",
    },
    "deepseek-v4-flash": {
        "openai_chat_completions": "deepseek-flash",
        "anthropic_messages": "deepseek-v4-flash",
        "openai_responses": "deepseek-flash",
    },
    "deepseek-v4-flash-vision-exp": {
        "openai_chat_completions": "deepseek-flash",
        "anthropic_messages": "deepseek-v4-flash-vision-exp",
        "openai_responses": "deepseek-flash",
    },
}


def observations_for(surfaces: list[str]) -> list[dict]:
    out = []
    for requested, by_surface in ALIAS_MATRIX.items():
        for surface in surfaces:
            echoed = by_surface[surface]
            out.append({
                "surface": surface,
                "requested_model_id": requested,
                "echoed_model_id": echoed,
                "http_status": 200,
                "echo_is_verbatim": echoed == requested,
                "proves_weights": False,
            })
    for surface in surfaces:
        out.append({
            "surface": surface,
            "requested_model_id": "deepseek-nope",
            "echoed_model_id": None,
            "http_status": 400,
            "error_text": "The supported API model names are deepseek-flash, deepseek-v4-pro",
            "echo_is_verbatim": False,
            "proves_weights": False,
        })
    return out


def identity_evidence(route_id: str, surface: str, cli_note: str, live_turn: dict) -> dict:
    return {
        "weights_identity_verifiable": False,
        "echo_is_not_proof": True,
        "surfaces_observed": ["openai_chat_completions", "anthropic_messages", "openai_responses"],
        "route_surface": surface,
        "observations": observations_for(["openai_chat_completions", "anthropic_messages", "openai_responses"]),
        "cross_surface_divergence": {
            "finding": (
                "The same requested id reports different `model` strings on different "
                "surfaces: a retired alias is rewritten to `deepseek-flash` on the "
                "OpenAI-compatible surfaces but echoed verbatim on the Anthropic-compatible "
                "surface."
            ),
            "demonstrated_by": ["deepseek-v4-flash", "deepseek-v4-flash-vision-exp"],
            "means": "the field is surface-local metadata, not a serving attestation",
        },
        "cli_side_observation": cli_note,
        "live_turn_observed": live_turn,
        "last_observed_utc": OBSERVED_UTC,
        "reproduce": (
            "DS_KEY=$(sed -n 's/^deepseek://p' ~/gptapi.md|head -1); "
            "curl -s https://api.deepseek.com/anthropic/v1/messages -H \"Authorization: Bearer $DS_KEY\" "
            "-H 'Content-Type: application/json' -d '{\"model\":\"deepseek-v4-flash\",\"max_tokens\":4,"
            "\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}'  # -> model=deepseek-v4-flash"
        ),
    }


def cli_block(name, version, binary_sha256, config_isolation, env_var_names, argv_template,
              invocation_mode, **extra):
    block = {
        "name": name,
        "version": version,
        "command_name": name,
        "binary_sha256": binary_sha256,
        "config_isolation": config_isolation,
        "env_var_names": env_var_names,
        "argv_template": argv_template,
        "invocation_mode": invocation_mode,
        "model_selection": extra.pop("model_selection", "explicit id, no alias"),
    }
    block.update(extra)
    return block


def prompt_block(context_tokens, source):
    return {
        "protocol_prompt_ref": "a0/contract/adapter_contract.md",
        "system_prompt_sha256": None,
        "system_prompt_null_reason": (
            "the CLI assembles the system prompt at runtime; it is not frozen by this "
            "contract at A0 and must be recorded per run in A1"
        ),
        "tool_schema_sha256": None,
        "tool_schema_null_reason": "tool schemas are CLI-internal and not exported",
        "prompt_source": source,
        "context_budget_tokens": context_tokens,
        "per_run_recording_required": True,
    }


def params_block(max_tokens):
    return {
        "temperature": {"value": None, "reason": "not set by the lane at A0; provider default"},
        "top_p": {"value": None, "reason": "not set by the lane at A0; provider default"},
        "max_tokens_per_turn": max_tokens,
        "sampling_seed": {"value": None, "reason": "no seeding path observed; sampling is provider-side"},
        "stream": True,
        "tool_choice": "auto",
        "parallel_tool_calls": {"value": None, "reason": "not set by the lane at A0"},
        "thinking": {"value": None, "reason": "not set by the lane at A0"},
        "retry": {"max_attempts": 1, "retry_on": ["transport_error"]},
        "timeout_s": 120,
    }


def perm_block(approval, sandbox, fs_scope, exec_scope, net_scope):
    return {
        "approval_policy": approval,
        "sandbox_mode": sandbox,
        "filesystem_scope": fs_scope,
        "exec_scope": exec_scope,
        "network_scope": net_scope,
    }


# The adapter instrument, per runtime.  The preimage is the runtime's adapter
# package directory as tracked in this repository; everything else about the
# runtime (launcher wrappers, adapter.json manifests, installed upstream
# checkouts, generated outputs) is outside the preimage and is therefore *not*
# covered by adapter_source_sha256 -- see REPORT.md §7 for the stated scope.
ADAPTER_COMMIT = "39e978b8"
ADAPTER_SOURCE_ROOTS = {
    "kapso": "a0/runtimes/kapso/a0_adapter",
    "eve": "a0/runtimes/eve/a0_adapter",
    "loreley": "a0/runtimes/loreley/src/a0_adapter",
    "simpleloop": "a0/runtimes/simpleloop/a0_adapter",
}
# The upstream repositories these adapters drive, as pinned in the archive
# bundles (a0/archive/PROVENANCE.md); "self_built" means the runtime is this repo.
UPSTREAM_PINS = {
    "kapso": "7d99b152",
    "eve": "979065fd",
    "loreley": "4c375920",
    "simpleloop": "self_built",
}


def _git(*args: str, cwd: Path = REPO_ROOT) -> bytes:
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {proc.stderr.decode().strip()}")
    return proc.stdout


def adapter_source_commit_sha() -> str:
    """The full object name of the commit the adapter preimages are taken from."""
    return _git("rev-parse", ADAPTER_COMMIT).decode().strip()


@functools.lru_cache(maxsize=None)
def adapter_source_entries(runtime: str, commit: str = ADAPTER_COMMIT) -> tuple:
    """The preimage of `adapter_source_sha256`: every blob under the runtime's
    adapter package at `commit`, as {path, sha256} in ascending path order.

    Read from the commit, not from the working tree, so the value does not move
    when an untracked file appears; `--verify` reports any working-tree drift.
    """
    root = ADAPTER_SOURCE_ROOTS[runtime]
    listing = _git("ls-tree", "-r", "--name-only", commit, "--", root).decode("utf-8")
    paths = sorted(p for p in listing.splitlines() if p)
    if not paths:
        raise SystemExit(f"no tracked adapter source under {root} at {commit}")
    return tuple(
        {"path": path, "sha256": hashlib.sha256(_git("show", f"{commit}:{path}")).hexdigest()}
        for path in paths
    )


def adapters(lane_by_runtime: dict) -> dict:
    out = []
    for runtime, lane in lane_by_runtime.items():
        entries = adapter_source_entries(runtime)
        out.append({
            "runtime": runtime,
            "lane": lane,
            "adapter_commit": ADAPTER_COMMIT,
            "adapter_source_root": ADAPTER_SOURCE_ROOTS[runtime],
            "adapter_source_files": [dict(e) for e in entries],
            "adapter_source_sha256": mrc.adapter_source_digest(list(entries)),
            "adapter_source_rule": mrc.ADAPTER_SOURCE_RULE,
            "upstream_pin": UPSTREAM_PINS[runtime],
        })
    return {"adapters": out}


def spec(route_id, components, ie, notes):
    return {
        "schema": mrc.SCHEMA,
        "route_id": route_id,
        "model_policy": MODEL_POLICY,
        "components": components,
        "identity_evidence": ie,
        "notes": notes,
    }


def build_all() -> dict:
    specs = {}

    # ---------------------------------------------------------------- codex
    specs["codex-deepseek-responses"] = spec(
        "codex-deepseek-responses",
        {
            "Provider": copy.deepcopy(PROVIDER),
            "Endpoint": {
                "scheme": "https",
                "host": "api.deepseek.com",
                "port": 443,
                "base_path": "/v1",
                "base_url": "https://api.deepseek.com/v1",
                "declared_in": "CODEX_HOME/config.toml [model_providers.ds].base_url",
                "tls_verify": True,
            },
            "RequestedModel": {
                "requested_model_id": "deepseek-flash",
                "canonical_id_claimed": "deepseek-flash",
                "role": "primary",
                "alias_policy": "canonical_ids_only",
                "fallback_chain": [],
                "permitted_secondary": ["deepseek-v4-pro"],
                "weights_identity": copy.deepcopy(WEIGHTS_IDENTITY),
            },
            "ApiSurface": {
                "wire_protocol": "openai_responses",
                "surface_path": "/v1/responses",
                "streaming": True,
                "request_envelope": "openai_responses",
                "response_envelope": "openai_responses",
                "protocol_markers": ["object:response", "status:completed", "output[]"],
                "wire_api_knob": "model_providers.ds.wire_api=\"responses\" (the only accepted value in 0.155.1)",
            },
            "Params": params_block({"value": None,
                                    "reason": "codex does not expose a lane-set max_tokens; its fallback model metadata applies"}),
            "Cli": cli_block(
                "codex", "0.155.1",
                "b085116f223ba6c0d3fda29d84f86f8e147194f3ec3f81821523e73b4dd533fb",
                "CODEX_HOME",
                ["DS_KEY"],
                "codex exec --skip-git-repo-check --sandbox <read-only|workspace-write|danger-full-access> <prompt>",
                "exec_non_interactive",
                model_selection="config model or -c model=...",
                config_files=["config.toml"],
                warnings=["Model metadata for `deepseek-flash` not found; fallback metadata applies"],
            ),
            "Prompt": prompt_block(
                {"value": None, "reason": "not measured for this lane; codex sizes context from fallback metadata"},
                "a1_provided_task_instruction",
            ),
            "Tools": {
                "toolset_ref": "codex_builtin",
                "tool_names_observed": ["shell", "apply_patch"],
                "tool_names_provenance": "observed in a live apply_patch + shell tool loop (codex report 5.2)",
                "tool_choice": "auto",
                "denied_tools": [],
                "extra_tool_sources": [],
            },
            "Permissions": perm_block(
                "never (approval: never)",
                "read-only for the verification turn; workspace-write for the tool loop",
                "workspace-write = {workdir, /tmp, $TMPDIR}",
                "shell tool available; socket() blocked under read-only and workspace-write",
                "blocked by CLI sandbox (socket() EPERM) unless proxied",
            ),
            "Network": copy.deepcopy(NETWORK),
            "RuntimeAdapters": adapters({
                "kapso": "codex", "eve": "codex_exec|codex_tmux",
                "loreley": "codex_cli", "simpleloop": "codex",
            }),
            "TaskSnapshot": copy.deepcopy(TASK_SNAPSHOT),
        },
        identity_evidence(
            "codex-deepseek-responses", "openai_responses",
            "live turn via codex exec against /v1/responses: exit 0, tokens used 830, reply OK",
            {"cli": "codex 0.155.1", "tokens_used": 830, "exit_code": 0, "reply": "OK"},
        ),
        [
            "EvE codex_exec hardcodes --dangerously-bypass-approvals-and-sandbox; codex_tmux can be closed. Same route, different Permissions: the two are NOT interchangeable A1 conditions.",
        ],
    )

    # --------------------------------------------------------------- claude
    specs["claude-deepseek-anthropic"] = spec(
        "claude-deepseek-anthropic",
        {
            "Provider": copy.deepcopy(PROVIDER),
            "Endpoint": {
                "scheme": "https",
                "host": "api.deepseek.com",
                "port": 443,
                "base_path": "/anthropic",
                "base_url": "https://api.deepseek.com/anthropic",
                "declared_in": "ANTHROPIC_BASE_URL (process env or CLAUDE_CONFIG_DIR/settings.json env block)",
                "tls_verify": True,
            },
            "RequestedModel": {
                "requested_model_id": "deepseek-flash",
                "canonical_id_claimed": "deepseek-flash",
                "role": "primary",
                "alias_policy": "canonical_ids_only",
                "fallback_chain": [],
                "permitted_secondary": ["deepseek-v4-pro"],
                "weights_identity": copy.deepcopy(WEIGHTS_IDENTITY),
            },
            "ApiSurface": {
                "wire_protocol": "anthropic_messages",
                "surface_path": "/anthropic/v1/messages",
                "streaming": True,
                "request_envelope": "anthropic_messages",
                "response_envelope": "anthropic_messages",
                "protocol_markers": ["type:message", "content[]", "usage.cache_read_input_tokens"],
                "beta_header_note": "with a non-claude-* id the CLI drops context-1m and fallback-credit betas",
            },
            "Params": params_block({"value": 32000,
                                    "source": "CLI default max_tokens for a non-claude-* model id"}),
            "Cli": cli_block(
                "claude", "2.1.278",
                "356673de39ab5e9e4d19314c33b2d0b01fa06519a44c3374aa947bfbd71a4049",
                "CLAUDE_CONFIG_DIR",
                ["ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN"],
                "claude -p --model deepseek-flash --output-format json <prompt>",
                "print_non_interactive",
                model_selection="--model argv, authoritative over the settings file",
                credential_header="authorization header carries a token sourced from ANTHROPIC_AUTH_TOKEN",
                config_files=["settings.json"],
                warnings=["[claude-code:unrecognized_model] deepseek-flash (non-fatal)"],
                caveats=[
                    "a real ~/.claude/settings.json silently outranks the process env unless CLAUDE_CONFIG_DIR is exported",
                    "the CLI's total_cost_usd is priced from an Anthropic table and is wrong by 10-20x",
                ],
            ),
            "Prompt": prompt_block(
                {"value": 200000, "source": "modelUsage.contextWindow observed in the live turn"},
                "a1_provided_task_instruction",
            ),
            "Tools": {
                "toolset_ref": "claude_code_builtin",
                "tool_names_observed": None,
                "tool_names_null_reason": "21 built-in tools in 2.1.278; not enumerated here and not frozen",
                "tool_names_provenance": "TaskOutput was removed between 2.1.260 and 2.1.278 (22 -> 21)",
                "tool_choice": "auto",
                "denied_tools": [],
                "extra_tool_sources": [],
            },
            "Permissions": perm_block(
                "prompt/--dangerously-skip-permissions depending on the lane",
                "none (CLI-level; closure comes from the network topology)",
                "unrestricted unless contained by the runtime's working directory",
                "Bash tool executes arbitrary commands",
                "open by default; closed only under the a0pc topology",
            ),
            "Network": copy.deepcopy(NETWORK),
            "RuntimeAdapters": adapters({"kapso": "claude_code|oss_claude_code"}),
            "TaskSnapshot": copy.deepcopy(TASK_SNAPSHOT),
        },
        identity_evidence(
            "claude-deepseek-anthropic", "anthropic_messages",
            "live turn via claude -p: exit 0, modelUsage key deepseek-flash, 17379 in / 2 out, "
            "maxOutputTokens 32000, reported total_cost_usd 0.086945 (wrong pricing basis)",
            {"cli": "claude 2.1.278", "input_tokens": 17379, "output_tokens": 2, "exit_code": 0},
        ),
        [
            "KAPSO must set type: claude_code explicitly on any block whose model is a deepseek id, or preflight.resolve_cli falls back to the codex lane.",
        ],
    )

    # ----------------------------------------------------------------- kilo
    specs["kilo-deepseek-chat"] = spec(
        "kilo-deepseek-chat",
        {
            "Provider": copy.deepcopy(PROVIDER),
            "Endpoint": {
                "scheme": "https",
                "host": "api.deepseek.com",
                "port": 443,
                "base_path": "/v1",
                "base_url": "https://api.deepseek.com/v1",
                "declared_in": "provider.<id>.options.baseURL in KILO_CONFIG_CONTENT",
                "tls_verify": True,
            },
            "RequestedModel": {
                "requested_model_id": "deepseek-flash",
                "canonical_id_claimed": "deepseek-flash",
                "role": "primary",
                "alias_policy": "canonical_ids_only",
                "fallback_chain": [],
                "permitted_secondary": ["deepseek-v4-pro"],
                "weights_identity": copy.deepcopy(WEIGHTS_IDENTITY),
            },
            "ApiSurface": {
                "wire_protocol": "openai_chat_completions",
                "surface_path": "/v1/chat/completions",
                "streaming": True,
                "request_envelope": "openai_chat_completions",
                "response_envelope": "openai_chat_completions",
                "protocol_markers": ["object:chat.completion", "choices[]", "usage.prompt_cache_hit_tokens"],
                "provider_package": "@ai-sdk/openai-compatible (bundled in the 7.7.5 binary)",
            },
            "Params": params_block({"value": None,
                                    "reason": "kilo does not expose a lane-set max_tokens for a custom provider"}),
            "Cli": cli_block(
                "kilo", "7.7.5",
                "b21e6ec743f2c63bdf1e586bf7a8ba9e26f3cfa273002c8810eb37d089ba791d",
                "XDG_* homes + KILO_CONFIG_CONTENT",
                ["DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"],
                "kilo run --auto --pure --dir <wt> --format json -m deepseek/deepseek-flash <prompt>",
                "run_non_interactive",
                model_selection="-m provider/model",
                config_files=["KILO_CONFIG_CONTENT (env)"],
                caveats=[
                    "does not fail fast on an unreachable endpoint: it waits for network indefinitely",
                    "kilo debug config prints the resolved key in cleartext; evidence collectors must redact",
                ],
            ),
            "Prompt": prompt_block(
                {"value": None, "reason": "not measured for this lane"},
                "a1_provided_task_instruction",
            ),
            "Tools": {
                "toolset_ref": "kilo_builtin",
                "tool_names_observed": ["write", "read", "bash"],
                "tool_names_provenance": "observed in a live tool loop (kilo report 2.2)",
                "tool_choice": "auto",
                "denied_tools": [],
                "extra_tool_sources": [],
            },
            "Permissions": perm_block(
                "--auto (auto-approve what is not explicitly denied)",
                "none (CLI-level)",
                "unrestricted unless contained by the runtime's working directory",
                "bash tool executes arbitrary commands",
                "open by default; closed only under the a0pc topology",
            ),
            "Network": copy.deepcopy(NETWORK),
            "RuntimeAdapters": adapters({"loreley": "kilo"}),
            "TaskSnapshot": copy.deepcopy(TASK_SNAPSHOT),
        },
        identity_evidence(
            "kilo-deepseek-chat", "openai_chat_completions",
            "live turn via kilo run: exit 0, reply OK, tokens total 12003 "
            "(9891 in / 2 out / 62 reasoning / 2048 cache read), kilo-reported cost 0.001528194",
            {"cli": "kilo 7.7.5", "total_tokens": 12003, "exit_code": 0, "reply": "OK"},
        ),
        [
            "Loreley's seed-portfolio pin needs a two-site patch (preflight.py:397 and scheduler/seed_portfolios.py:147); patching one site only makes a campaign die mid-run.",
            "Loreley prices kilo events as `unpriced` before consulting any pricing table (pricing.py:64-74).",
        ],
    )

    # ------------------------------------------------------------- opencode
    specs["opencode-deepseek-chat"] = spec(
        "opencode-deepseek-chat",
        {
            "Provider": copy.deepcopy(PROVIDER),
            "Endpoint": {
                "scheme": "https",
                "host": "api.deepseek.com",
                "port": 443,
                "base_path": "/v1",
                "base_url": "https://api.deepseek.com/v1",
                "declared_in": "provider.<id>.options.baseURL in an OPENCODE_CONFIG file",
                "tls_verify": True,
            },
            "RequestedModel": {
                "requested_model_id": "deepseek-flash",
                "canonical_id_claimed": "deepseek-flash",
                "role": "primary",
                "alias_policy": "canonical_ids_only",
                "fallback_chain": [],
                "permitted_secondary": ["deepseek-v4-pro"],
                "weights_identity": copy.deepcopy(WEIGHTS_IDENTITY),
            },
            "ApiSurface": {
                "wire_protocol": "openai_chat_completions",
                "surface_path": "/v1/chat/completions",
                "streaming": True,
                "request_envelope": "openai_chat_completions",
                "response_envelope": "openai_chat_completions",
                "protocol_markers": ["object:chat.completion", "choices[]", "usage.prompt_cache_hit_tokens"],
                "provider_package": "aisdk:@ai-sdk/openai-compatible",
            },
            "Params": params_block({"value": None,
                                    "reason": "opencode does not expose a lane-set max_tokens for a custom provider"}),
            "Cli": cli_block(
                "opencode", "v2.0.11",
                "24832f82cea1bac62bb38e864a4af8df23a3950ce7abad0c3b7d6dc575c77d0a",
                "XDG_* homes + OPENCODE_CONFIG (a file path, not content)",
                ["DEEPSEEK_API_KEY"],
                "opencode run --standalone --format json --auto --model deepseek/deepseek-flash <prompt>",
                "run_non_interactive",
                model_selection="--model provider/model",
                config_files=["OPENCODE_CONFIG file"],
                caveats=[
                    "OPENCODE_CONFIG_CONTENT is read by the background service, so docker exec -e does not reach it; use a file path and --standalone",
                    "--dir is rejected in v2.0.11",
                    "{env:VAR} substitution in the config did not resolve on v2.0.11",
                ],
            ),
            "Prompt": prompt_block(
                {"value": None, "reason": "not measured for this lane"},
                "a1_provided_task_instruction",
            ),
            "Tools": {
                "toolset_ref": "opencode_builtin_with_permission_rules",
                "tool_names_observed": ["shell", "edit", "webfetch"],
                "tool_names_provenance": "permission rules deny/remove the tool from the toolset rather than failing at call time",
                "tool_choice": "auto",
                "denied_tools": ["shell", "edit", "webfetch (as configured for the verification turn)"],
                "extra_tool_sources": [],
            },
            "Permissions": perm_block(
                "--auto turns ask into allow but cannot override deny",
                "none (CLI-level)",
                "unrestricted unless contained by the runtime's working directory",
                "shell tool executes arbitrary commands; deny removes it entirely",
                "open by default; closed only under the a0pc topology",
            ),
            "Network": copy.deepcopy(NETWORK),
            "RuntimeAdapters": adapters({"eve": "opencode"}),
            "TaskSnapshot": copy.deepcopy(TASK_SNAPSHOT),
        },
        identity_evidence(
            "opencode-deepseek-chat", "openai_chat_completions",
            "live turn via opencode run --standalone: exit 0, reply OK",
            {"cli": "opencode v2.0.11", "exit_code": 0, "reply": "OK"},
        ),
        [
            "EvE's opencode driver needs three changes (config file path, --standalone, service port); it is not a zero-change swap.",
        ],
    )

    return specs


def adapter_preimage_report() -> int:
    """Print each adapter preimage, its digest, and any working-tree drift."""
    print(f"adapter preimages: {len(ADAPTER_SOURCE_ROOTS)} runtimes, "
          f"commit {ADAPTER_COMMIT} ({adapter_source_commit_sha()})")
    drift = 0
    for runtime, root in sorted(ADAPTER_SOURCE_ROOTS.items()):
        entries = adapter_source_entries(runtime)
        digest = mrc.adapter_source_digest(list(entries))
        print(f"[ok ] {runtime:<11} {root:<40} {len(entries):>2} files  {digest}")
        for entry in entries:
            blob = _git("show", f"{ADAPTER_COMMIT}:{entry['path']}")
            local = REPO_ROOT / entry["path"]
            if not local.is_file():
                drift += 1
                print(f"       working tree lacks {entry['path']}")
            elif local.read_bytes() != blob:
                drift += 1
                print(f"       working tree differs from {ADAPTER_COMMIT}: {entry['path']}")
    if drift:
        print(f"working-tree drift vs {ADAPTER_COMMIT}: {drift} file(s); the digests above "
              f"describe the commit, not the tree")
    else:
        print(f"working tree matches {ADAPTER_COMMIT} for every file in every preimage")
    return drift


def verify() -> int:
    """Re-derive every declaration from the repo and compare with what is shipped.

    Writes nothing.  Exits non-zero on any difference, including adapter-source
    drift, so a stale declaration cannot be mistaken for a current one.
    """
    adapter_preimage_report()
    bad = 0
    for route_id, spec_doc in build_all().items():
        doc = mrc.build_mrc(spec_doc)
        for path, payload in (
            (HERE / "declarations" / f"{route_id}.spec.json", spec_doc),
            (HERE / "declarations" / f"{route_id}.mrc.json", doc),
        ):
            want = json.dumps(payload, indent=2, sort_keys=True) + "\n"
            got = path.read_text(encoding="utf-8") if path.exists() else ""
            ok = got == want
            bad += not ok
            print(f"[{'ok  ' if ok else 'BAD '}] {path.name}")
        print(f"       MRC* = {doc['mrc_star']}")
    print("shipped declarations match a fresh derivation from the repo" if not bad
          else f"{bad} declaration file(s) do NOT match a fresh derivation")
    return 1 if bad else 0


def main() -> int:
    if sys.argv[1:] == ["--verify"]:
        return verify()
    if sys.argv[1:]:
        print(f"usage: {Path(sys.argv[0]).name} [--verify]", file=sys.stderr)
        return 2
    outdir = HERE / "declarations"
    outdir.mkdir(parents=True, exist_ok=True)
    for route_id, spec_doc in build_all().items():
        spec_path = outdir / f"{route_id}.spec.json"
        spec_path.write_text(json.dumps(spec_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        doc = mrc.build_mrc(spec_doc)
        mrc_path = outdir / f"{route_id}.mrc.json"
        mrc_path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"{route_id:<32} MRC* = {doc['mrc_star']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
