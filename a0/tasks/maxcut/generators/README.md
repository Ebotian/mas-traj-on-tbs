# `a0/tasks/maxcut/generators/` — provenance for the frozen Max-Cut suite

Everything here is **provenance, never data identity**. The identity of an instance is the sha256 of
`suite/<role>/<graph_id>.json` (`INTERFACE.md` §2); nothing in this directory may be cited as the
reason a graph has the value it has, and `generator.seed` in particular is explicitly excluded from
identity and from every verdict.

| Path | What it is |
|---|---|
| `maxcut_suite.py` | the whole tool: deterministic generators, canonical writer, verifier, reporter |
| `config.json` | the frozen suite configuration: master seed, families, strata, parameters, reps |
| `provenance.json` | per-graph seed + **the Planted families' node labels**, derived from the frozen files by `audit_labels.py refresh` |
| `audit_labels.py` | the label audit: recorded labels == regenerated labels, no spelling of them in `suite/**` or in the candidate-facing view |
| `nontriviality_probe.json` | NON-NORMATIVE diagnostic: random / 1-exchange cut fractions per graph |
| `FREEZE.json` | the commit that froze `suite/`, the generator source digest, and the manifest digest |
| `DEVIATIONS.md` | where this workstream departs from `INTERFACE.md`, or an explicit statement that it does not |

Owner: the suite workstream. `e_star.py`, `candidates/` and `references/` belong to other workers.

---

## 1. What the suite is

`suite/` holds **60 instances at n = 128, unit weights, no self-loops, no duplicate edges**:

* `dev/` — 24 (`G_dev_0001` … `G_dev_0024`), 6 per family;
* `eval/` — 24 (`G_eval_0001` … `G_eval_0024`), 6 per family;
* `calibration/` — 12 (`C_0001` … `C_0012`), 3 per family;
* `manifest.json` — the index: per-graph sha256, family, stratum, n, |E|, degree statistics, connected
  components, isolated-node count, the full generator record, and the whole configuration.

Four families, three parameter strata each. The family of every graph is in the file itself
(`family`); the stratum is in the manifest.

---

## 2. Reproducing, and producing a different suite

```console
$ cd /home/ebt/rsi-dev

# rebuild the frozen suite in place (byte-identical: see §6)
$ python3 a0/tasks/maxcut/generators/maxcut_suite.py build

# check everything: canonical identity, key set, structure, regeneration, statistics,
# cross-role disjointness, planted-label leakage
$ python3 a0/tasks/maxcut/generators/maxcut_suite.py verify

# the tables quoted in suite/README.md
$ python3 a0/tasks/maxcut/generators/maxcut_suite.py stats
$ python3 a0/tasks/maxcut/generators/maxcut_suite.py probe            # per-family summary
$ python3 a0/tasks/maxcut/generators/maxcut_suite.py probe --detail   # + the per-graph table

# a DIFFERENT suite with the same procedure -- new master seed, new directory
$ python3 a0/tasks/maxcut/generators/maxcut_suite.py build --suite /tmp/maxcut-alt --master-seed 777
$ python3 a0/tasks/maxcut/generators/maxcut_suite.py verify --suite /tmp/maxcut-alt --master-seed 777
```

Standard library only, no third-party packages, no network, no model calls. Python 3.8+ syntax; the
frozen suite was built with the system interpreter (`python3` = CPython 3.14.7) and is byte-identical
under any of them because every draw comes from the splitmix64 stream below.

`build` never touches anything outside `--suite` (graph files + `manifest.json`) and
`--generators` (`provenance.json`).

---

## 3. The generators, exactly

Each generator is a pure function of `(n, params, seed)`. Parameters are *distribution parameters*;
the probability parameters travel as exact rationals (`p_num / p_den`), and every draw is an integer
comparison (`u64 % p_den < p_num`), so nothing depends on binary64 rounding. The decimal spelling
(`"p": "0.030"`) is carried alongside them for readability only.

| family | `generator.name` | procedure |
|---|---|---|
| `ER` | `er_gnp` | G(n,p): every pair `(i,j)`, `i<j`, in lexicographic order, drawn with probability `p_num/p_den` |
| `RR` | `rr_pairing` | uniform-ish random `d`-regular graph by the pairing model: shuffle `n·d` stubs, pair them off, **reject and redraw** on any self-loop or duplicate edge |
| `BA` | `ba_preferential` | seed graph `K_{m+1}`, then each later node `v` attaches `m` edges to existing nodes drawn **without replacement** with probability proportional to current degree (integer cumulative walk, rejection on repeats) |
| `Planted` | `planted_partition` | community label vector = a **random permutation** of the size multiset; every pair drawn with `p_in` if the two labels agree, else `p_out` |

