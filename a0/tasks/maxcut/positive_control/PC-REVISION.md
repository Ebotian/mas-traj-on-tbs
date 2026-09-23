# `PC-REVISION.md` — the positive control of T1 is revised to the bounded-round variant at `k = 10`

**Status: ADOPTED, 2026-09-23.** This is a **contract revision**, not a local
change: the gate thresholds do not move, the suite does not move, `E*` does not
move, and no other workstream's directory is touched. Only the identity of the
positive control `PC_i` moves.

* **Evidence scope type: `instrumentation`.**
* **Decision owner:** the coordinator (this file records the decision that was
  put in front of them by `../gates/REVISION-PROPOSAL.md`, now marked ADOPTED).
* **Where the gate now reads its control:** `../gates/gate_runner.py`,
  `DEFAULT_PC = positive_control/variants/pc_exchange_k10`. The un-suffixed
  `python3 gates/gate_runner.py --set dev|eval` now evaluates the revised PC and
  issues `ADMISSIBLE` on both sets.

---

## 1. Old control and new control, with file digests

Both are frozen §4 candidates. `source_sha256` is
`e_star_child.candidate_source_digest` over the candidate's files — i.e. exactly
the `candidate_source_sha256` that E* stamps into every Outcome. The per-file
digests are the ones recorded in `manifest.json`.

### Old control — the unbounded local optimum (now history)

| field | value |
|---|---|
| path | `positive_control/pc/` |
| candidate_id | `pc01_external_networkx_one_exchange` |
| procedure | `one_exchange(G_i, initial_cut=b_i, seed=s_i)` run to a local optimum (`MAX_SWAPS = None`) |
| `source_sha256` | `25de3e5d496198d74c7427de0d4504a0f3e49e8056c154d8eb8197648bcfb901` |
| `solution.py` sha256 | `1d488d6e956f584aa8495a1b287a43766fe3b5aed6d4fea066e7403d080e2149` |
| `candidate.json` sha256 | `036b5ef7afc8c93cf3b0b626777c8c07e9ea2eb59c3c8311a543b2ea4d4c8a05` |
| `pinned/networkx_maxcut_b69beb2c.py` sha256 | `793419aac0d000051ab9f9e2f9a0c9018d94cc871a8c385131d8fe01ca9590fb` |
| `pinned/networkx_init_b69beb2c.py` sha256 | `ec29aaa9f39edc35a6bc752099756f44c0153e4e2391f80f817e14808c0e4d15` |
| its verdicts | `../gates/verdict.dev.json`, `../gates/verdict.eval.json` (both `NOT_ADMISSIBLE`) |

### New control — the adopted bounded round

| field | value |
|---|---|
| path | `positive_control/variants/pc_exchange_k10/` |
| candidate_id | `pc_exchange_k10` |
| procedure | the same pinned `one_exchange(G_i, initial_cut=b_i, seed=s_i)`, stopped after 10 accepted improving swaps (`MAX_SWAPS = 10`) |
| `source_sha256` | `ee49eba0798028532c2bcf084b56b137e19937a827105da97c75ed5a01e759da` |
| `solution.py` sha256 | `13a353a22a2cd35c32ce6ced3111d7f01b0dd14e5e876858a7dbd8d14d7ccc58` |
| `candidate.json` sha256 | `691d4ef962f50d5bbebfb61fd0e8a382283858010a6bd35264348e44364a6b65` |
| its verdicts | `../gates/verdict.dev.pc_exchange_k10.json`, `../gates/verdict.eval.pc_exchange_k10.json` (both `ADMISSIBLE`) |

**The new control is the old control with one line changed.** Verified, not
asserted:

```
$ diff positive_control/pc/solution.py positive_control/variants/pc_exchange_k10/solution.py
71c71
< MAX_SWAPS = None
---
> MAX_SWAPS = 10
$ python3 positive_control/make_variants.py --check     # → "verdict": "PASS", 0 failures
```

