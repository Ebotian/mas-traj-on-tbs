# `positive_control/` — the baseline `b_i` and the contract's positive control `PC_i`

Owner: the positive-control workstream of `a0/tasks/maxcut/`. Authority:
`../INTERFACE.md` (v1.1); the choices this directory had to make are in
`DEVIATIONS.md`, and the gate that consumes these artifacts is in `../gates/`.

## 1. What is here

| path | what it is |
|---|---|
| `baseline/solution.py` | **`b_i`** — one seeded uniform random bisection. A §4 candidate, nothing else |
| `variants/pc_exchange_k10/solution.py` | **`PC_i`, adopted 2026-09-23** — NetworkX `one_exchange(G_i, initial_cut=b_i, seed=s_i)`, transliterated from the pin, **stopped after 10 accepted improving swaps**. The gate reads it by default (`../gates/REVISION-PROPOSAL.md` §6.1) |
| `pc/solution.py` | **history — superseded, kept** — the same transliteration run to a local optimum (`MAX_SWAPS = None`, i.e. the pin). It failed the ρ half of the gate and left the task inadmissible; bytes, verdicts and pin evidence are unchanged |
| `pc/pinned/networkx_maxcut_b69beb2c.py` | the pinned upstream file, verbatim (`793419aa…`) |
| `pc/pinned/networkx_init_b69beb2c.py` | the pinned commit's `networkx/__init__.py` (`3.7.1rc0.dev0`), verbatim |
| `variants/pc_exchange_k{01,02,05,25}/` | the same candidate with `MAX_SWAPS` set to `k`: the truncation lever, as frozen §4 candidates. **History** — measured candidates for the 2026-09-23 decision; none was adopted |
| `PC-REVISION.md` / `HISTORY.md` | the revision record for the adopted PC, and the index of every control this directory has owned |
| `make_variants.py` | `--write` / `--check`: generates the variants from `pc/solution.py` and verifies each differs from it by exactly one line |
| `manifest.json` | the frozen identity of every candidate above: each file's sha256 *and* the whole-candidate `source_sha256` E* uses |
| `build.py` | `--freeze` / `--check`: re-derive the manifest with E*'s own resolver, and cross-check `b_i` against `C*(T1)`'s `c02` through the real ABI |
| `verify_pc_identity.py` | runs the transliteration and a real pinned NetworkX side by side, over the whole suite; writes `pc_identity_report.json` |
| `reference_one_exchange.py` | the reference arm of the above: run by an interpreter that has NetworkX, prints what it did (including the sha256 of the `maxcut.py` it actually loaded) |
| `bootstrap_pin.sh` | builds `.venv-pin` from the pinned commit (PyPI fallback accepted only if the `maxcut.py` is byte-identical) |
| `pc_identity_report.json` | the frozen evidence: `PASS`, 64 graphs, six checks |

Frozen identities, one line each:

```
b_i                6bfd919ed73c49dbb27fd2eb8f1f7224fac131773d7c8e1aa1f8b6ed09b24d97
PC_i (adopted)     ee49eba0798028532c2bcf084b56b137e19937a827105da97c75ed5a01e759da  # = pc_exchange_k10, since 2026-09-23
PC_i (superseded)  25de3e5d496198d74c7427de0d4504a0f3e49e8056c154d8eb8197648bcfb901  # = pc/, local optimum, history
pc_exchange_k01    69cbaccde91cbcbd7f19730c6c64328e9b4192b2a42b4257c5affe0a495727b2
pc_exchange_k02     ce125f72f1d95efdf1d80ef1a66686e9693ea95389b8cd4a2ba24385302187c0
pc_exchange_k05     8085adcf9f46d0a3b8a89ede85f3ed9631935f2527f32d2f64be69ee6c5f8b74
pc_exchange_k10     ee49eba0798028532c2bcf084b56b137e19937a827105da97c75ed5a01e759da  # adopted
pc_exchange_k25     43a03d0d3e7268ae7ce4b554bad227896e4b4331ae76ee2e51e9d0d417509aeb
```

`PC_i`'s digest moved from `d3c12b54…` on 2026-09-22 when `MAX_SWAPS` was added
to its source (`DEVIATIONS.md` D-PC-7) — inert at the time, because the
contract's PC was still `None`. It moved again on **2026-09-23**, this time as a
decision: `25de3e5d…` (local optimum) → `ee49eba0…` (`k = 10`). That second move
is a contract revision with its own record (`PC-REVISION.md`), and it is the
reason the file you are reading no longer describes `pc/` as *the* PC. The
pin-equality check (`pc_identity_report.json`, C1–C5) is a statement about the
shared transliteration source and is unaffected by `MAX_SWAPS`.

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
value, cut, rounds = one_exchange(n, edges, initial_cut, random.Random(seed), MAX_SWAPS)
emit_partition([1 if v in cut else 0 for v in range(n)])
```

`MAX_SWAPS = None` runs the loop to a local optimum, which is the pin verbatim.
`MAX_SWAPS = k` stops it after `k` *accepted improving* swaps, checked at the top
of the round so the round that finds no improvement still terminates the loop the
pin's way. The `k` variants are the truncation lever measured in
`../gates/strength_table.json`; **the contract adopted `k = 10` on 2026-09-23**
(`PC-REVISION.md`), so `MAX_SWAPS = 10` is now the value the gate runs by
default, and `pc/` with `MAX_SWAPS = None` is history.

No score is written to the artifact: §3's partition is the only output, and E*
recomputes `cut_edges` from the graph and that partition (§5, §6).

## 4. Verify it

```bash
cd a0/tasks/maxcut/positive_control

# identity of the frozen trees, and b_i == C*(T1) c02 on all 60 frozen graphs,
# both through §4's real ABI
python3 build.py --check

# the truncations are the frozen PC with one line changed -- verified, not asserted
python3 make_variants.py --check

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
  above, stopped at `k = 10` since 2026-09-23, and it lives here. Note that
  `../INTERFACE.md` — the interface authority — *still* defines `PC_i` nowhere;
  the definition this directory implements is recorded in `PC-REVISION.md` §7 and
  it is the coordinator's to move into the contract.
* **Never given to a searching agent.** `pc/` contains NetworkX source inside the
  candidate tree; anything that materialises candidates into an agent workspace
  must exclude this directory (`DEVIATIONS.md` D-PC-5).
* **Zero model spend.** No key was read and no API call was made.
