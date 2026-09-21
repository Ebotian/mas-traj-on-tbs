# MRC* — execution report and evidence

Owner: `a0/mrc/**`. Measured 2026-09-21 (CST, UTC+8) on this host.
Every claim is tagged **verified by running it**, **read from source**, or **inferred**. The key was
read from `~/gptapi.md` into an env var inside the same shell command that used it; no artefact
under this directory contains it (`grep -rF` on the key returns nothing).

Companion documents: `SPEC.md` (the schema and its justification), `A1_ATTRIBUTION.md` (the
per-iteration record A1 owes), `mrc_schema.json`, `frozen_routes.json`.

---

## 1. What was produced

| Path | What it is |
|---|---|
| `mrc_schema.json` | JSON Schema (draft 2020-12) for a declaration, house style |
| `mrc.py` | canonical hashing + validator + CLI (`compute` / `recompute` / `validate`) |
| `frozen_routes.json` | the four routes with their frozen provider/endpoint/surface/model |
| `make_declarations.py` | writes the four `.spec.json` and `.mrc.json` files |
| `declarations/*.spec.json` | the human-authored inputs |
| `declarations/*.mrc.json` | the frozen declarations (12 component digests + MRC*) |
| `mrc_selftest.py` | 39 checks; independent re-implementation; 12 negative cases |
| `fixtures/negative/*.mrc.json` | the mutated declarations the validator must reject |
| `SPEC.md` | schema, field-by-field justification, the A1 per-iteration requirement |

Frozen MRC*, recomputed 2026-09-21 after the adapter path-independence fix moved the adapter
digests (§7) — the values first reported here covered an `adapter_source_sha256` that had no
preimage, so they were superseded rather than patched:

```
codex-deepseek-responses     9becc39c0fea3db8ff456b7d68d42198523a43074249d93faad4a8a7c06cfd01
claude-deepseek-anthropic    dfb9316f60d44d2c3363d755f777f65e0b0a6938fa864518ad077bcc2aa1f78c
kilo-deepseek-chat           6688c0d42b0c70605690bb55539a0d6b86d6dc5f7b85c6b2686dab18edf68f24
opencode-deepseek-chat       d04a41595fac1789ec73874826c449b39a353b7b4572fe8c32a5b61d6edce06d
```

---

## 2. The four lanes, verified live against the real configuration

Each route was driven **end to end** with a minimal real turn — not merely configured — so that the
declaration describes a route that demonstrably worked. Versions and binary digests were taken from
the installed binaries:

```
claude   2.1.278 (Claude Code)   /usr/bin/claude    sha256 356673de39ab5e9e4d19314c33b2d0b01fa06519a44c3374aa947bfbd71a4049
codex    codex-cli 0.155.1       /usr/bin/codex     sha256 b085116f223ba6c0d3fda29d84f86f8e147194f3ec3f81821523e73b4dd533fb
opencode v2.0.11                 /usr/bin/opencode  sha256 24832f82cea1bac62bb38e864a4af8df23a3950ce7abad0c3b7d6dc575c77d0a
kilo     7.7.5                   /usr/bin/kilo      sha256 b21e6ec743f2c63bdf1e586bf7a8ba9e26f3cfa273002c8810eb37d089ba791d
```

### codex → DeepSeek `/v1`, `wire_api="responses"` **[verified by running it]**

Isolated `CODEX_HOME`, the recipe from the codex re-verification:

```bash
DS_KEY=$(sed -n 's/^deepseek://p' ~/gptapi.md|head -1) \
CODEX_HOME=/tmp/mrc-verify/codex-home timeout 120 codex exec \
  --skip-git-repo-check --sandbox read-only "Reply with exactly the two characters: OK"
```

```
provider: ds
sandbox: read-only
reasoning effort: none
session id: 01a0c2cf-7f63-7ff3-819c-e4a68ea78331
warning: Model metadata for `deepseek-flash` not found. Defaulting to fallback metadata; ...
codex
OK
tokens used
830
```

Exit 0. The config block (`model = "deepseek-flash"`, `[model_providers.ds] base_url =
"https://api.deepseek.com/v1"`, `env_key = "DS_KEY"`, `wire_api = "responses"`) also loads clean
under `codex debug models`. The fallback-metadata warning is real and is recorded in the
declaration's `warnings`.

### claude → DeepSeek `/anthropic`, `ANTHROPIC_AUTH_TOKEN` **[verified by running it]**

Fresh empty `CLAUDE_CONFIG_DIR` so the process environment is authoritative (the global
`~/.claude/settings.json` is known to outrank the environment otherwise):

```bash
DS_KEY=$(sed -n 's/^deepseek://p' ~/gptapi.md|head -1) \
CLAUDE_CONFIG_DIR=/tmp/mrc-verify/claude-home \
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic ANTHROPIC_AUTH_TOKEN="$DS_KEY" \
timeout 180 claude -p --model deepseek-flash --output-format json "Reply with exactly the two characters: OK"
```