Documented details that a re-implementer must match:

* **Draw order is part of the procedure.** `er_gnp` and `planted_partition` consume one draw per pair
  in lexicographic `(i,j)` order, and `planted_partition` draws for *both* branches (so the number of
  draws does not depend on the labels). `rr_pairing` consumes the shuffle of the current attempt and
  then one draw per pair; a rejected attempt still advances the stream. `ba_preferential` consumes a
  draw per accepted target and one per rejected repeat.
* **`rr_pairing` includes its rejections.** The number of attempts before a simple graph appears is
  therefore part of the recorded stream, and the instance is still a deterministic function of
  `(n, d, seed)`.
* **`ba_preferential` is a declared variant.** Targets are sampled without replacement by rejection
  rather than by an exact sequential sampler; the seed graph is `K_{m+1}`. This is a *documented
  choice*, not NetworkX's `barabasi_albert_graph`, and the two will not agree edge-for-edge.
* **Node numbering.** Community labels are permuted, so the label vector is not readable from the
  sizes and node order carries no community information.
* **The manifest is self-describing.** `manifest.json.generator_config` is the configuration that was
  actually used (including an overridden master seed), so the embedded config alone determines the
  instances: rebuild from that config with the recorded generator revision and you get the same bytes.

### Randomness and seeds

```python
class SplitMix64:                       # maxcut_suite.py
    state = seed & (2**64 - 1)
    next_u64 = splitmix64-mix(state += 0x9E3779B97F4A7C15)
```

`random` is not used anywhere, so the suite does not depend on an interpreter's RNG implementation or
on `PYTHONHASHSEED`. Per-graph seeds are derived, not chosen:

```
seed(graph) = int.from_bytes(sha256(
    "a0.maxcut.suite/v1|master=<M>|role=<dev|eval|calibration>|family=<F>|stratum=<S>|rep=<r>|graph_id=<ID>"
).digest()[:8], "big")
```

The `role` is inside the seed material, so dev, eval and calibration instances come from
**independently seeded streams**, not from splitting one draw — which is what the assignment requires
and what makes the three sets independent rather than merely disjoint. The seeds themselves are
recorded per graph in `manifest.json` (`graphs[i].generator.seed`) and in `provenance.json`.

---

## 4. Strata, and why these parameters

`n = 128` everywhere. Full configuration: `config.json` (also embedded verbatim in
`manifest.json.generator_config`).

| family | strata | expected regime |
|---|---|---|
| `ER` | `p = 0.030, 0.050, 0.080` | mean degree 4.0 / 6.2 / 10.6 |
| `RR` | `d = 3, 4, 5` | exact mean degree 3 / 4 / 5 |
| `BA` | `m = 2, 3, 5` | mean degree 4.0 / 5.9 / 9.8, heavy tail |
| `Planted` | `k, sizes, p_in, p_out` = `(2, [64,64], 0.10, 0.02)`, `(4, [32×4], 0.15, 0.02)`, `(3, [64,40,24], 0.12, 0.03)` | mean degree 6.7–8.2, 4–7× intra/inter contrast |

The suite is deliberately **sparse** (mean degree 3–11). Two reasons:

1. **Headroom.** The later gate compares a plain `one_exchange` baseline with a reference target and
   demands a per-family improvement of order 0.02–0.03 (`a0/A1-CONTRACT-AUDIT.md` §B3). Dense graphs
   saturate: a trivial local search lands within a hair of the optimum, the gate becomes vacuous, and
   the canonical failure the audit names is exactly "inject something nearly optimal and watch what
   space is left". Sparse instances keep the gap open.
2. **No trivially separable family.** Random partitions score ~0.50 on every family (§5), i.e. a
   random partition is nowhere near any reference target, and the structure families are structurally
   distinct from one another (uniform / exactly regular / heavy-tailed / community).

