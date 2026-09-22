# Deviations from `a0/tasks/maxcut/INTERFACE.md` — suite workstream

`INTERFACE.md` is the binding authority. This file exists so that nothing is silent. It is owned by
the suite workstream (`a0/tasks/maxcut/{suite,generators}/`); `INTERFACE.md` itself was not edited.

## Verdict

**No semantic deviation.** Every frozen requirement of `INTERFACE.md` §1, §2 and §9 that the suite
touches is implemented as written, and `maxcut_suite.py verify` re-checks the machine-checkable ones:

| requirement | status | evidence |
|---|---|---|
| §1 layout: `suite/{dev,eval,calibration}/`, ids `G_dev_0001…G_dev_0024`, `G_eval_0001…G_eval_0024`, `C_0001…`, `suite/manifest.json`, `generators/` for provenance | as specified | `build`; `verify` `graph_files 60` |
| §2 graph file carries exactly `schema, graph_id, family, n, edges, generator, notes` | as specified | `verify` `graph_keys 60` (exact key-set equality, not containment) |
| §2 canonical form `json.dumps(sort_keys=True, separators=(",",":"), ensure_ascii=True)` + one trailing newline | as specified | `verify` `canonical_reparse 60` re-serialises each file and compares bytes |
| §2 nodes `0..n-1`, no self-loops, no duplicate edges, each edge `[u,v]` with `u<v`, `edges` ascending, unit weights (no `weight` key) | as specified | `verify` `graph_structure 60` |
| §2 isolated nodes permitted **but** their count recorded per graph in `manifest.json` | as specified | `manifest.graphs[i].isolated_nodes`, cross-checked by `verify` |
| §2 `generator.seed` is provenance, not identity, and no verdict may reference it | as specified | the manifest's identity is the file sha256 (`distinct_graph_sha256`); the suite emits no verdict at all |
| §9 calibration disjoint from dev/eval and used for no algorithmic selection | as specified | independent seeded streams (`role` in the seed material); `verify` `role_disjoint 1`; `manifest.roles.calibration` states the prohibition |
| Work assignment: 24 dev + 24 eval (6 per family), ≥ 12 calibration, four families, `n=128` | as specified | `manifest.counts = {dev:24, eval:24, calibration:12, total:60}` |

## 1. Process deviation (location of this file)

`INTERFACE.md`'s header says a workstream that must deviate records it in **`a0/A1-DEVIATIONS.md`**.
The orchestrating assignment for this round instead says: *"write the deviation and its justification
into `DEVIATIONS.md` inside your own directory; … never edit the interface file"*, and
`a0/A1-DEVIATIONS.md` is outside this workstream's owned paths. This file is therefore at
`a0/tasks/maxcut/generators/DEVIATIONS.md`, and **`a0/A1-DEVIATIONS.md` was not touched**. If the
contract owner wants the record consolidated upstream, this file is the source to copy; nothing here
is hidden by the different location.

## 2. Interface gaps this workstream had to fill (not deviations — the interface is silent)

Recorded here because downstream consumers (`e_star.py`, `candidates/`, `references/`) have to read
what I emit, and none of it is specified by `INTERFACE.md`.

1. **`suite/manifest.json` has no schema in `INTERFACE.md`.** §1 requires the file and says it carries
   "per-graph sha256, family, n, |E|, statistics"; §2 adds the isolated-node count. I defined
   `"schema": "a0.maxcut.suite.manifest/v1"` with: `n`, `counts`, `canonical_form`, `identity`,
   `roles`, `generator` (`name`, `version`, `source_sha256`), `generator_config` (the whole frozen
   configuration), `separation` (the sampling rule and the overlap counts), `family_summary`, and
   `graphs[]` — each entry carrying `graph_id, role, path, family, stratum, n, edges, graph_sha256,
   generator{name,version,params,seed}, degree{min,max,sum,median,mean,mean_fraction,std_floor,
   histogram}, components{count,sizes,largest,connected}, isolated_nodes, edge_set_sha256`.
   `graph_id`/`path` are the join keys a consumer needs; `degree.histogram` is the authoritative
   degree distribution (integers), while `mean`/`median`/`std_floor` are display strings.
2. **The calibration set's size is not specified** (§1 writes only `C_0001.json …`; §9 constrains it
   to be disjoint and non-selective). This suite has 12 — the assignment's minimum, one independent
   draw per (family, stratum) cell. It is kept small deliberately: `INTERFACE.md` §9 makes
   `T_wall = 30 min` the binding constraint, and the calibration step consumes wall clock from the
   same budget. `config.reps.calibration` is the knob if a denser latency sample is wanted.