```
[claude-code:unrecognized_model] {"model":"deepseek-flash","query_source":"sdk"}
{"duration_api_ms":885,"stop_reason":"end_turn",
 "total_cost_usd":0.086945,
 "usage":{"input_tokens":17379,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":2,...},
 "modelUsage":{"deepseek-flash":{"inputTokens":17379,"outputTokens":2,"costUSD":0.086945,
                                 "contextWindow":200000,"maxOutputTokens":32000,...}}}
```

Exit 0, `modelUsage` keyed `deepseek-flash`. Two things the declaration records as caveats: the CLI
spends ~17.2k input tokens before the task text, and its `total_cost_usd` is priced from an
Anthropic table it does not have an entry for (real spend is a small fraction of $0.087).

### kilo → DeepSeek (OpenAI-compatible) **[verified by running it]**

```bash
kilo debug config        # free: resolves the provider, key shown as <REDACTED> by me
kilo run --auto --pure --dir /tmp/mrc-verify/kilo-wt --format json --title mrc-kilo \
     -m deepseek/deepseek-flash "Reply with exactly the two characters: OK"
```

`debug config` resolves `provider.deepseek.options.baseURL = "https://api.deepseek.com/v1"` with
`npm: "@ai-sdk/openai-compatible"` and `apiKey: "{env:DEEPSEEK_API_KEY}"`. The live turn:

```
{"type":"text",...,"text":"OK", ...}
{"type":"step-finish",...,"cost":0.001528194,
 "tokens":{"total":12003,"input":9891,"output":2,"reasoning":62,"cache":{"read":2048,"write":0}}}
```

Exit 0.

### opencode → DeepSeek (OpenAI-compatible) **[verified by running it]**

`OPENCODE_CONFIG` pointing at a file (not `OPENCODE_CONFIG_CONTENT`, which the background service
does not see) and `--standalone`:

```bash
opencode debug config
opencode run --standalone --format json --auto --model deepseek/deepseek-flash "Reply with exactly the two characters: OK"
```

`debug config` resolves `deepseek` → `package: "aisdk:@ai-sdk/openai-compatible"`, `settings.baseURL
= "https://api.deepseek.com/v1"`, model `{providerID: deepseek, model: deepseek-flash}`. The live
turn returned `{"type":"text",...,"text":"OK"}` with exit 0.

---

## 3. The identity measurement (the review's point 7) **[verified by running it]**

Direct `curl` against the three surfaces, requesting four ids plus a bogus one. `served` = the id
the response reports:

| requested | `/v1/chat/completions` | `/anthropic/v1/messages` | `/v1/responses` |
|---|---|---|---|
| `deepseek-flash` | deepseek-flash | deepseek-flash | deepseek-flash |
| `deepseek-v4-pro` | deepseek-v4-pro | deepseek-v4-pro | deepseek-v4-pro |
| `deepseek-v4-flash` | **deepseek-flash** | **deepseek-v4-flash** | **deepseek-flash** |
| `deepseek-v4-flash-vision-exp` | **deepseek-flash** | **deepseek-v4-flash-vision-exp** | **deepseek-flash** |
| `deepseek-nope` | 400 | 400 | 400 |

`deepseek-nope` → `400 {"error":{"message":"The supported API model names are deepseek-flash,
deepseek-v4-pro, but you passed deepseek-nope.",...}}`, so the endpoint is not a permissive
catch-all.

**The finding.** For a canonical id every surface echoes the request. For a *retired alias* the
surfaces disagree: the OpenAI-shaped surfaces canonicalize, the Anthropic-shaped one echoes. The
same request therefore produces two different "served" strings, which proves the field is
surface-local metadata and not an attestation. No surface anywhere returns a weights digest,
checkpoint id, or revision. This is frozen as `weights_identity.verifiable: false` **inside** the
digest, so "we do not claim weights" cannot be edited away without changing MRC*.

**Correction to `a0/STATUS.md` §7.** That section says the Anthropic surface reported
`deepseek-v4-flash` for a *requested* `deepseek-flash`. It does not reproduce: the request
`deepseek-flash` is reported as `deepseek-flash` on the Anthropic surface. `deepseek-v4-flash`
appears only when the *alias* is requested, and then it is the Anthropic surface (not the OpenAI
one) that echoes it. The review's conclusion is unaffected and in fact sharpened. `STATUS.md` is the
coordinator's file and was not edited.

---

## 4. Validator output **[verified by running it]**

Positive — all four declarations:

```
$ python3 mrc.py validate --mrc-file declarations/codex-deepseek-responses.mrc.json --frozen frozen_routes.json
valid: route=codex-deepseek-responses MRC* = 9becc39c0fea3db8ff456b7d68d42198523a43074249d93faad4a8a7c06cfd01
… (claude, kilo, opencode likewise) …
```

Negative — the required drift cases and others, each failing with a specific code (every line below
is the real output of the command above it):

