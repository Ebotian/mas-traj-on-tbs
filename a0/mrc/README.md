# `a0/mrc` — ModelRouteContract (MRC*)

Freezes the **model route** the way `a0/contract/evalcontract.py` freezes the **evaluator**. It
exists so the A1 estimand can be written honestly:

```
Δ | same declared model route      ← this contract
Δ | same model weights             ← not verifiable here, and frozen as such
```

The external review's point 7 asked for exactly this: an echo of a requested model id is not proof
of which weights served a request, so the thing that gets frozen is the route.

## Files

| file | purpose |
|---|---|
| `SPEC.md` | the schema, each field justified by what it would change in an A1 result |
| `REPORT.md` | execution evidence: the four lanes driven live, the identity matrix, validator output |
| `A1_ATTRIBUTION.md` | what an A1 iteration must record, and how it meets `B_hard` |
| `mrc_schema.json` | JSON Schema (draft 2020-12) for a declaration |
| `mrc.py` | canonical hashing + validator + CLI |
| `frozen_routes.json` | the four routes with their frozen provider/endpoint/surface/model |
| `declarations/` | filled declarations (`.spec.json` inputs, `.mrc.json` frozen docs) |
| `make_declarations.py` | regenerates `declarations/`; `--verify` re-derives and diffs, writing nothing |
| `verify_adapter_preimage.py` | recomputes each adapter source digest from its preimage, sharing no code with `mrc.py` |
| `mrc_selftest.py` | 44 checks, incl. an independent MRC* re-implementation, the adapter-preimage checks, and 14 negative cases |
| `fixtures/negative/` | declarations that must be rejected, with the code each triggers |

## Quick start

```bash
cd a0/mrc
python3 mrc_selftest.py                     # 44/44, no network, no key
python3 mrc.py validate --mrc-file declarations/codex-deepseek-responses.mrc.json --frozen frozen_routes.json
python3 verify_adapter_preimage.py           # each adapter digest, recomputed from git
```

`adapter_source_sha256` is not "the hash of some file": each adapter records the files it covers
(`adapter_source_files`), the root and commit they were taken from, and the rule that maps them to
the digest — so a third party can recompute the value, and the validator rejects a digest with no
preimage. Scope and rule: `SPEC.md` §6.1, `REPORT.md` §7.

## The four routes

`codex-deepseek-responses` · `claude-deepseek-anthropic` · `kilo-deepseek-chat` ·
`opencode-deepseek-chat` — all against `api.deepseek.com`, all on `deepseek-flash` as primary with
`deepseek-v4-pro` permitted as a mixed secondary and OpenRouter excluded.
