# `positive_control/` deviations and interpretation notes

Owner: the positive-control workstream of `a0/tasks/maxcut/`. Authority:
`../INTERFACE.md` (v1.1) and the task assignment that named this directory.
Nothing here is silent: each entry names the clause that left a choice open,
what was chosen, and why. `../INTERFACE.md` was not edited.

---

## D-PC-1 — `PC_i` is a line-for-line transliteration of the pin, not `import networkx`

**Clause.** §4 runs the candidate as a subprocess in a *private* scratch
directory with a minimal environment, no injected files and no network.

**What was done.** `pc/solution.py` contains the pinned `one_exchange` loop
transcribed verbatim from `pc/pinned/networkx_maxcut_b69beb2c.py` (lines
118-143), with the pin's two helpers (`_swap_node_partition`, and
`cut_size(edges, cut)` as the unweighted reading of
`nx.algorithms.cut_size(G, cut, weight=None)`) and `seed` realised exactly as
the pin's `@py_random_state(2)` does for an integer: `random.Random(seed)`.

**Why.** A candidate that imported the ambient `networkx` would have an identity
that is *whatever happens to be installed* — the opposite of §5's
`candidate_source_sha256`. The transliteration's identity is its own bytes.

**Why that is not a drift risk here.** The obvious objection — a transliteration
can disagree with the thing it copies — is discharged by execution, not by
argument: `verify_pc_identity.py` runs *both* the transliteration and a real
NetworkX install and requires the returned cut value **and** the returned
partition to be equal. It is run over all 60 frozen graphs plus 4 non-suite
graphs, against **two independent installs**:

| install | networkx | python | `maxcut.py` sha256 | result |
|---|---|---|---|---|
| `pc/.venv-pin` (`pip install git+…@b69beb2c…`) | `3.7.1rc0.dev0` | 3.14.7 | `793419aa…` | PASS, 64/64 |
| `~/openevolve/.venv-llm4ad` (PyPI wheel) | `3.6.1` | 3.12 | `793419aa…` | PASS, 64/64 |

`pc_identity_report.json` is the pinned-venv run. The `3.6.1` wheel and the
pinned commit ship a byte-identical `maxcut.py`, so the commit pin and the
released version agree on the function that matters; both are recorded rather
than one being assumed.

---

## D-PC-2 — `PC_i`'s identity includes the interpreter version; `b_i`'s does not

**Clause.** §5 records `interpreter.{implementation,version,executable}` in every
Outcome; §2 refuses to let an RNG implementation into a graph's identity.

**What was done.** Two different and deliberate RNG choices:

* **`b_i` uses splitmix64** (the stream the frozen suite's own generators use),
  so `b_i` is a function of `(graph bytes, seed)` under any CPython.
* **`PC_i` uses `random.Random(seed).shuffle`**, because that *is* the pin's
  behaviour and cannot be replaced without changing what `PC` means.

**Consequence, stated rather than hidden.** `random.Random.shuffle`'s result is a
property of CPython's `random` module (the `_randbelow`-based algorithm, stable
from 3.11 onwards), not of NetworkX. So PC's frozen identity is the tuple

    (graph_sha256, b_i, s_i, networkx_commit, interpreter_version)

and byte-for-byte reproducibility of the PC run is claimed **for a fixed
interpreter**, which §5 already stamps into every Outcome. A re-run under a
different CPython major version must re-check `pc_identity_report.json`; the two
installs above (3.12 and 3.14) do agree today.

---

## D-PC-3 — the orientation of `initial_cut` is part of the identity

**Clause.** The assignment writes `one_exchange(G_i, initial_cut=b_i, seed=s_i)`
without saying how a `b_i` that is an *assignment vector* becomes an
`initial_cut`, which is a *set of nodes*.

**What was done.** Frozen as `initial_cut = { v : b_i[v] == 1 }`, and the graph
is built with `add_nodes_from(range(n))` so that `G.nodes()` is `0..n-1`, the
order the pin's `list(G.nodes())` assumes.

**Why it matters.** The complement of `b_i` has the *same cut value* but a
different search trajectory, so it is not a free choice: two implementers could
each be "using b_i" and get different answers. `verify_pc_identity.py`'s check
C0 pins the orientation by requiring the reference arm's initial-cut size to
equal the baseline's `1`-count on every graph.

---

## D-PC-4 — `b_i` is bit-identical to `C*(T1)`'s `c02_ok_low_baseline`, on purpose

`baseline/solution.py` uses the same splitmix64 stream with the same keying
constant (`0xA5A5A5A5A5A5A5A5`) as `../candidates/c02_ok_low_baseline`, so the
two programs emit **byte-identical** `partition.json` on all 60 frozen graphs.
`build.py --check` verifies that through §4's real ABI (`run_invocation`), not by
reading either source.

**Why.** The repository should have one baseline, not two that happen to agree.
This keeps `c02`'s frozen conformance evidence (`conformance.report.json`,
`G_dev_0001` → 132) usable as evidence about `b_i`, while `b_i` still carries its
own frozen bytes and digest in `manifest.json`.

---

## D-PC-5 — the pin is inside the candidate tree, so it is inside `candidate_source_sha256`

`pc/` contains `pinned/networkx_maxcut_b69beb2c.py` and
`pinned/networkx_init_b69beb2c.py`. `e_star_child.candidate_files` hashes every
file in the candidate directory except dot-directories and `__pycache__`, so both
pins enter `candidate_source_sha256` (`d3c12b54…`). That is intended — the pin
*is* part of PC's identity — and it is why `manifest.json` lists four files for
`pc/`, only one of which is the entry.

**Consequence for the later experiment.** This directory contains NetworkX
source. The assignment says the PC's source is never given to a searching agent
and that PC is not the B0+ experiment. Anything that materialises candidate
directories into an agent's workspace must exclude `positive_control/pc/`.

---

## D-PC-6 — the pin was fetched over the network, with the host proxy unset

The host exports `http_proxy=http://127.0.0.1:7890`, and that proxy refuses TLS
(`curl: (35) TLS connect error … unexpected eof`). The pinned bytes were
therefore fetched directly (`curl --noproxy '*'`) from
`raw.githubusercontent.com/networkx/networkx/b69beb2c…`, and NetworkX was
installed from the same commit into `pc/.venv-pin` with the proxy variables
unset.

This is recorded because a pin that can only be re-fetched through a network path
someone has to guess is not a reproducible identity on its own. What makes it
reproducible offline is the sha256: `793419aa…` for `maxcut.py`, `ec29aaa9…` for
`networkx/__init__.py`, plus the commit sha and the exact `pip` command in
`README.md` §6.

---

## Considered and deliberately not done

* **No model spend.** The assignment allows none for this task, and none was
  used: no API call was made and no key was read.
* **The calibration set is not used.** §9 forbids using
  `suite/calibration/**` for anything but resource rates, and a gate is a
  selection-adjacent judgement, so `gate_runner.py` never touches it.
* **`eval` is not used to decide anything.** Its numbers exist, are reported,
  and are written to a *separate* file (`gates/verdict.eval.json`), so §12's
  "eval must not enter any visible path" is not weakened by the fact that the
  gate runner is capable of reading it.