```
$ python3 mrc.py validate --mrc-file fixtures/negative/neg_endpoint_drift.mrc.json --frozen frozen_routes.json
FAIL MRC-ENDPOINT-DRIFT: codex-deepseek-responses: got 'https://openrouter.ai/api/v1', frozen value is 'https://api.deepseek.com/v1'
exit=1

$ python3 mrc.py validate --mrc-file fixtures/negative/neg_model_drift.mrc.json --frozen frozen_routes.json
FAIL MRC-MODEL-DRIFT: codex-deepseek-responses: got 'deepseek-v4-flash', frozen value is 'deepseek-flash'
exit=1

$ python3 mrc.py validate --mrc-file fixtures/negative/neg_echo_as_proof.mrc.json --frozen frozen_routes.json
FAIL MRC-IDENTITY-WEIGHTS-CLAIM: weights_identity_verifiable must be exactly false; no surface here attests weights
FAIL MRC-IDENTITY-ECHO-AS-PROOF: observations[0] treats an echo as weight proof
exit=1

$ python3 mrc.py validate --mrc-file fixtures/negative/neg_abs_path_leak.mrc.json --frozen frozen_routes.json
FAIL MRC-DIGEST-MISMATCH: Cli: recorded=e9ae79871ac96f382634d138a91156a0867c7e3d88c48653e7b25b9ea999d3f5 recomputed=61d88909ec701e006bd7687e8bf6f0afe2a2081d4ff39ff1d0684032980df933
FAIL MRC-DIGEST-MISMATCH: MRC*: recorded=9becc39c0fea3db8ff456b7d68d42198523a43074249d93faad4a8a7c06cfd01 recomputed=c26135ea90610342f0b1ae32cf60de4153459ddec1b978f2a7e93d32c133cf4b
FAIL MRC-HYGIENE: Cli.config_files[0]: absolute path leaked into hashed input: '/home/ebt/rsi-dev/a0/runtimes/kapso/config'
exit=1

$ python3 mrc.py validate --mrc-file fixtures/negative/neg_eid_drift.mrc.json --frozen frozen_routes.json
FAIL MRC-EID-DRIFT: TaskSnapshot.eid_star is 'fac50fc400000000000000000000000000000000000000000000000000000000', expected '664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328'
exit=1

$ python3 mrc.py validate --mrc-file fixtures/negative/neg_adapter_digest_without_preimage.mrc.json --frozen frozen_routes.json
FAIL MRC-ADAPTER-PREIMAGE: adapters[0] (kapso): adapter_source_sha256 declared with no usable preimage: adapter_source_files must be a list of {path, sha256} entries
exit=1

$ python3 mrc.py validate --mrc-file fixtures/negative/neg_adapter_digest_off_preimage.mrc.json --frozen frozen_routes.json
FAIL MRC-ADAPTER-DIGEST: adapters[0] (kapso): adapter_source_sha256=0000000000000000000000000000000000000000000000000000000000000000 is not the digest of the listed preimage (06df3969358eff8542b43b6ad09319c33353f6af615f23f1c6a61e5fdbebcf82)
exit=1
```

(The two digest lines in `neg_abs_path_leak` are the point of that fixture's `rehash=True` branch:
the edit is caught once as a naive edit with stale digests *and* once as the specific hygiene
violation. `neg_adapter_digest_without_preimage` and `neg_adapter_digest_off_preimage` recompute
every digest before validation, so the only failures they show are the adapter ones.)

**What the drift cases do and do not protect.** `Endpoint.base_url`, `RequestedModel.requested_model_id`,
`ApiSurface.surface_path` and `Provider.provider_id` are checked against an **external** registry
(`frozen_routes.json`), so a self-consistent recomputation still fails (`MRC-*-DRIFT`). `Tools` and
`Permissions` are **not** in that registry: they are protected only by the `MRC*` pin. This is
stated here explicitly rather than left implied by a table of "required drift cases", and it is
measured — perturb one component, recompute every digest with `mrc.py compute`, then validate:

```bash
cd /home/ebt/rsi-dev/a0/mrc && python3 - <<'PY'
import copy, json, pathlib, subprocess, sys
base = json.loads(pathlib.Path("declarations/codex-deepseek-responses.spec.json").read_text())
cases = {
 "endpoint": lambda s: s["components"]["Endpoint"].__setitem__("base_url", "https://openrouter.ai/api/v1"),
 "model":    lambda s: s["components"]["RequestedModel"].__setitem__("requested_model_id", "deepseek-v4-pro"),
 "tools":    lambda s: s["components"]["Tools"].__setitem__("tool_choice", "none"),
 "perms":    lambda s: s["components"]["Permissions"].__setitem__("sandbox_mode", "danger-full-access"),
}
for name, fn in cases.items():
    spec = copy.deepcopy(base); fn(spec)
    p = pathlib.Path(f"/tmp/mrc-tp/{name}.spec.json"); p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(spec)); out = f"/tmp/mrc-tp/{name}.mrc.json"
    r = subprocess.run([sys.executable, "mrc.py", "compute", "--spec", str(p), "--out", out],
                       capture_output=True, text=True)
    print(f"--- {name}: {r.stdout.splitlines()[0]}")
    v = subprocess.run([sys.executable, "mrc.py", "validate", "--mrc-file", out,
                        "--frozen", "frozen_routes.json"], capture_output=True, text=True)
    print(v.stdout.rstrip() or "(no stdout)")
    print(f"exit={v.returncode}")
PY
```

