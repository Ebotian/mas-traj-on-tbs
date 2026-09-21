# ModelRouteContract (MRC*) — freezing the model route the way `EID*` freezes the evaluator

Owner: `a0/mrc/**`. Status: **delivered for A0-adjacent closure** (external review, point 7).
Everything here is either *verified by running it*, *read from source*, or *inferred*, and each
claim below says which.

---

## 1. Why this exists, and what it is not

`EID*` freezes **what was measured** — the evaluator. It says nothing about **what was measuring
it**. For the A1 comparison ("does open-world acquisition improve automated search") to be
attributable, the *measuring instrument* has to be frozen too, and the honest scope of that
freeze has to be written down.

The estimand this contract supports is:

```
Δ | same declared model route        ← this contract, and the only thing we can defend
```

and **not**

```
Δ | same model weights               ← not verifiable here; see §5
```

We cannot prove which weights served a request. Neither DeepSeek surface returns a weights digest,
a checkpoint id, a revision, or a signed serving attestation. The `model` field in a response is
server-written metadata, and — measured below — **it disagrees with itself across surfaces**: a
retired alias is silently rewritten to `deepseek-flash` on the OpenAI-compatible surfaces but
echoed verbatim on the Anthropic-compatible surface. Two surfaces given the *same* request
therefore report *different* "served" ids. That is the formal reason an echo cannot be treated as
proof, and it is why the freeze below is a freeze of the **route**, not of the model.

MRC* is therefore deliberately *weaker and more honest* than "same model": it pins every knob that
would change what an A1 arm actually is, and it freezes the non-claim about weights.

---

## 2. Canonical hashing and serialization

Same spirit and same bytes as `a0/contract/evalcontract.py` (verified: the self-test hashes a
torture object with both modules and compares byte-for-byte, and checks the domain separator is a
single NUL):

```
canonical_json(obj)   = json.dumps(obj, sort_keys=True, separators=(",",":"),
                                   ensure_ascii=True, allow_nan=False).encode("ascii")
domain_digest(d, b)   = sha256(d.encode("ascii") + b"\x00" + b)
ComponentDigest(name) = domain_digest("a0/mrc/v1/" + name, canonical_json(payload))
MRC*                  = domain_digest("a0/mrc/v1/MRC*", canonical_json({name: digest}))
```

Consequences, all enforced or tested:

- **No absolute paths.** A base URL's *path* (`/v1/responses`) is allowed because it is not a
  location; a filesystem root (`/home/...`, `/usr/...`, `C:\...`) is rejected wherever it appears.
- **No mtimes, ownership, hostnames, pids.** Keys named `mtime`/`ctime`/`atime`/`uid`/`gid`/
  `hostname`/`pid`/`absolute_path` are rejected outright.
- **No credential material.** Only the *names* of environment variables appear. Strings shaped like
  `sk-…` or `Bearer <token>` are rejected.
- **No unfrozen digest smuggled in as absent.** Any field named `*_sha256` may be `null` only with a
  sibling `<field>_null_reason`. An unfrozen prompt hash is an exposure; the contract must say so.
- **Portability, tested:** MRC* is invariant to where the spec file lives and to component/key
  order, and changes when a load-bearing field (requested model, base URL, CLI version) changes.

`identity_evidence` is deliberately **outside** the digest (it carries its own
`identity_evidence_digest`). It is a witness, not part of the contract: recording a new observation
must not change the identity of the route. The frozen non-claim about weights
(`RequestedModel.weights_identity`) *is* inside the digest, so "we do not claim weights" is itself
frozen.

---

## 3. The twelve components, justified by what they would change in an A1 result

