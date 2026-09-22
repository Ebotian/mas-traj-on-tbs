# `positive_control/` — the baseline `b_i` and the contract's positive control `PC_i`

Owner: the positive-control workstream of `a0/tasks/maxcut/`. Authority:
`../INTERFACE.md` (v1.1); the choices this directory had to make are in
`DEVIATIONS.md`, and the gate that consumes these artifacts is in `../gates/`.

## 1. What is here

| path | what it is |
|---|---|
| `baseline/solution.py` | **`b_i`** — one seeded uniform random bisection. A §4 candidate, nothing else |
| `pc/solution.py` | **`PC_i`** — NetworkX `one_exchange(G_i, initial_cut=b_i, seed=s_i)`, transliterated from the pin |
| `pc/pinned/networkx_maxcut_b69beb2c.py` | the pinned upstream file, verbatim (`793419aa…`) |
| `pc/pinned/networkx_init_b69beb2c.py` | the pinned commit's `networkx/__init__.py` (`3.7.1rc0.dev0`), verbatim |
| `manifest.json` | the frozen identity of both candidates: every file's sha256 *and* the whole-candidate `source_sha256` E* uses |
| `build.py` | `--freeze` / `--check`: re-derive the manifest with E*'s own resolver, and cross-check `b_i` against `C*(T1)`'s `c02` through the real ABI |
| `verify_pc_identity.py` | runs the transliteration and a real pinned NetworkX side by side, over the whole suite; writes `pc_identity_report.json` |
| `reference_one_exchange.py` | the reference arm of the above: run by an interpreter that has NetworkX, prints what it did (including the sha256 of the `maxcut.py` it actually loaded) |
| `bootstrap_pin.sh` | builds `.venv-pin` from the pinned commit (PyPI fallback accepted only if the `maxcut.py` is byte-identical) |
| `pc_identity_report.json` | the frozen evidence: `PASS`, 64 graphs, six checks |

Two frozen identities, in one line each:

```
b_i   source_sha256  6bfd919ed73c49dbb27fd2eb8f1f7224fac131773d7c8e1aa1f8b6ed09b24d97
PC_i  source_sha256  d3c12b54999415a199bdcd1c9bfed715a8e28147014a14083fe0bd502be3987f
```

## 2. The pin

    repository  https://github.com/networkx/networkx
    commit      b69beb2c4f6e480aaca4b0de7b4883f2b9f1030b   (2026-09-21, "Bump release version")
    file        networkx/algorithms/approximation/maxcut.py
    sha256      793419aac0d000051ab9f9e2f9a0c9018d94cc871a8c385131d8fe01ca9590fb
    licence     BSD-3-Clause
    function    one_exchange(G, initial_cut=None, seed=None, weight=None)

The same bytes are shipped in the networkx **3.6.1** wheel, so the commit pin
and the released version agree on this file; both were checked by running the
verification against two independent installs (§4).

**Why the pin is not the whole identity.** The pinned implementation shuffles a
fresh `list(G.nodes())` on every round (`seed.shuffle(nodes)`) and then takes
`max(..., key=cut_size)`, which returns the **first** maximiser — so the equal-gain
tie-breaks depend on the shuffle, and the shuffle depends on the seed. Freezing
`initial_cut` alone therefore does not pin the result. The frozen identity of one
PC run is:

    (graph_sha256, b_i, s_i, networkx_commit, interpreter_version)

with `s_i = 1337` (`gate_config.theta.seed`, the evaluator's own default, §4) and
`interpreter_version` because `random.Random(seed).shuffle` is CPython's
algorithm, not NetworkX's — see `DEVIATIONS.md` D-PC-2.

## 3. How `PC_i` is computed

```python
assignment = splitmix64(n, seed ^ 0xA5A5A5A5A5A5A5A5)      # == b_i, byte for byte
initial_cut = {v for v in range(n) if assignment[v] == 1}   # the orientation, frozen
value, cut, rounds = one_exchange(n, edges, initial_cut, random.Random(seed))
emit_partition([1 if v in cut else 0 for v in range(n)])
```

No score is written to the artifact: §3's partition is the only output, and E*
recomputes `cut_edges` from the graph and that partition (§5, §6).

## 4. Verify it

```bash
cd a0/tasks/maxcut/positive_control

# identity of the frozen trees, and b_i == C*(T1) c02 on all 60 frozen graphs,
# both through §4's real ABI
python3 build.py --check

# the pin, and the transliteration against the real thing
sh bootstrap_pin.sh
python3 verify_pc_identity.py \
    --reference-python "$PWD/.venv-pin/bin/python" \
    --report pc_identity_report.json
```

The second command prints `PC identity: PASS over 64 graphs (C1=True C2=True)`
and exits 0. Its six checks, all executable:

| check | what it asserts | result |
|---|---|---|
| C0 | the orientation convention: the reference arm's initial-cut size equals `b_i`'s `1`-count | PASS 64/64 |
| C1 | the vendored pinned file's sha256 is `793419aa…` | PASS |
| C2 | the NetworkX the reference interpreter *actually loaded* has that same `maxcut.py` sha256 — checked by content, not `__version__` | PASS |
| C3 | transliteration == real pinned NetworkX: same cut value **and** same partition | PASS 64/64 |
| C4 | the transliteration is a function of `(graph bytes, seed)`, and its returned value equals the cut recomputed from the partition it emitted | PASS 64/64 |
| C5 | `PC_i ≥ b_i` on every graph (one_exchange only accepts improving swaps) | PASS 64/64 |

`C3` was also run with a second, independently installed NetworkX
(`3.6.1` from a PyPI wheel, python 3.12) — PASS 64/64. The 64 graphs are the 60
frozen ones plus 4 generated into `tmp/` (ignored by git) so the check is not
only a statement about files one workstream produced.

## 5. What this is *not*

* **Not the B0+ experiment.** This is a task-admissibility pre-gate run by us,
  offline, *before* any campaign exists. B0+ asks a different question — whether a
  substrate can exploit an *injected* artifact — and needs the harness-owned
  evaluator, budget enforcement and unseen instances to answer it.
* **Not the `C*(T1)` candidate named `c01_ok_high_pc`.** That is a local-search
  heuristic; no definition of `PC` existed in the repository when it was frozen
  (`../README.md` says so explicitly). The contract's `PC` is the NetworkX call
  above, and it lives here.
* **Never given to a searching agent.** `pc/` contains NetworkX source inside the
  candidate tree; anything that materialises candidates into an agent workspace
  must exclude this directory (`DEVIATIONS.md` D-PC-5).
* **Zero model spend.** No key was read and no API call was made.