Real output of that command:

```
--- endpoint: MRC* = d5c9b929f21820b68ce0ad849486bd6d0f8fdf61122ebb31c1ec8644ab935042
FAIL MRC-ENDPOINT-DRIFT: codex-deepseek-responses: got 'https://openrouter.ai/api/v1', frozen value is 'https://api.deepseek.com/v1'
exit=1
--- model: MRC* = 3b4a220e9d94e759aca59a46d98366dc0afc4aa22edf67a33a816af1d2714e69
FAIL MRC-MODEL-DRIFT: codex-deepseek-responses: got 'deepseek-v4-pro', frozen value is 'deepseek-flash'
exit=1
--- tools: MRC* = 8ee5ce35220045fc4bcf2c79bf29f8d75cffd990f77f6e1dc054d4a1e8927cf1
valid: route=codex-deepseek-responses MRC* = 8ee5ce35220045fc4bcf2c79bf29f8d75cffd990f77f6e1dc054d4a1e8927cf1
exit=0
--- perms: MRC* = a3779b941c457dd8735b78909c9ad52a130afba1243bfeca5c2d34c427adee1a
valid: route=codex-deepseek-responses MRC* = a3779b941c457dd8735b78909c9ad52a130afba1243bfeca5c2d34c427adee1a
exit=0
```

So a tool or permission change is not *semantically* rejected — it is only tamper-evident through the
`MRC*` value, and it therefore only shows up in a run's own record. An A1 arm has to compare its
`mrc_star` against the value recorded in §1 and in `SPEC.md` §4; there is no second line of defence
for tool and permission drift. (A naive edit that leaves the digests stale is caught as
`MRC-DIGEST-MISMATCH`, which is weaker evidence, not this.)

Self-test:

```
$ python3 mrc_selftest.py
… 44 lines …
44/44 checks passed
```

The suite includes an **independent re-implementation** of MRC* (written long-hand in the test,
sharing no helper with `mrc.py`) reproducing all four digests, canonical-form byte-equality with
`a0/contract/evalcontract.py`, an independent re-implementation of the adapter-preimage rule, three
adapter-preimage checks (manifest→digest, rule identity, and preimage-vs-repo), and four positive
controls so the negative suite cannot be passing vacuously.

---

## 5. How a third party re-runs this

```bash
cd /home/ebt/rsi-dev/a0/mrc
python3 mrc_selftest.py                                       # 44/44, no network, no key
python3 make_declarations.py                                  # regenerate declarations
python3 make_declarations.py --verify                         # re-derive and diff; writes nothing
python3 verify_adapter_preimage.py                            # recompute the adapter digests from git
python3 mrc.py validate --mrc-file declarations/<route>.mrc.json --frozen frozen_routes.json
```

To re-measure identity (needs the key, spends a few 4-token calls):

```bash
DS_KEY=$(sed -n 's/^deepseek://p' ~/gptapi.md|head -1)
curl -s https://api.deepseek.com/anthropic/v1/messages -H "Authorization: Bearer $DS_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-v4-flash","max_tokens":4,"messages":[{"role":"user","content":"hi"}]}'
# -> "model":"deepseek-v4-flash"   (echo)
curl -s https://api.deepseek.com/v1/chat/completions -H "Authorization: Bearer $DS_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":4}'
# -> "model":"deepseek-flash"      (canonicalized) -- the divergence
```

---

## 6. What is not established (explicit)

- **Weight-level identity is not verifiable** and is frozen as such. Do not quote MRC* as evidence
  that two arms ran the same weights.
- **Prompts and tool schemas are null** (with reasons). They are the largest unfrozen surface and
  the first thing A1 must record per iteration — see `A1_ATTRIBUTION.md`.
- The **verification turns ran with direct host egress**, whereas the declarations freeze the closed
  `a0pc-*` topology as the intended A1 route (`Network.a0_verification_egress = "host_direct"` says
  so, and a note explains it). A1 must actually run under the closed topology; running open when the
  route was declared closed means it is not the declared route.
- **Sampling parameters are provider defaults** on all four routes (recorded as null + reason). They
  are an unmeasured degree of freedom.
- **Adapter digests** are recomputed from the repo at `39e978b8` and carry their preimage in the
  declaration; §7 states the rule and gives the command that reproduces each value. **Upstream pins**
  are still read from the archive bundles' provenance, not re-measured here. The adapter packages were
  first recorded at `261f0c9`; the path-independence fix (§7) moved the kapso/eve/loreley bytes, so the
  digests now describe `39e978b8` (simpleloop's package is unchanged by this workstream, so its digest
  is the same value it had before).
- The **prompt-context budgets** are measured only where a tool reported them (claude 200 000
  window / 32 000 output).
- No **long-context or long-horizon** run was made: every verification turn here is tiny. The codex
  route in particular is only proven on small requests.