The pin, the shuffle stream, the first-maximiser tie-break and the
`initial_cut = {v : b_i[v] == 1}` orientation are all unchanged. The
transliteration-vs-pin identity evidence (`pc_identity_report.json`, checks
C0–C5) is a statement about that shared source and therefore still holds.

### History item

The old control is **kept, and must not be deleted**: the directory
`positive_control/pc/` and its frozen bytes are unchanged, its verdicts
`../gates/verdict.{dev,eval}.json` are unchanged, and it is still reachable with
an explicit `--pc positive_control/pc`. It is labelled as superseded in
`HISTORY.md`, in `../gates/REVISION-PROPOSAL.md` §2/§7, and in
`../gates/README.md`.

---

## 2. The criterion, written before the answer

From `../gates/REVISION-PROPOSAL.md` §6, written and frozen **before** the
strength curve below was complete, so that the recommendation is reproducible
from the table rather than eyeballed. A replacement PC should

1. pass **both** gates on dev **and** eval with **all four families** clear of
   each bar — not on the 3-of-4 rule;
2. clear both bars by at least **2×** on both sets; and
3. among those, be the **strongest** variant.

The thresholds themselves were frozen earlier still, in
`../gates/gate_config.json`, and `INTERFACE.md` §12 forbids relaxing them:
Δ ≥ 0.03 overall and ≥ 0.02 per family in ≥ 3 of 4 families; ρ global median
≥ 0.30 and family median ≥ 0.30 in ≥ 3 of 4 families; plus the saturation veto
(baseline headroom median ≥ 1/20 and no graph with `T_i == b_i`).

---

## 3. The full measured table

The lever is "the same published procedure, stopped by a budget rather than by
optimality". Every row is a frozen §4 candidate evaluated by `E*` on the frozen
suite; Δ and ρ are exact rationals (decimals shown are display fields).

| variant | `MAX_SWAPS` | Δ dev | Δ eval | ρ dev | ρ eval | Δ families (dev/eval) | ρ families (dev/eval) |
|---|---|---|---|---|---|---|---|
| `pc_exchange_k01` | 1 | `0.018221` | `0.017983` | `0.940123` | `0.942883` | 1/4, 1/4 | 4/4, 4/4 |
| `pc_exchange_k02` | 2 | `0.032882` | `0.033074` | `0.895644` | `0.894196` | 4/4, 4/4 | 4/4, 4/4 |
| `pc_exchange_k05` | 5 | `0.069658` | `0.070200` | `0.775149` | `0.762308` | 4/4, 4/4 | 4/4, 4/4 |
| **`pc_exchange_k10`** | **10** | **`0.116585`** | **`0.116427`** | **`0.615639`** | **`0.600847`** | **4/4, 4/4** | **4/4, 4/4** |
| `pc_exchange_k25` | 25 | `0.204898` | `0.202023` | `0.325903` | `0.301163` | 4/4, 4/4 | 3/4, **2/4** |
| `pc` (old control) | ∞ | `0.247943` | `0.238448` | `0.158820` | `0.178716` | 4/4, 4/4 | **0/4, 0/4** |

Applying the pre-registered criterion:

| k | (1) 4/4 on both sets | (2) min margin ≥ 2× | (3) strongest |
|---|---|---|---|
| 1 | no (Δ 1/4) | no (0.61×) | — |
| 2 | yes | **no** (Δ 1.10×) | — |
| **10** | **yes** | **yes** (min `2.00×`, eval ρ) | **the strongest that qualifies** |
| 5 | yes | yes (2.32×) | weaker than 10 |
| 25 | **no** (eval ρ 2/4) | no (1.00×) | — |

**`k = 25` passes on dev and fails on eval**, so the 3-of-4 rule is not a safety
net and the choice could not have been made on dev alone. Machine-readable:
`../gates/strength_table.json`; re-derive with `python3
../gates/strength_table.py`.

### The adopted verdicts