Degeneracy audit, over all 60 instances (measured, `manifest.json`): smallest |E| = 192, largest |E| =
713, **no graph has zero edges**, the smallest largest-component is **123 of 128 nodes**, 15 isolated
nodes exist in total and only 8 of the 60 graphs contain any (`INTERFACE.md` §2 permits isolated nodes
and requires them to be recorded, which the manifest does per graph).

`RR` carries **no degree signal at all** — the degree sequence is constant (3, 4 or 5), so whatever a
solver finds comes from the arrangement. `BA` is the opposite extreme (degree max 50; over its 12
dev+eval instances, 103 of 1536 nodes sit at degree ≥ 17). `Planted` is a trap for anything that
equates "community structure" with "good cut": the planted partition's cut fraction is only 0.14–0.32,
*below* a random partition (see §5).

---

## 5. The non-triviality probe (`nontriviality_probe.json`)

```console
$ python3 a0/tasks/maxcut/generators/maxcut_suite.py probe
| family | graphs | random cut frac (mean) | 1-exchange cut frac (mean of bests) | range of 1-exchange |
|---|---|---|---|---|
| ER | 12 | 0.5055 | 0.7439 | 0.6796–0.8075 |
| RR | 12 | 0.5003 | 0.8083 | 0.7578–0.8698 |
| BA | 12 | 0.5009 | 0.7404 | 0.688–0.7984 |
| Planted | 12 | 0.5045 | 0.7243 | 0.7013–0.7422 |
```

Method: 8 seeded uniform random partitions (mean cut fraction) and 4 seeded random starts pushed to a
steepest-descent single-flip local optimum (best cut fraction), per graph; the Planted rows also
report the generator's own planted partition.

**This is not the reference set.** `R_i / OPT_i / U_i` is owned by `a0/tasks/maxcut/references/`. The
probe is a parameter-justification diagnostic: it shows (a) no instance is degenerate (every graph has
edges and a giant component, §4) and (b) no family is trivially separable (a random partition sits at
~0.50 while a plain local search reaches 0.72–0.81, so the reference has somewhere to sit above and
the improvement channel is not pre-filled).

One honest caveat, surfaced here rather than buried: the **tightest headroom is `RR d = 3`**, where
1-exchange already reaches 0.8698 on one instance. The asymptotic max-cut fraction of a random
3-regular graph is about 0.88–0.89 (*inferred* from the literature on the 1RSB/spin-glass computation
— not measured here; the study's own reference value is `references/`'s job), which leaves that
stratum the least room above a plain local search. If the pre-registered per-family gate turns out to
fail on a family, `RR d = 3` is the first candidate for re-drawing — and `INTERFACE.md` §12 requires a
failed gate to be met with a rebuilt, recorded suite, not a relaxed gate.

---

## 6. Verification

`verify` recomputes the entire suite from `(config, master_seed)` and compares against what is on
disk. It does **not** trust the writer:

| check | what it proves |
|---|---|
| `canonical_reparse` (×60) | reloading each file and re-serialising per `INTERFACE.md` §2 reproduces the same bytes — the sha256 is a function of the content, not of the writer |
| `graph_sha256` / `graph_keys` / `graph_structure` (×60) | each file's digest matches the manifest; the key set is exactly `{schema, graph_id, family, n, edges, generator, notes}`; `n = 128`; `u < v`; no self-loop; no duplicate; strictly ascending; endpoints in range |
| `graph_regenerated` (×60) | re-running the recorded `(generator, params, seed)` reproduces the file edge-for-edge — the suite is re-runnable |
| `graph_statistics` (×60) | |E|, the degree statistics, the component decomposition and the isolated-node count in the manifest agree with the file |
| `distinct_graph_sha256` / `distinct_edge_set_sha256` | no two of the 60 instances are the same graph, by bytes or by edge set |
| `role_disjoint` | dev, eval and calibration are pairwise disjoint |
| `leakage_scan` / `leakage_needles` / `leakage_files` | no JSON file under `suite/**` (60 graphs + `manifest.json`) contains a planted label vector — both the compact and the spaced JSON spelling — or a label-bearing key |
| `generator_revision` | the manifest was produced by the generator revision on disk now |

```console
$ python3 a0/tasks/maxcut/generators/maxcut_suite.py verify
  canonical_reparse            60
  distinct_edge_set_sha256     1
  distinct_graph_sha256        1
  generator_revision           1
  graph_files                  60
  graph_keys                   60
  graph_regenerated            60
  graph_statistics             60
  graph_structure              60
  leakage_files                61
  leakage_needles              30
  leakage_scan                 1
  manifest_ids                 1
  role_disjoint                1
graphs verified: 60
PASS: canonical identity, structure, regeneration, statistics, disjointness and leakage all clean
```