**Spend.** Model tokens this pass, from the counts the tools printed: codex 830; claude 17 379 in /
2 out; kilo 12 003 total (9 891 in / 2 out / 62 reasoning / 2 048 cached); opencode a few hundred;
plus ~30 tiny `curl` probes of 4–8 output tokens each. Total well under **US$0.01** at
`deepseek-flash` rates, inside the cents budget.

---

## 7. The adapter source digests: preimage, rule, and the recomputed values **[verified by running it]**

### The defect this replaces

The four `RuntimeAdapters.adapters[].adapter_source_sha256` values first shipped here had **no
preimage**. Reproduced before the fix: hashing the 3,596 files under `a0/runtimes` (excluding
`.venv`, `checkout`, `out`, `__pycache__`) matched none of them, and the reviewer's repo-wide scan of
all 106,768 files matched none either. The strings existed only inside `a0/mrc/**`. In a contract
whose subject is the gap between declared and measured identity, a declaration field that cannot be
traced to bytes is the defect class itself, so the values were **recomputed from a real preimage**
rather than annotated.

### The rule, which is recorded inside every declaration

```
adapter_source_sha256 = sha256(b'a0/mrc/v1/RuntimeAdapters/adapter_source' + b'\x00'
                               + canonical_json([[path, sha256(file bytes)], …]))
```

- `canonical_json(obj) = json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=True)`.
- The list is **every blob under `adapter_source_root` at `adapter_commit`**, taken from
  `git ls-tree -r <adapter_commit> -- <adapter_source_root>`, ordered by ascending path — that
  ordering is part of the rule, and the validator rejects any other order.
- The list is not implied: it is written into the declaration as `adapter_source_files`
  (`{path, sha256}` per file), beside `adapter_source_root`, `adapter_commit` and the rule string
  `adapter_source_rule`. Anyone holding the declaration can recompute the digest without our code,
  our repo paths, or the network.

### Scope of the preimage, stated rather than implied

The preimage is the adapter **package**. It does **not** cover launcher wrappers (`a0/runtimes/
loreley/bin/a0-loreley`), per-runtime `adapter.json` entry-point manifests, installed upstream
checkouts (`loreley/checkout`, `kapso_ck`), `__pycache__`, or anything under `out/`. Those are
instruments too; if an A1 arm changes one of them, `adapter_source_sha256` will not move. They are
outside this field's claim, and the field's claim is now exactly what it says.

### The complete enumeration of what the preimage does not cover **[verified by running it]**

An earlier revision of this section named only the launcher, the `adapter.json` manifests, the
upstream checkouts and `out/`, and a review list added a few directories. That list was
**incomplete and is superseded by the enumeration below**, which is read from the repository rather
than written down. It is produced by `git ls-files` on each runtime and split at the declared
preimage root:

```bash
cd /home/ebt/rsi-dev
for r in kapso eve loreley simpleloop; do
  case $r in
    kapso)      root=a0/runtimes/kapso/a0_adapter ;;
    eve)        root=a0/runtimes/eve/a0_adapter ;;
    loreley)    root=a0/runtimes/loreley/src/a0_adapter ;;
    simpleloop) root=a0/runtimes/simpleloop/a0_adapter ;;
  esac
  echo "== $r preimage=$(git ls-files "$root" | wc -l) outside=$(git ls-files "a0/runtimes/$r" | grep -vc "^$root/")"
  git ls-files "a0/runtimes/$r" | grep -v "^$root/" | sed -E "s|^a0/runtimes/$r/||" \
    | grep -vE '^(out|runs|state)/' | sort
done
```

Outside the preimage, tracked and (excluding run output) **instrument-shaped**:

| runtime | preimage | outside | instrument-shaped outside the preimage |
|---|---|---|---|
| kapso | 11 | 3344 | `config/` (4: `adapter.json`, `kapso-core-reqs.txt`, `mode.circle-packing.yaml`, `mode.circle-packing.codex.yaml`), `contract/` (1: `selection/kapso.selection.json`), `bin/` (3: `e2e_round.py`, `e2e_verify.py`, `smoke.py`), top level (4: `ADAPTER.md`, `BRIDGE-2ROUND.md`, `README.md`, `adapter.json`); run output: `runs/` (3037), `state/` (295) |
| eve | 12 | 1167 | `tools/` (5: `run_one_eve_iteration.py`, `replicate_a02.py`, `selection_adoption_check.py`, `eid_r_mutation_check.py`, `recompute-eid-r`), `steps/` (1: `eve_evaluator_step.sh.tmpl`), `selection/` (1: `eve.selection.json`), top level (2: `DECLARATIONS.md`, `README.md`); run output: `out/` (1158) |
| loreley | 14 | 5278 | `src/` plugin modules (3: `loreley_a0_plugin.py`, `loreley_a0_plugin_metrics_heavy.py`, `loreley_a0_plugin_metrics_mapping.py`), `policy/` (1), `probe/` (1), `infra/` (1: `net.sh`), `bin/` (2: `a0-loreley`, `a0_loreley.py`), `llm-round/` (21), `scratch/` (1: `smoke_evaluator.py`), `tools/` (1: `verify_eidr.py`), top level (3: `README.md`, `VERIFICATION.md`, `adapter.json`); run output: `out/` (5244) |
| simpleloop | 14 | 5463 | `policy/` (3: `simpleloop.policy.json`, `simpleloop.inject.json`, `proposed.a0.contract.simpleloop.selection.json`), `solvers/` (1: `main_run.json`), `tools/` (2: `check-frozen-conventions`, `recompute-eid-r`), `tests/` (2), top level (5: `A0_REPORT.md`, `HANDOFF_to_contract_owner.md`, `README.md`, `conftest.py`, `pytest.ini`); run output: `out/` (5450) |