3. **Probability parameters are exact rationals** (`p_num`/`p_den`) with the decimal spelling carried
   alongside, and the generators use integer comparisons rather than binary64. `INTERFACE.md` does not
   constrain this; it is done so that the suite is a function of `(params, seed)` alone, in the same
   spirit as §5's "the winner is decided on integers".
4. **Statistics are computed from the frozen edge list by integer arithmetic** (`sum`, histogram,
   component sizes are integers; `median` is exact; `mean` is exact because `n = 128` is a power of
   two; `std_floor` is truncated from an integer square root). No float enters any frozen field.
5. **`generators/nontriviality_probe.json` is non-normative.** It holds random-partition and
   1-exchange cut fractions used to justify the parameters. It is **not** `R_i/OPT_i/U_i` and must not
   be consumed as a reference; `references/` owns those. The file says so in its own `role` field.

## 3. Known limitations (stated, not hidden)

* **`ba_preferential` is a documented variant** of Barabási–Albert (seed graph `K_{m+1}`; targets
  sampled without replacement by rejection). Regenerating with NetworkX's `barabasi_albert_graph`
  will not reproduce these files; regenerating with `generators/maxcut_suite.py` will.
* **Eight of the 60 graphs contain isolated nodes** (15 in total), concentrated in `ER` at `p = 0.030`
  and `p = 0.050`. This is permitted by §2 and recorded per graph, but a consumer that silently
  assumes connectivity would be wrong; the smallest largest-component is 123/128 and no graph has zero
  edges.
* **`ER p=0.030` instances are occasionally fragmented** (up to 6 components, all but the giant one
  being singletons). This is a property of the sparse regime, kept deliberately: it is the regime with
  the most headroom (§3 of `generators/README.md`).

## 4. `provenance.json` was stale; it is now derived from the frozen files (finding F4)

**What was wrong.** `INTERFACE.md` §2 lets a graph carry a `generator` block of
*distribution* parameters, and `suite/README.md` §5 promises that the Planted
families' label vectors are absent from the candidate-readable surface. The
promise was checked by searching `suite/**/*.json` for the vectors recorded in
`generators/provenance.json` — but those vectors were **not the labels of any
shipped graph**. Measured before this change (`a0/verify/a1-testbed/REPORT.md`
§2b): for all 15 Planted graphs the recorded `seed` differs from the graph's
`generator.seed` (e.g. `G_dev_0019`: provenance `10591771958253030697`, graph
`2710780250033404024`), the recorded vectors carry no community structure
(intra/inter density 0.062/0.062 against a declared `p_in/p_out` of 0.100/0.020),
and `master_seed` read `777` while the suite was built at `20260922`. The check
was green because it searched for vectors no shipped graph contains.

**What it is now.** `audit_labels.py refresh` regenerates each Planted graph's
edge list *and* label vector from that graph's own frozen `generator` block with
the frozen generator, refuses to proceed unless the edges reproduce the file
byte-for-byte, and writes the labels into `provenance.json`. So the recorded
labels are the labels of the graph on disk — or the tool fails.

**Why a new file instead of editing `maxcut_suite.py`.** `suite/manifest.json`
records `generator.source_sha256`, and `maxcut_suite.py verify` fails if the file
on disk hashes differently. Editing it would break the frozen suite's own
identity check, so the audit moved to `generators/audit_labels.py` and
`maxcut_suite.py` is byte-identical. `maxcut_suite.py verify`'s own
`leakage_*` counters are *not* inert any more either: with the corrected
provenance they now search for the true label vectors.

**What the audit checks** (`python3 generators/audit_labels.py verify`):
1. every recorded label vector equals the vector the frozen file regenerates, and
   every recorded seed equals the graph's `generator.seed` (this check fails
   against the old `provenance.json` — that is how F4 was reproduced);
2. no spelling of the true labels (compact/spaced 0/1, compact/spaced `±1`,
   decimal bitmask or per-class bitmasks, class-membership lists) occurs in
   `suite/**/*.json` — 61 files, 15 x 6 needles, 0 hits;
3. the *candidate-facing view* of every graph carries exactly
   `{schema, graph_id, family, n, edges}` and no `generator`/`notes`, and no
   spelling of the true labels appears in it.

**The honest limitation, restated.** The suite file itself still reproduces the
labels: §2 keeps the `generator` block because that is what makes regeneration a
check, and the block plus the frozen generator *is* the label vector. The
property the study needs is therefore not "the labels are absent from the suite"
but "the labels are absent from what a candidate is handed". That is now the
checked statement: `e_star.py` hands over `candidate_graph_document()` and masks
`suite/**` from the child. `suite/README.md` §5 (frozen, uneditable) still
describes the old, weaker claim; this section supersedes it.