`leakage_needles = 30` = 15 planted graphs × 2 spellings, over `leakage_files = 61` JSON files.
`generator_revision` is the one check that a legitimate edit to `maxcut_suite.py` will fail until the
suite is rebuilt — that is intentional: the manifest claims which revision produced the data.

---

## 7. Provenance, and the planted labels

`provenance.json` (schema `a0.maxcut.suite.provenance/v1`) holds one record per Planted instance:

```json
{"graph_id": "G_dev_0019", "role": "dev", "family": "Planted", "stratum": "k2sym",
 "seed": 2710780250033404024, "planted_labels": [1, 0, 1, 1, 0, ...],
 "planted_community_sizes": [64, 64]}
```

**The record is derived from the frozen file, and the audit says so.** `audit_labels.py refresh`
regenerates each Planted graph's edge list *and* label vector from that graph's own `generator` block
with the frozen generator, refuses to continue unless the edges reproduce the file byte-for-byte, and
writes the labels. An earlier revision of this file was **stale** — its seeds and vectors belonged to
a previous revision of the seed derivation and matched none of the 15 shipped graphs, which made
`verify`'s leakage scan search for vectors no file contains (finding F4;
`generators/DEVIATIONS.md` §4, `a0/verify/a1-testbed/REPORT.md` §2b).

**The honest statement of what is secret.** Nothing about the planted partition is *secret*: §2 keeps
`generator.params` + `generator.seed` in `graph.json` because that block is what makes regeneration a
check, so anyone holding the suite file and this generator can recompute the labels. What must hold —
and what the study actually needs — is that **the bytes handed to a candidate carry no `generator`
block at all**: `e_star.py` writes a candidate-facing view containing exactly
`schema, graph_id, family, n, edges` into the candidate's private run directory, masks `suite/**` from
the child, and records both digests in the Outcome (`graph_sha256` for the suite file,
`candidate_graph_sha256` for the handed bytes). The audit checks the view as well as the suite:

```console
$ python3 a0/tasks/maxcut/generators/audit_labels.py verify
planted graphs: 15
provenance records: 15
suite JSON files scanned with 15 x 6 label spellings: 61, hits: 0
candidate-facing views checked: 60 (keys == ['schema', 'graph_id', 'family', 'n', 'edges'])
PASS: the recorded labels are the labels of the frozen graphs, no spelling of them appears in
suite/**/*.json, and the candidate-facing view carries only schema/graph_id/family/n/edges
NOTE: the suite file itself still reproduces the labels (that is what makes regeneration a check);
the evaluator masks suite/** from a candidate and hands the view instead
```

Run it against the pre-fix `provenance.json` and it fails on all 15 graphs — which is the check that
`maxcut_suite.py verify`'s `leakage_*` counters never provided on their own. Those counters are still
meaningful now, because they search the corrected vectors.

`audit_labels.py` is a separate file on purpose: `suite/manifest.json` records
`generator.source_sha256`, so editing `maxcut_suite.py` would break `verify`'s `generator_revision`
check and move the suite's frozen identity. `maxcut_suite.py` is byte-identical to the frozen
revision.

`suite/README.md` §5 (frozen, and therefore not editable here) still describes the older, weaker
claim — "the labels are absent from `suite/`" — and quotes the older needles. It is superseded by the
statement above; `generators/DEVIATIONS.md` §4 records the discrepancy.

---

## 8. Freezing

```console
$ python3 a0/tasks/maxcut/generators/maxcut_suite.py record --commit <hash>
```

writes `FREEZE.json`:

```json
{"schema": "a0.maxcut.suite.freeze/v1", "commit": "<the commit that froze suite/>",
 "suite_version": "1.0.0", "generator_source_sha256": "...", "master_seed": 20260922,
 "manifest_sha256": "...", "manifest_counts": {"dev": 24, "eval": 24, "calibration": 12, "total": 60}}
```

The manifest does **not** contain the commit (it cannot: the commit does not exist until the data is
committed), so there is no circular dependency — `FREEZE.json` records the commit of the data-freezing
commit, and `manifest.json` records the generator source digest, which is what ties the two together.