Two corrections to the review list, both verified: loreley's `llm-round/` is **21 tracked files
including logs, worktrees and result JSON** (only 7 are scripts/documents), and the top-level
`README.md`/`adapter.json`/`DECLARATIONS.md`/`VERIFICATION.md` files are tracked instruments too.

### Which of these can change an A1 result while MRC* stays identical **[verified by running it]**

This is the property the enumeration exists to expose, so it is answered by locating the exact line
at which each file enters a run, not by category. Files the **adapter or evaluator reads at run
time** change a number while `MRC*` (and `adapter_source_sha256`) do not move:

| file (outside the preimage) | how it enters the run |
|---|---|
| eve `steps/eve_evaluator_step.sh.tmpl` | the **evaluation step script the runtime executes**, read at `eve_runtime.py:87`; its digest is recorded at `eve_runtime.py:172` but is not frozen by any contract |
| loreley `src/loreley_a0_plugin.py`, `..._metrics_heavy.py`, `..._metrics_mapping.py` | the **worker-evaluator plugin the runtime calls** (`WORKER_EVALUATOR_PLUGIN`), `runtime.py:37`; EID_r hashes the plugin source, but EID_r is a runtime self-report (see D3 in `a0/STATUS.md`) |
| kapso `config/adapter.json` | the adapter's own path config: E*, C*, EID*, mode config, state root (`common.py:62`) |
| kapso `config/mode.circle-packing.yaml` (+ `.codex.yaml`) | the KAPSO **mode config**: fidelity mode, `subsample_seed`, `parent_policy`, budget, coding agent (`runtime.py:103`) |
| kapso `contract/selection/kapso.selection.json` | KAPSO's selection declaration + failure-stage map (`common.py:398`); the adapter only *reports* a mismatch against the frozen copy (`_frozen_canonical_compare`), it does not refuse |
| simpleloop `policy/simpleloop.policy.json`, `policy/simpleloop.inject.json` | the SimpleLoop **policy** (scalarization, tie-break) and injection config, read at `policy.py:22-23` |
| simpleloop `solvers/main_run.json` | the solver roster the campaign consumes |
| loreley `probe/egress_candidate/solution.py` | the closure-probe candidate (`closure.py:43`) |
| loreley `infra/net.sh` | the network setup for the declared closed topology |
| eve `selection/eve.selection.json`, loreley `policy/loreley.selection.json` | the per-runtime selection declarations (`selectionmap.py`; `failure_stage.py:80`) |
| loreley `bin/a0-loreley`, `a0_loreley.py`, `adapter.json`; kapso `bin/*.py`; eve `tools/run_one_eve_iteration.py`; loreley `llm-round/*.sh`/`*.py` | the launchers and campaign drivers an A1 arm would reuse |

Files that do **not** change a score but do change what a green verdict means — the checkers and
tests — are the same class of uncovered instrument: `eve/tools/eid_r_mutation_check.py`,
`eve/tools/selection_adoption_check.py`, `eve/tools/recompute-eid-r`, loreley `tools/verify_eidr.py`,
simpleloop `tools/check-frozen-conventions`, simpleloop `tools/recompute-eid-r`,
simpleloop `tests/`, `conftest.py`, `pytest.ini`.

The sharper statement: **the evaluator step (`eve/steps/`), the evaluator plugin
(`loreley/src/loreley_a0_plugin*.py`), the runtime policy files and the mode config are instruments
that decide every score, and none of them is inside any frozen digest.** An A1 arm can change the
evaluator EvE executes — or the plugin Loreley calls — and `MRC*` will not move. `adapter_source_sha256`
covers the adapter *package* only, and its claim is exactly that; closing this gap needs a wider
instrument digest, which is registered as an open item rather than silently implied.

### The adapter path-independence fix (why these digests changed) **[verified by running it]**