A field earns its place only if varying it could move an A1 Δ. Fields that cannot are left out
(e.g. nothing records the CLI's cosmetic banner).

| # | Component | What it is | If it varied, what an A1 result would actually be measuring instead |
|---|---|---|---|
| 1 | **Provider** | `provider_id`, upstream hosts, catalog endpoint, `openrouter_used:false` | A different provider is a different instrument *and* a different price/rate regime. Excluding OpenRouter is a user decision; freezing the flag makes a silent re-route detectable. |
| 2 | **Endpoint** | scheme, host, port, `base_url`, whether TLS is verified | A different base URL is a different serving stack. A `/v1` vs `/anthropic` endpoint speaks a different protocol *and* reports model identity differently (§5). This is the field the frozen registry checks hardest. |
| 3 | **RequestedModel** | requested id, alias policy, permitted secondary, and the frozen **weights non-claim** | Swapping `deepseek-flash`→`deepseek-v4-pro` changes capability and cost by ~4×; permitting an alias changes *which model you think you asked for*. Fixing `alias_policy: canonical_ids_only` is what stops a retired alias from entering a run unnoticed. |
| 4 | **ApiSurface** | wire protocol, surface path, streaming, protocol markers | Responses vs Chat Completions vs Messages changes tool-calling, caching fields, and identity reporting. Codex cannot speak Chat at all; claude cannot speak Responses. Two arms on different surfaces are not the same condition. |
| 5 | **Params** | temperature/top_p/max_tokens/seed/stream/tool_choice/retry/timeout | A sampling change is a direct confound on any search-quality Δ: at a fixed budget, greedy vs sampled decoding changes which candidates survive. An unset value is recorded as *unset with a reason*, not silently defaulted. |
| 6 | **Cli** | name, version, **binary sha256**, config isolation, env-var **names**, argv template | The CLI builds the prompt, tool set, and context assembly. A version bump already changed the tool set (22→21) between 2.1.260 and 2.1.278. The binary hash is what makes "same CLI" checkable rather than asserted. |
| 7 | **Prompt** | protocol-prompt reference, system-prompt hash, context budget | The prompt is where the study's treatment is actually administered. It is **not frozen here** (null + reason): the CLI assembles it at runtime, so it must be recorded per iteration in A1 (§7). Recording context budget matters because claude spends ~17.2k input tokens before the task text. |
| 8 | **Tools** | toolset reference, observed tool names, denied tools, extra sources | Tool availability decides whether the agent can act on the world at all — for the open-world arm this is close to the treatment. A `deny` rule removes a tool from the toolset rather than failing at call time, so its absence is invisible in a transcript unless declared. |
| 9 | **Permissions** | approval policy, sandbox mode, filesystem/exec/network scope | Whether the agent can execute code or write files, and where. EvE's `codex_exec` hardcodes a bypass while `codex_tmux` can be closed — *same route, different permissions*, not interchangeable arms. |
| 10 | **Network** | topology, egress policy, allowlist hosts, proxy, host-bypass risk | **In this study egress policy is the treatment.** An arm that can fetch external artefacts and one that cannot are different conditions by construction. Freezing this is what makes "closed" a declared property rather than an assumed one. |
| 11 | **RuntimeAdapters** | per-runtime lane, adapter commit, adapter source digest **with its preimage**, upstream pin | The adapter is what translates the runtime's actions into this route. Two runtimes sharing a route but not an adapter commit are not the same instrument. The digest is only usable if it names the bytes it covers, so each adapter records `adapter_source_root`, `adapter_source_files` (one `{path, sha256}` per file) and the `adapter_source_rule`; a digest with no preimage fails validation (`MRC-ADAPTER-PREIMAGE`). See §6.1 for the rule and its stated scope. |
| 12 | **TaskSnapshot** | `task_id`, `eid_star`, `e_star_sha256`, `c_star_digest`, candidate count | The evaluator and candidate set this route is paired with. A route run against a different `EID*` is measuring a different thing; the validator rejects any `eid_star` other than the frozen one. |

---

## 4. The four frozen routes

Frozen registry: `frozen_routes.json`. Filled declarations: `declarations/*.mrc.json`.
All four were **verified live on this host** (real model turns), not invented — see `REPORT.md` §2
for the commands and their output.

| route_id | CLI (version) | surface | base URL | MRC* |
|---|---|---|---|---|
| `codex-deepseek-responses` | codex 0.155.1 | `/v1/responses` | `https://api.deepseek.com/v1` | `6ed87ac4…` |
| `claude-deepseek-anthropic` | claude 2.1.278 | `/anthropic/v1/messages` | `https://api.deepseek.com/anthropic` | `b61c3a15…` |
| `kilo-deepseek-chat` | kilo 7.7.5 | `/v1/chat/completions` | `https://api.deepseek.com/v1` | `8baaa800…` |
| `opencode-deepseek-chat` | opencode v2.0.11 | `/v1/chat/completions` | `https://api.deepseek.com/v1` | `490f9109…` |

These four values were last recomputed on 2026-09-21 when the adapter path-independence fix moved the
adapter source digests for all four runtimes (§6.1, `REPORT.md` §7); the earlier values
(`2c5272b8…`, `6630264f…`, `821bfd38…`, `b17b21e8…`, then `0d98045b…`, `f31802ac…`, `e80a3530…`,
`046ca78c…`, then `9becc39c…`, `dfb9316f…`, `6688c0d4…`, `d04a4159…`) are superseded and must not be
quoted.

Encoded user decisions (`model_policy`, validated): **`deepseek-flash` primary**;
**mixed use of `deepseek-v4-pro` permitted** (`permitted_secondary`); **OpenRouter excluded**
(`excluded_providers` contains `openrouter`, and `Provider.openrouter_used` is `false`). A
declaration that names any other primary, permits an un-listed secondary, or drops the exclusion
fails validation.

---

## 5. `identity_evidence`: what was observed, and why an echo is not proof

Each declaration carries an `identity_evidence` block. Measured 2026-09-21 by direct `curl` against
the live endpoint (requested id → id the response reports):

| requested | `openai_chat_completions` | `anthropic_messages` | `openai_responses` |
|---|---|---|---|
| `deepseek-flash` | `deepseek-flash` | `deepseek-flash` | `deepseek-flash` |
| `deepseek-v4-pro` | `deepseek-v4-pro` | `deepseek-v4-pro` | `deepseek-v4-pro` |
| `deepseek-v4-flash` (retired alias) | **`deepseek-flash`** | **`deepseek-v4-flash`** | **`deepseek-flash`** |
| `deepseek-v4-flash-vision-exp` | **`deepseek-flash`** | **`deepseek-v4-flash-vision-exp`** | **`deepseek-flash`** |
| `deepseek-nope` | 400 | 400 | 400 |

Read the last two data rows carefully. For a *canonical* id every surface echoes the request, which
looks like confirmation and is not. For a *retired alias* the surfaces disagree — the OpenAI-shaped
ones rewrite it to `deepseek-flash`, the Anthropic-shaped one returns it verbatim. **The same
request produces two different "served" strings**, so the field is surface-local metadata rather
than an attestation. Nothing anywhere carries a weights identity.

Therefore each declaration freezes:

```json
"weights_identity": {
  "verifiable": false,
  "surface_echo_is_not_proof": true,
  "reason": "…(the paragraph above, abridged)…"
}
```

and the validator refuses any declaration whose evidence block claims `weights_identity_verifiable:
true`, or whose observation sets `proves_weights: true` on an echo
(`MRC-IDENTITY-WEIGHTS-CLAIM`, `MRC-IDENTITY-ECHO-AS-PROOF`).

> **Correction to the reviewed document.** `a0/STATUS.md` §7 states that the Anthropic surface
> reported `deepseek-v4-flash` for a requested `deepseek-flash`. That does **not** reproduce here:
> for a requested `deepseek-flash` the Anthropic surface reports `deepseek-flash`. The
> `deepseek-v4-flash` string appears only when the *alias* is what was requested, and then it is the
> Anthropic surface that echoes it while the OpenAI surfaces canonicalize it. The review's
> conclusion (echo ≠ proof) stands and is in fact stronger than stated; the surface attribution in
> the reviewed text is inverted and should not be quoted. `STATUS.md` is owned by the coordinator
> and was not edited here.

---

## 6. The validator

`mrc.py` — `compute`, `recompute`, `validate`. Codes and what they catch:

| Code | Trigger |
|---|---|
| `MRC-SCHEMA` / `MRC-MISSING-COMPONENT` | wrong schema tag; a component absent |
| `MRC-DIGEST-MISMATCH` | a payload edited without recomputing the digest, or MRC* disagrees |
| `MRC-HYGIENE` | absolute filesystem path, or a credential-shaped literal, in hashed material |
| `MRC-NULL-DIGEST` | a `*_sha256` is null without a stated reason |
| `MRC-IDENTITY-*` | evidence block missing, or an echo presented as weight proof |
| `MRC-PROVIDER/ENDPOINT/SURFACE/MODEL-DRIFT` | the declaration disagrees with `frozen_routes.json` |
| `MRC-POLICY-PRIMARY/EXCLUDED/SECONDARY` | the model policy no longer encodes the user's decision |
| `MRC-EID-DRIFT` | the task snapshot names an `eid_star` other than `664115e0…` |
| `MRC-ADAPTER-MISSING` | no runtime/adapter commits declared |
| `MRC-ADAPTER-PREIMAGE` | an `adapter_source_sha256` is declared with no preimage, no `adapter_source_root`, or no rule |
| `MRC-ADAPTER-DIGEST` | an `adapter_source_sha256` is not the digest of the preimage recorded beside it |
| `MRC-ROUTE-UNKNOWN` | a route not present in the frozen registry |

Run it:

```bash
cd /home/ebt/rsi-dev/a0/mrc
python3 mrc.py validate --mrc-file declarations/codex-deepseek-responses.mrc.json --frozen frozen_routes.json
python3 mrc.py recompute --mrc-file declarations/codex-deepseek-responses.mrc.json
python3 mrc_selftest.py          # 44 checks, incl. 14 negative cases
python3 verify_adapter_preimage.py
```

### 6.1 The adapter source digest, and why it is not just "a hash of a file"

`RuntimeAdapters.adapters[].adapter_source_sha256` is the one digest in the contract that covers
bytes outside the declaration, so it is also the one that can rot into an unfalsifiable string. It is
therefore defined over an explicitly recorded preimage:

```
adapter_source_sha256 = sha256(b'a0/mrc/v1/RuntimeAdapters/adapter_source' + b'\x00'
                               + canonical_json([[path, sha256(file bytes)], …]))
```

with `canonical_json` the same function as everywhere else, and the list given by
`git ls-tree -r <adapter_commit> -- <adapter_source_root>` in ascending path order. The preimage
itself is written into the declaration as `adapter_source_files`, one `{path, sha256}` per file, so
the value is recomputable by anyone holding the declaration and checkable by the validator
(`MRC-ADAPTER-PREIMAGE`, `MRC-ADAPTER-DIGEST`). A digest whose preimage cannot be named is not
evidence, and this contract now refuses to record one.

**Scope, declared:** the preimage is the adapter *package* — `a0/runtimes/<runtime>/a0_adapter` (for
loreley, `a0/runtimes/loreley/src/a0_adapter`). It does **not** cover launcher wrappers
(`bin/a0-loreley`), `adapter.json` entry-point manifests, installed upstream checkouts
(`loreley/checkout`, `kapso_ck`), `__pycache__`, or generated outputs under `out/`. A change in any
of those moves the instrument without moving `adapter_source_sha256`; they are outside this field's
claim, so if an A1 arm changes one of them the change has to be recorded as part of that arm's
adapter identity, not inferred from the digest.

**What the drift check does not cover.** `frozen_routes.json` holds provider, endpoint, surface path
and requested model id — those four fail validation from an *external* registry even after a
self-consistent recomputation (`MRC-*-DRIFT`). `Tools` and `Permissions` are not in that registry:
they are protected only by the `MRC*` pin, so a self-consistent tool/permission edit validates and
simply yields a different `MRC*`. Comparing a run's `mrc_star` against the recorded value in §4 is
the only check for them; this is a property of hashing, stated here so no one reads the drift table
as covering more than it does.

---

## 7. What an A1 run must record per iteration, and how it meets `B_hard`

For attribution to hold, an A1 iteration must be replayable as *"this turn happened on route R,
under budget B, and produced evaluator outcome O"*. MRC* freezes R's shape; the run must record
that R held at the moment of the turn, plus the budget, plus the outcome link.

**Per iteration, record:**

1. **`mrc_star`** — the route actually in force. If a run mixes routes (e.g. a `deepseek-v4-pro`
   calibration arm), each turn records its own `mrc_star`; mixing without recording it destroys
   attribution.
2. **`identity_evidence` at runtime** — the `requested` id *and* the `echoed`/reported id **as the
   surface reported it**, plus which surface. Store both, never just one: this is the only place the
   echo-vs-proof distinction survives into the data.
3. **CLI identity as executed** — `name@version` and the binary `sha256` (or a re-check that it
   equals the frozen value), so "same CLI" is checkable rather than asserted.
4. **Effective params and permission/network posture** — the values actually used, not the declared
   defaults, since a CLI may override them (claude's `max_tokens=32000` for a non-`claude-*` id is
   an example).
5. **Prompt digest** — the system/prompt bytes actually sent. This is the largest unfrozen surface
   in the contract (§3, row 7) and the first place A1 attribution could silently break.
6. **`eid_star` and the evaluator outcome** — the pairing back to the frozen `EID*` and the
   `E*` outcome, so the turn links route → score unambiguously.

**Interaction with `B_hard = (T_wall, N_evaluatorCalls, concurrency cap)`:**

- The budget is only comparable **per route**. `T_wall` is wall-clock, and the four routes differ
  in per-turn latency (`deepseek-flash` ~5.5 s vs `deepseek-v4-pro` ~12.6 s on the same 4-turn
  task, measured); a faster route fits *more* iterations into the same `T_wall`. So `T_wall` alone
  is not a fair cross-route budget — report `N_evaluatorCalls` alongside it, since that is the
  route-insensitive denominator.
- `N_evaluatorCalls` counts calls to `E*`, not model calls. Because `E*` is local and frozen, it is
  the one counter genuinely invariant across routes; it is the anchor that makes the two arms
  comparable.
- **The concurrency cap bounds model spend, which is where routes actually diverge.** Per-turn
  input scales with the CLI's own prompt: claude spends ~17.2k input tokens per trivial turn vs
  codex ~0.8k and kilo ~10k. Under a concurrency cap, a high-prompt-overhead route exhausts a token
  budget in far fewer iterations. Record `N_modelCalls`, `T_in`/`T_out` and per-route token counts
  in the resource trace so this is visible rather than inferred.
- Record the **route** in every `resource` trace event: without it, a budget trace cannot be split
  by route, and the two arms' budgets silently merge.

Net: MRC* freezes the *route*; the per-iteration records above freeze *that the route was the one
in force*; `B_hard` bounds the search. Attribution then reads *"Δ over the same route under the same
counted budget"* — which is exactly the estimand in §1, and the strongest one the evidence supports.

---

## 8. Status of this work

**Verified by running it**
- All four routes produced real model turns on this host (codex 830 tok, claude 17 379/2 tok,
  kilo 12 003 tok, opencode "OK"); commands and output in `REPORT.md` §2.
- The identity matrix in §5, by direct `curl` on all three surfaces.
- `mrc_selftest.py`: **44/44** checks, including canonical-form byte-equality with `evalcontract.py`,
  an independent re-implementation of MRC*, an independent re-implementation of the adapter-preimage
  rule, three preimage checks (manifest→digest, rule identity, preimage-vs-repo), four positive
  controls, and **14 negative cases** each failing with its expected code.
- All four declarations validate clean against `frozen_routes.json` and `mrc_schema.json`.
- **Adapter source digests** recomputed from the repo at `5d96967f` (the path-independence fix; the
  values before it were taken at `261f0c9`, then `39e978b8`): each of the four values is
  reproduced from its recorded preimage by `verify_adapter_preimage.py` (no code shared with
  `mrc.py`) and by `make_declarations.py --verify`, and the working tree matches the pinned commit
  for all 51 preimage files (§6.1, `REPORT.md` §7). Only simpleloop's digest moved at `5d96967f`;
  kapso, eve and loreley are the same values they carried at `39e978b8`.

**Read from source / prior measurements**
- **Upstream pins** (`7d99b152`, `979065fd`, `4c375920`, `self_built`) and the closure topology are
  read from `a0/archive/provenance.json` and the `exit-closed` reports, not re-measured here.
- Tool-name lists for claude/opencode are taken from prior reports.

**Not established (explicit)**
- **Weight-level identity remains unverifiable** — by construction, and now frozen as such.
- **Prompts and tool schemas are not frozen** (`null` + reason). They are the largest remaining
  attribution risk and the first thing A1 must record per iteration (§7).
- The verification turns ran with **direct host egress**, while the declarations freeze the **closed
  `a0pc-*` topology** as the intended A1 route (`Network.a0_verification_egress` says so). A1 must
  run under the closed topology and re-confirm the barrier; a route run open when it was declared
  closed is not the declared route.
- Sampling parameters on all four routes are provider defaults (`null` + reason): not set, not
  measured, and a hidden degree of freedom.
- The repo head moved to `261f0c9` during the adapter work; the path-independence fix committed the
  loreley/eve/kapso adapters at `39e978b8` and the simpleloop adapter at `5d96967f`, which is the
  adapter commit now recorded.
