# `C*` — the fixed candidate set for the plumbing task

14 candidates, each a self-contained directory holding the complete candidate
source (`solution.py`, the upstream entry point) plus `candidate.json` (identity,
version, kind, purpose). Nothing here is a pointer to a mutable worktree: the
bytes in this directory *are* the candidate, and `manifest.json` freezes the
sha256 of every `solution.py`.

`manifest.json` follows `a0.candidateset/v1` (the shape
`a0/contract/adapter_contract.md` §2 consumes) and additionally carries this
workstream's provenance keys (`kind`, `purpose`, `expected_status_at_theta_e_star`,
`designed_relations`).

Rebuild and verify the tree with:

```bash
.venv/bin/python tools/build_c_star.py --check
.venv/bin/python tools/build_c_star.py --write
```

`c01_good_hex`'s geometry is the recorded output of
`tools/make_good_packing.py` (see `tools/good_packing_26.json`); every other
member is a small, hand-written variation on it, so the whole set is
reproducible from those two files.

The `E*` column below is the objective at `theta_E* = seed 1337, fidelity full`
(`E_STAR.json`); the exact command per candidate is recorded there too.

| candidate | role | E\* objective | E\* status (exit) | reason it exists |
|---|---|---|---|---|
| `c01_good_hex` | good | 2.4519205208433132 | ok (0) | high end of the required ordered pair; leaves headroom above the baseline for A1/B0 |
| `c02_baseline_upstream` | baseline | 0.25 | ok (0) | low end of that pair; verbatim upstream `solution.py`@`b91c090`, i.e. SimpleLoop's `c_0` |
| `c03_mirror` | tie | 2.4519205208433132 | ok (0) | exact tie with `c01`, different content |
| `c04_near_tie` | tie | 2.4518205208433135 | ok (0) | near-tie with `c01` (Δ ≈ 1e-4) |
| `c05_overlapping` | bad | `null` | invalid (2) | one fully overlapping pair: overlap gate |
| `c06_empty` | bad | `null` | invalid (2) | returns nothing: count gate |
| `c07_single` | bad | `null` | invalid (2) | one valid circle: count gate only |
| `c08_out_of_bounds` | bad | `null` | invalid (2) | whole packing translated out of the square: bounds gate only |
| `c09_malformed_import` | bad | `null` | error (3) | `solution.py` does not parse |
| `c10_raises` | bad | `null` | error (3) | `pack_circles` raises |
| `c11_non_deterministic` | bad | `null` | error (3) | valid geometry, different radii per call |
| `c12_exit_without_artifacts` | bad | `null` | error (3) | kills the runner with `os._exit(0)`: no artifact, exit code 0 |
| `c13_slow` | bad | `null` | error (3) | valid geometry behind a 0.3 s sleep: p50 budget |
| `c14_near_zero` | bad | 2.600000000000001e-05 | ok (0) | a *genuine* near-zero score |

## The required relations

**Ordered pair with a decidable margin.** `E*(c01) = 2.4519205208433132` and
`E*(c02) = 0.25`; the margin is ≈ 2.2, which is ~4.4×10¹⁵ ULP at this magnitude
— no tolerance, rounding rule or rank transform can absorb it. `c02` is the
upstream baseline itself, so A0.2's "assert the next parent is `c1`" runs against
the study's own `c_0`.

**Tied pair, identical structure, different content.** `c03_mirror` is `c01`
reflected across the main diagonal (`x` and `y` swapped). Reflection is an exact
isometry of the unit square, so `objective`, `structure`, `fields` and even
`validity.checks` are **bit-identical** to `c01`'s while the source bytes differ:

```
c01 solution.py sha256 bca4286e…f4a6d   (2867 bytes)
c03 solution.py sha256 893d0aa4…f6fcf   (2849 bytes)
```

So: yes, there is a pair with identical structure and different content. Its
`canonical_digest` differs from `c01`'s only because the Outcome records the
candidate's content hash — that is the point of the pair: a runtime that
identifies candidates by *content* scores them identically; one that keys a cache
by *path* or keeps stale state can be caught by running the pair in either order.

**Near-tied pair.** `c04_near_tie` shrinks one radius by 1e-4. Shrinking a radius
can neither break the square bounds nor create an overlap, so the geometry stays
valid and only the objective moves: Δ = `1.0000000000021e-04` (the deviation from
exactly 1e-4 is the binary64 summation error, not a design slack).

**Genuine near-zero.** `c14_near_zero` returns 26 circles of radius 1e-6:
`E*(c14) = 2.600000000000001e-05`, a real number ~5 orders of magnitude below the
baseline. It exists so that the degenerate members cannot be confused with a low
but real score: `E*(c14)` is a number, `E*(c06)` is `null`.

## Degenerate members, and raise-versus-return

Four members return *something* that E\* then rejects on geometry grounds —
`status="invalid"`, `objective=null`, exit code 2, with structural diagnostics
still present (e.g. `c05_overlapping` reports `overlap_count=1`,
`min_gap=-0.1886`). These are distinguishable from a zero score in three
independent ways: the objective is `null` rather than `0.0`, `scored` is `false`,
and the exit code is non-zero.

Five members are expected to make E\* **fail rather than return a measurement**:
`c09`–`c13`, `status="error"`, `objective=null`, exit code 3. `c12` is the
sharpest: the candidate kills the runner with `os._exit(0)`, so the *process exit
code is 0* and the only signal is the missing artifact marker
(`failure.kind="child_terminated_early"`). An adapter that trusts a clean exit
code, or that maps "no objective" to `0.0`, produces exactly the false green
A0.1 is designed to find.

One further case is worth stating explicitly: E\* does **not** raise an uncaught
exception for any member of `C*`. It always writes the Outcome and signals the
outcome class through the exit code (0/2/3). Only an unreadable candidate path
makes E\* exit 3 without writing `--out` at all (it never writes a partial or
zero-valued Outcome).