The four adapter packages above were edited to stop resolving the repository from a hard-coded host
root (`contracts.py:13` in loreley was `A0_ROOT = Path("/home/ebt/rsi-dev/a0")`; kapso read absolute
paths straight out of `config/adapter.json`; loreley's closure probe bind-mounted `/home/ebt`). Each
now resolves the repo root from its own location, with `$A0_REPO_ROOT` as an explicit override:

| adapter | change |
|---|---|
| loreley `src/a0_adapter/contracts.py` | `REPO_ROOT = $A0_REPO_ROOT or Path(__file__).resolve().parents[5]`; `A0_ROOT = REPO_ROOT / "a0"` |
| loreley `src/a0_adapter/closure.py:130` | bind-mount `{REPO_ROOT}:{REPO_ROOT}` instead of `/home/ebt:/home/ebt` |
| eve `a0_adapter/common.py` | same resolution; `A0_ROOT`/`REPO_ROOT` derived from `$A0_REPO_ROOT` or `ADAPTER_DIR` |
| kapso `a0_adapter/common.py` | `AdapterConfig.load` re-roots every config path recorded under the declared repo root onto this checkout's root; `$A0_KAPSO_SRC` overrides the upstream path |

Demonstration (copy the tree, run the copy's adapter, show nothing lands back in the original):

```bash
rm -rf /tmp/a0path && mkdir -p /tmp/a0path/copy && cp -a /home/ebt/rsi-dev/a0 /tmp/a0path/copy/a0
# PRE-FIX (before the edits) the copy's adapter still resolves the ORIGINAL:
#   cd /tmp/a0path/copy/a0/runtimes/kapso && .venv/bin/python -c \
#     "import sys;sys.path.insert(0,'.');from a0_adapter.common import AdapterConfig;\
#      c=AdapterConfig.load();print(c.a0_root) "
#   -> /home/ebt/rsi-dev/a0
# POST-FIX the copy resolves the copy:
cd /tmp/a0path/copy/a0/runtimes/loreley && ./checkout/.venv/bin/python -c \
  "import sys;sys.path.insert(0,'src');from a0_adapter.contracts import A0_ROOT;print(A0_ROOT)"
# -> /tmp/a0path/copy/a0
touch /tmp/a0path/marker
cd /tmp && /tmp/a0path/copy/a0/runtimes/loreley/bin/a0-loreley eidr-recompute \
  --run-dir /tmp/a0path/copy/a0/runtimes/loreley/out/pathindep
find /home/ebt/rsi-dev/a0/runtimes -newer /tmp/a0path/marker -type f | wc -l   # -> 0
find /home/ebt/rsi-dev/a0/contract -newer /tmp/a0path/marker -type f | wc -l   # -> 0
```

(The `find` is scoped to `a0/runtimes` and `a0/contract`, the trees an adapter can reach; other
workstreams were editing `a0/qualification`, `a0/conformance` and `a0/envelope` concurrently, so a
whole-`a0` scan is not a clean control while parallel workers are active.)

Real output: in-place resolution is unchanged (`/home/ebt/rsi-dev` for all three; `$A0_KAPSO_SRC`
still `/home/ebt/kapso_ck/kapso/src`); the copied loreley adapter resolves `A0_ROOT` to the copy and
writes `loreley.program.md` under the copy; `find` reports **0** files under the original `a0`
touched by the run. The copy's kapso adapter, run for real (`python -m a0_adapter conformance
--runtime kapso`, 14 candidates, `pass: true`), likewise writes only under the copy; the registered
tree destination is `config.state_root / "registered-eval"` (`runtime.py:135`), which is now the
copy. An explicit override works from either tree:
`A0_REPO_ROOT=/tmp/a0path/copy ... -> REPO_ROOT /tmp/a0path/copy`.

One residual, handed off rather than fixed: the per-runtime `adapter.json` manifests still declare an
**absolute** `cmd`/`interpreter`/`pythonpath` (`a0/runtimes/loreley/adapter.json` →
`/home/ebt/rsi-dev/a0/runtimes/loreley/bin/a0-loreley`; `a0/runtimes/kapso/adapter.json` →
`/home/ebt/rsi-dev/.../python -m a0_adapter`). A harness that *discovers* adapters through those
manifests therefore still launches the original tree's adapter from a copy — the mechanism an
independent verifier observed writing run artifacts into the original `out/`. Those files are outside
this workstream's ownership; the adapter code is now path-independent, the manifests are not.

The **simpleloop** adapter has the same defect and belongs to another workstream, so it was not
edited here: `a0/runtimes/simpleloop/a0_adapter/cli.py:34` is still
`DEFAULT_WORK_ROOT = "/home/ebt/rsi-dev"`, and all of its other defaults (`DEFAULT_CANDIDATE_SET`,
`DEFAULT_EID`, …) are repo-relative strings resolved against that root. It is handed off.

### Recomputed values, by preimage

`python3 verify_adapter_preimage.py` (shares no code with `mrc.py`, reads the declarations, asks
`git`, applies the rule; no network, no key; exit 0 iff every value is reproduced):

```
[ok  ] codex-deepseek-responses     kapso       a0/runtimes/kapso/a0_adapter             11 files  06df3969358eff8542b43b6ad09319c33353f6af615f23f1c6a61e5fdbebcf82
[ok  ] codex-deepseek-responses     eve         a0/runtimes/eve/a0_adapter               12 files  3405931768156016b6db6b41f80fe3aa5554aa4d7bd20f9d90cb24b8832038e8
[ok  ] codex-deepseek-responses     loreley     a0/runtimes/loreley/src/a0_adapter       14 files  3107e8b69a326042c5a2e972714eda8654922396ec119850bb8eea126c269eff
[ok  ] codex-deepseek-responses     simpleloop  a0/runtimes/simpleloop/a0_adapter        14 files  167fe070911bb7a4767690e387e6fa2d138ec61cf31b3f6c7014814b1d5bcc89
[ok  ] claude-deepseek-anthropic    kapso       a0/runtimes/kapso/a0_adapter             11 files  06df3969358eff8542b43b6ad09319c33353f6af615f23f1c6a61e5fdbebcf82
[ok  ] kilo-deepseek-chat           loreley     a0/runtimes/loreley/src/a0_adapter       14 files  3107e8b69a326042c5a2e972714eda8654922396ec119850bb8eea126c269eff
[ok  ] opencode-deepseek-chat       eve         a0/runtimes/eve/a0_adapter               12 files  3405931768156016b6db6b41f80fe3aa5554aa4d7bd20f9d90cb24b8832038e8
every adapter digest is reproduced from its preimage
```

`adapter_commit` resolves to `39e978b89db1335387a2ff42a860ca50b02fdb94`, and the **working tree
matches that commit byte-for-byte for all 51 files in the four preimages**, so the digest describes
both the pinned commit and the tree as it stands (not just one of them):

```
$ python3 make_declarations.py --verify
adapter preimages: 4 runtimes, commit 39e978b8 (39e978b89db1335387a2ff42a860ca50b02fdb94)
[ok ] eve         a0/runtimes/eve/a0_adapter               12 files  3405931768156016b6db6b41f80fe3aa5554aa4d7bd20f9d90cb24b8832038e8
[ok ] kapso       a0/runtimes/kapso/a0_adapter             11 files  06df3969358eff8542b43b6ad09319c33353f6af615f23f1c6a61e5fdbebcf82
[ok ] loreley     a0/runtimes/loreley/src/a0_adapter       14 files  3107e8b69a326042c5a2e972714eda8654922396ec119850bb8eea126c269eff
[ok ] simpleloop  a0/runtimes/simpleloop/a0_adapter        14 files  167fe070911bb7a4767690e387e6fa2d138ec61cf31b3f6c7014814b1d5bcc89
working tree matches 39e978b8 for every file in every preimage
[ok  ] codex-deepseek-responses.spec.json
… eight files …
shipped declarations match a fresh derivation from the repo
exit=0
```

The three adapters this workstream owns changed (`kapso`, `eve`, `loreley`); the **simpleloop**
digest is unchanged (`167fe070…`), because that package is another workstream's and was not touched
here. These declarations therefore cover the simpleloop adapter as of `39e978b8`; if its owner lands
further edits, the declarations must be regenerated again (the preimage rule makes that mechanical).

### What now makes the field non-repeatable of the old defect

- The validator refuses a digest with no preimage (`MRC-ADAPTER-PREIMAGE`) or a digest that is not
  the digest of the preimage it lists (`MRC-ADAPTER-DIGEST`); `mrc_schema.json` requires
  `adapter_source_root`, `adapter_source_files` and `adapter_source_rule` whenever a
  `adapter_source_sha256` string is present. Two negative fixtures cover both refusals (their real
  output is in §4).
- The self-test independently re-implements the rule, recomputes each recorded digest from the
  manifest recorded beside it, and checks that the manifest is exactly the repo's file set at the
  declared commit — three checks, so the field cannot silently go back to being an unfalsifiable
  string.
- A `null` digest remains admissible, but only with `adapter_source_null_reason`, as before.

### Consequences for values quoted elsewhere

The four MRC* values in §1 are new; everything reported before them is superseded and should not be
quoted — `2c5272b8…`, `6630264f…`, `821bfd38…`, `b17b21e8…` (the original, pre-preimage values) and
then `0d98045b…` (codex), `f31802ac…` (claude), `e80a3530…` (kilo), `046ca78c…` (opencode) (the
values that stood until the path-independence fix). `frozen_routes.json` pins
provider/endpoint/surface/model only and does not contain MRC*, so it did not change.

The path-independence fix changes the **adapter digests**, and therefore MRC*, for kapso, eve and
loreley; simpleloop is unchanged. Any A1 record that pinned the previous adapter digests
(`3ab3e139…` kapso, `57a5c251…` eve, `3ab1436f…` loreley) is describing the pre-fix adapters and must
be re-pinned.

One directory outside this one embeds the old values: the reviewer's
`a0/verify/sprint-contract/mrc-falsify/**` (nine files: the `*_tamper.mrc.json` perturbations, their
`spec_*.json` inputs, and `codex_tools_naive.mrc.json`). Those files carry the superseded adapter
digests and MRC*, so re-running the validator on them now reports `MRC-ADAPTER-PREIMAGE` alongside
the code each was built to demonstrate. Their conclusions are unaffected — the model/endpoint cases
still fail from the external registry, and the tools/permissions cases still validate
self-consistently — but the fixtures must be rebuilt from the current declaration to be re-run, which
means re-running the reviewer's own generation step. That directory belongs to the reviewer and was
not edited here.