| set | verdict | Δ mean | ρ median | families (Δ / ρ) | evidence |
|---|---|---|---|---|---|
| dev | **`ADMISSIBLE`** | `0.116584858` | `0.615639328` | 4/4 / 4/4 | `../gates/verdict.dev.pc_exchange_k10.json` |
| eval | **`ADMISSIBLE`** | `0.116426731` | `0.600847458` | 4/4 / 4/4 | `../gates/verdict.eval.pc_exchange_k10.json` |

Both reproduce the `k = 10` row of the table exactly; no decision field moved
against the measured curve (see §5).

---

## 4. Post-hoc caveat — a posterior degree of freedom

We measured ρ for the contract's `PC_i`, saw it fail the gate, and only then went
looking for a weaker artifact, so the choice of `k` was made after the value of ρ
was known; this is therefore a posterior degree of freedom, and it is declared
here rather than spent quietly. The thresholds were frozen before any of this was
measured and do not move, the suite and `E*` do not move, and the criterion in §2
was written before the answer was known, so the *selection* is reproducible by
anyone — but the *fact that a selection was made at all* is a real cost to the
task's claim, because weakening the artifact weakens the very improvement the
task exists to demonstrate (Δ falls from `0.2479` to `0.1166`, a factor of 2.1).
A reader who considers this degree of freedom unspendable should return
`NOT_ADMISSIBLE` and re-draw the suite instead; that is a legitimate answer and
needs no declaration.

---

## 5. Evidence scope, and what this revision may and may not support

**Evidence scope type: `instrumentation`.** Every number in this file is a
statement about the assay — the evaluator, the frozen suite, the target
references and the positive control — not a statement about the world, and not a
result of any campaign. The gate exists to decide whether the *instrument* can
measure anything on this task at all.

> **The value of ρ for the new control is a property of the assay and MUST NOT be
> used as evidence about the world.**

Two consequences, both checked rather than asserted:

* **The revision moved no decision number.** The re-run rewrote no stored
  Outcome and no stored verdict: immediately after
  `python3 gates/gate_runner.py --set dev` and `--set eval` under the revised
  default, `git status --short -- a0/tasks/maxcut/gates
  a0/tasks/maxcut/positive_control` named `gate_runner.py` and nothing else. The
  two identity instruments then report identity-only movement against the
  pre-re-stamp revision `7bf8a14b`, with **0 decision leaves**:
  `../gates/refreeze.evidence.json` (12/12 verdicts, 1 identity leaf each) and
  `../gates/restamp.evidence.json` (576/576 Outcomes, 6 identity leaves each).
* **The prohibition is not decorative.** `ρ` is a property of `(b_i, p_i, T_i)`
  for a chosen artifact on a chosen suite; quoting it as if it measured the
  difficulty of max-cut, or the value of open-world search, would be a category
  error. `PC-REVISION.md` binds the number to `instrumentation` scope.

---

## 6. Reproduce

```bash
cd a0/tasks/maxcut

# the adopted control, by default, on both sets — must read ADMISSIBLE
python3 gates/gate_runner.py --set dev
python3 gates/gate_runner.py --set eval

# the old control, for comparison — still NOT_ADMISSIBLE
python3 gates/gate_runner.py --set dev  --pc positive_control/pc

# the one-line relationship between old and new control
diff positive_control/pc/solution.py positive_control/variants/pc_exchange_k10/solution.py
python3 positive_control/make_variants.py --check

# the identity instruments (both CLEAN, 0 decision leaves)
python3 gates/refreeze_evidence.py
python3 gates/restamp_evidence.py
```

---

## 7. The `INTERFACE.md` change — reported, not applied

`../INTERFACE.md` is the contract's interface authority and is owned by the
coordinator. This workstream did not edit it. This section states the change it
needs, as an exact before/after.

### 7.1 The finding: the contract does not define `PC_i` today

Verified, not assumed:

```console
$ grep -n "PC_i\|one_exchange\|positive_control" a0/tasks/maxcut/INTERFACE.md
$ echo "rc=$?"
rc=1                                   # no match: none of the three appears
$ grep -c "PC" a0/tasks/maxcut/INTERFACE.md
2
$ grep -n "PC" a0/tasks/maxcut/INTERFACE.md
175:至少覆盖：`ok` 但低分；`ok` 且高分（用 PC 结果）；…
186:- 放宽任何预注册门（PC 按族 Δ、ρ、饱和 NO-GO）；不过就重造套件并记录。
```

§1's layout (§1, the fenced block at lines 17–31) lists `generators/`, `suite/`,
`e_star.py`, `e_star_child.py`, `candidates/`, `references/`, `a0/meter/` and
`a0/a1/` — and neither `positive_control/` nor `gates/`.

`INTERFACE.md` names `PC` exactly twice — §10 (`ok` 且高分（用 PC 结果）) and §12
(不许放宽 PC 门) — and neither says *what* `PC_i` is. `../README.md` already
records the same gap ("No definition of `PC` exists anywhere in this
repository"), and `gate_config.json` points its `authority` at this file. So the
change is an **addition** before it is a replacement: the adopted control has no
contract-visible definition to revise.

### 7.2 The sentence that must change, and its replacement

The only sentence in `INTERFACE.md` that binds the positive control is §12's
first bullet. **Before** (verbatim, line 186):

```
- 放宽任何预注册门（PC 按族 Δ、ρ、饱和 NO-GO）；不过就重造套件并记录。
```

**After** — the same prohibition, with the contract element it was silent about
now named, so that adopting a `k` cannot be mistaken for relaxing a gate:

```
- 放宽任何预注册门（PC 按族 Δ、ρ、饱和 NO-GO）；不过就重造套件并记录。**正控 `PC_i` 的身份不属于门限**：2026-09-23 起 `PC_i` = `one_exchange(G_i, initial_cut=b_i, seed=s_i)`（NetworkX `b69beb2c`）在 **10 次接受改进交换后截断**，冻结于 `positive_control/variants/pc_exchange_k10/`（`source_sha256 = ee49eba0798028532c2bcf084b56b137e19937a827105da97c75ed5a01e759da`）；该身份只能经契约修订更换（见 `positive_control/PC-REVISION.md`），门限、套件与 `E*` 不随之改变。
```

### 7.3 The two supporting edits the same change needs

1. **§1's directory layout omits the whole positive-control machinery.** Both
   directories that carry the contract's artifact identity are absent, so the
   gate has no layout entry to point at. Insert after the `references/` line:

   ```
     positive_control/        ★正控 PC_i + 冻结基线 b_i（+ 截断变体 + 身份报告）
     gates/                   ★预注册可接纳门：判定、值文件、身份再盖章证据
   ```

2. **§12's failing branch names only one lever.** "不过就重造套件并记录" describes
   re-drawing the suite. The adopted resolution used the *other* lever — the
   artifact's identity — and `gates/REVISION-PROPOSAL.md` §6 is where that lever
   was measured and decided. The replacement in §7.2 carries this; no further
   sentence change is needed.

### 7.4 Not this workstream's to change, and reported as such

* `../candidates/c01_ok_high_pc` is the `C*(T1)` row whose *reason to exist* was
  the positive control (§10's "`ok` and high (PC)"). Now that `PC_i` is defined,
  `../README.md`'s note says that candidate "is the thing to replace". It is
  outside this directory's ownership and was not touched.
* `a1`'s registered T1 tree, `redesign/`'s lever tables, and the `C*(T1)` tie
  rows `c04_tie_a_pc_optimum` / `c05_tie_b_pc_complement` carry `PC_∞` numbers.
  Per `../gates/REVISION-PROPOSAL.md` §7 they are now numbers about a *different*
  artifact: not wrong, but needing a re-run or an explicit `PC_∞` label by their
  owners.
