# `a0/attestation/` — execution/load attestation for `E*`

Owner: execution/load attestation workstream (external review, point 1). Field
specification and the full justification of every field: [`FIELDS.md`](FIELDS.md).

## The gap this closes

`EID* = 664115e0…` freezes the **intended** evaluator identity. It cannot see the
**executed** one: a different module imported under the evaluator's name, a stale or
forged `__pycache__` entry, a different native dependency, or an environment variable
that changes behaviour all leave every byte of the declared source unchanged. Our own
history contains the motivating incident (`local_eval.py` frozen as "the evaluator"
while the runtime loaded `evaluate.py`, one ULP away).

This directory produces, for each real `E*` invocation, an attestation that separates

```
EID_semantic   the frozen five-component EID*, recomputed at run time from the
               inputs actually on disk
EID_execution  H(EID_semantic, invocation, dependencies, runtime, loaded artifacts,
                 environment, candidate actually evaluated)
```

and a verifier that answers three questions **separately**:

- **Q1** does it recompute?
- **Q2** does its `EID_semantic` component match the frozen value?
- **Q3** is the declared identity *realized* by this execution?

Q3 exists because the review's `EID_execution ⊨ EID_semantic` is not implementable as
written (see `FIELDS.md` §2). Q1 ∧ Q2 are not sufficient, and the demonstrations are the
proof: all three tampered attestations recompute perfectly and carry the frozen
`EID_semantic`.

## Files

| file | role |
|---|---|
| `attest.py` | producer. Runs the real frozen CLI (`python e_star.py evaluate …`) plus a capture route and a child probe, and writes the canonical attestation |
| `_bootstrap.py` | the sensor. Installs a `sys.addaudithook` in the process that runs `E*` and records the `exec` code objects, imports, opens, child process and environment |
| `attest_lib.py` | the identity scheme (`EID_execution`), shared by producer, self-test and demos |
| `verify_attestation.py` | verifier. Deliberately **does not** import `attest_lib`: it has its own canonicalizer, its own reimplementation of `E*`'s self-report scheme and of the contract's `EID*` combination step |
| `selftest.py` | 11 executed checks: canonicalizer agreement, the two independent reimplementations, and four injected faults that must be rejected |
| `demo.py` | builds and runs the four demonstrations (control + three attacks) and records predictions vs observations |
| `FIELDS.md` | field-by-field specification, non-obtainable fields, limits of the method, wiring proposal |
| `out/` | generated attestations, verdicts, self-test report, demo evidence |

`e_star.py`, `e_star_child.py` and everything else under `a0/tasks/**` are **not**
modified: the wrapper observes the evaluator from outside, through the audit hook.

## Quick start

```sh
PY=a0/tasks/circle-packing/.venv/bin/python

# one real invocation
$PY a0/attestation/attest.py --candidate a0/tasks/circle-packing/C_STAR/c01_good_hex
# → out/attestation.c01_good_hex.full.json

$PY a0/attestation/verify_attestation.py \
    --attestation a0/attestation/out/attestation.c01_good_hex.full.json --repo-root .
# → Q1 RECOMPUTES / Q2 SEMANTIC_MATCH / Q3 REALIZED          (exit 0)

$PY a0/attestation/selftest.py     # 11 checks, all must pass
$PY a0/attestation/demo.py         # control + 3 demonstrations, with verification
```

Full command list, including the determinism check: `FIELDS.md` §7.
Verifier exit codes: `0` all good, `1` does not recompute, `2` semantic mismatch,
`3` not realized, `4` malformed.

## Results

Clean runs (`out/attestation.*.json`, `out/verdict.*.json`):

| candidate | declared verdict | Q1 | Q2 | Q3 | EID_execution |
|---|---|---|---|---|---|
| `c01_good_hex` | `ok` | RECOMPUTES | SEMANTIC_MATCH | REALIZED | `bf2ba2ef…5de755005` |
| `c05_overlapping` | `invalid` | RECOMPUTES | SEMANTIC_MATCH | REALIZED | `927bfa43…0e463274` |

`EID_semantic` is `664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328`
in both, and the semantic identity is recomputed independently by the verifier with the
contract owner's `evalcontract.py` over the live tree. Three runs of the same candidate
produce the same `EID_execution` and byte-identical payloads (`out/determinism.{a,b}.json`).

Demonstrations (`out/demo/`, candidate `c05_overlapping`, declared `invalid`; the
declared `E*` source hash is unchanged before and after: `2abc6ea1…`):

| | d0 control | d1 shadow module | d2 stale bytecode | d3 other file |
|---|---|---|---|---|
| Q1 / Q2 | ok / ok | ok / ok | ok / ok | ok / ok |
| Q3 | REALIZED | **NOT_REALIZED** | **NOT_REALIZED** | **NOT_REALIZED** |
| verdict on the route that ran the substitution | `invalid` | `invalid` (identity falsified) | **`ok` 2.4519…** | **`ok` 2.4519…** |
| verdict on the authoritative script route | `invalid` | `invalid` | `invalid` (disagrees) | **`ok`** |
| `E*` self-report | frozen | falsified (predicted) | frozen | different (predicted) |
| executed code | = source | = source | **≠ source** (predicted) | = patched source (predicted) |

On the route that ran the substituted artifact, d2 and d3 report the study's `invalid`
candidate as `ok` with the best nominal score — the false green — while `EID*` stays
bit-identical. d1 changes nothing but the hash `E*` reports about itself. Complete
evidence, including whether each forgery's predicted digest was the one observed:
`out/demo/EVIDENCE.json`.

## What is not covered

`FIELDS.md` §5 lists the limits as limits: the harness is trusted software; namespace
hygiene covers `hashlib`/`argparse`/`json` but not `importlib.util`; the child process is
attested by a probe rather than instrumented; `routes_agree` can false-positive on
timing-sensitive candidates; `EID_execution` is host-relative by design; one candidate
per attestation; and the whole thing is **self**-attestation — a compromised producer can
emit a consistent lie, so producing the attestation from the conformance layer rather than
from inside the lane is a wiring decision, not something this directory can enforce
against itself. The native-dependency counterexample is **not** demonstrated, for a
measured reason: this interpreter build loads no extension modules at all, so there is no
native artifact to swap (`native_dependencies: []`, and the 33 MB interpreter binary is
hashed in full).

The container-image digest is `null` and nothing was fabricated in its place: `E*` runs on
the host, so no image digest exists for this invocation; `environment_digest` covers
everything that is recomputable here.

## Wiring every run (proposal, not implemented)

The four adapters still call `E*` directly. `FIELDS.md` §8 names each call site
(`simpleloop/a0_adapter/estareval.py:219`, `kapso/a0_adapter/channels.py:113`,
`eve/a0_adapter/common.py:419`, `loreley/src/a0_adapter/runtime.py:325`) and shows which
mechanisms are live today: demonstration d1 is live for **KAPSO and EvE**, which forward
their own environment (including `PYTHONPATH`) into `E*`; demonstration d2 is not live for
any of them, because all four invoke `E*` as a script, and running a script never consults
`__pycache__`. The proposal is: redirect each call site to `attest.py` (same CLI surface,
one option change, forwarding the existing env with `--env`); carry
`{eid_execution, eid_semantic, attestation_path, verdict}` on the per-run trace record (a
contract-owner change); add a per-lane run register so `--declared-eid-execution` has
something to compare against; and make the conformance runner fail a row whose attestation
is not `REALIZED`, rather than compare it. No file outside `a0/attestation/` was touched to
produce any of this.
