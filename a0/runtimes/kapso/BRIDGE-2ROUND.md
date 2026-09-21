# KAPSO two-round E2E bridge — `E*_t → parent_{t+1}` in a real campaign

Owner: this workstream. Everything under `runs/bridge-2round/**` and this file.
Written 2026-09-21. Every verdict below is **verified by running it** unless it says otherwise.

Artifacts:

| path | what it is |
|---|---|
| `runs/bridge-2round/bridge.py` | the runner: `round1` prepares a campaign and runs one iteration; `round2` resumes the same campaign **in a fresh process** and runs the second |
| `runs/bridge-2round/verify.py` | post-hoc verifier: re-derives every claim from KAPSO's own state, git and fresh `E*` runs (no model, no key) |
| `runs/bridge-2round/mode.bridge.yaml` | mode config: codex lane, DeepSeek `deepseek-flash`, `implementation_timeout: 1200` |
| `runs/bridge-2round/codex-home/config.toml` | isolated `CODEX_HOME` (DeepSeek provider, `env_key = "DS_KEY"`, `wire_api = "responses"`) |
| `runs/bridge-2round/real/` | **the run under test**: `round1.json`, `round2.json`, `campaign-state-{round1,final}.json`, `state-after-round*.json`, `verification.json`, `workspace/`, `independent/` |
| `runs/bridge-2round/logs/` | `round1.log`, `round2.log` (KAPSO stdout with the live codex transcript), `codex-smoke.log` |
| `runs/bridge-2round/dryrun/` | the same two rounds with the implementation phase seamed instead of a model session — the free self-test of the run/resume/report/verify code paths |
| `runs/bridge-2round/codex-smoke/` | cwd of the one-call lane check |

Files touched by this workstream: the eight paths above, plus this file. `git status --porcelain
a0/runtimes/kapso` lists only `?? a0/runtimes/kapso/runs/bridge-2round/`; no shared adapter file,
no other runtime's directory and not `a0/STATUS.md` was modified. No container was started.

## 1. Verdict

**Round 1 produced a decidable improvement (margin `2.201820520843313`), and round 2's real
parent, branch and deliverable all derive from round 1's winner — verified from KAPSO's own
recorded state, not from the model's claims.** `verify.py` returns `verdict: bridge_verified`,
12/12 checks true (`runs/bridge-2round/real/verification.json`).

| | round 1 | round 2 |
|---|---|---|
| lane | real `run_implementation` (`strategy.py:1036`) over a codex/**deepseek-flash** session; ideation + judge seamed | same, resumed in a fresh process |
| frozen candidate installed | `c04_near_tie` | `c01_good_hex` |
| node / branch / parent branch | node 0 / `generic_exp_0` / `main` | node 1 / `generic_exp_1` / **`generic_exp_0`** (node 0) |
| score of record | `2.451820520843313` | `2.4519205208433132` |
| fresh independent `E*` on the committed branch | `2.451820520843313` (same) | `2.4519205208433132` (same) |
| session time / round wall clock | 20.5 s / 23 s | 16.5 s / 19 s |
| model tokens (codex's own print) | 11,017 | 10,531 |

`E*` identity: `EID* = 664115e0…9328`. KAPSO's registered evaluator for this campaign,
`EID_r = manifest:1c6cdec3d71c01124249e00a8723c6b4ea7442ed479edcfc249b937d7125e962`, is **the
same fingerprint the audited A0.1 run recorded** (`runs/a0-01/a01/registered_tree.json`), so the
campaign measured under the ruler the audit signed off on. (Not an incidental match: the older
`runs/e2e-real/` used `5495c224…`, the pre-candidate-set-gate tree; see §6.)

## 2. What was actually run

Rounds are the runtime's own `GenericSearch.run` — one iteration per call — driven by
`runs/bridge-2round/bridge.py`. The ideation phase is seamed and hands the session a frozen `C*`
candidate id plus its bytes; **the implementation phase is not seamed**, so KAPSO's own
`run_implementation` created an `ExperimentSession` (git clone of the parent branch), ran a real
`codex exec` session inside it, had that session write `solution.py`, run
`python kapso_evaluation/kapso_eval.py --fidelity full --fraction 1.0 --seed 1337` in the
foreground, and commit/push to the workspace. The judge is seamed, but it only reads the score off
the session's manifest line; the score of record is set by KAPSO's own `manifest_of_record`
(`registered_evaluation.py:52-102`) in `generate_feedback` (`feedback_flow.py`).

Round 2 is *not* a continuation of round 1's process: it resumes the campaign the way the
orchestrator does on a restart — `GenericSearch(import_from_checkpoint=True)` +
`strategy.load_state(dump_state-round1)` + adopt the registry head without re-running
`EvaluationMaintainer.setup()`. So "round 2's parent" is selected by real KAPSO code from a
deserialized `node_history`, not from anything this workstream passed in.

### Wall-clock caps (what was chosen, and how it is enforced)

* **1500 s hard cap per round**, imposed by the launching shell: each round runs as its own
  background task under `timeout 1500 …`. A fresh process per round is what makes the cap hard —
  a killed round 2 cannot take round 1's artifacts with it.
* KAPSO's own `search_strategy.params.implementation_timeout` is set to **1200 s**
  (`mode.bridge.yaml`) so a stalled session is killed by the runtime's deadline ~300 s *before*
  the harness cap, leaving the round enough time to finalize a node (`score=None`) and record
  `not_verified` rather than being SIGTERM'd mid-write.
* Both rounds finished in ~20 s, i.e. the caps were never approached. Both are recorded in each
  round report (`wall_clock_cap_sec`, `cap_enforced_by`).

## 3. Round 1 — a decidable improvement

* baseline on `main` is the frozen `c02_baseline_upstream` (`solution.py` sha256 `18bacee4…`);
  a fresh independent `E*` run on `main`'s committed `solution.py` returns **`0.25`**.
* round 1's session installed `c04_near_tie` byte-for-byte (branch `generic_exp_0`'s `solution.py`
  sha256 `3bf7bf310c976e9a488fadad81e27ea4dfef47e5e218fc2bdbe861e72f1cf418` = the frozen
  `DataManifest` digest), and the session's manifest line names
  `candidate_identity.candidate_id = c04_near_tie, in_frozen_set: true`.
* node 0's score of record is `2.451820520843313`; KAPSO's own `manifest_of_record` accepted the
  session's manifest (`fidelity=full, fraction=1.0, seed=1337` = the granted class), and a fresh
  `E*` run on the committed artifact returns the same number to the last bit.

**Margin: `2.451820520843313 − 0.25 = 2.201820520843313`.** Decidable against `EID*`'s
conformance epsilon of `1e-9` by twelve orders of magnitude. `E*`'s bit-reproducibility (three
repeats, spread `0.0`, one canonical digest) is the A0.1 record's measurement, not this run's;
what this run adds is that the *fresh* `E*` run on the committed artifact reproduces the node's
score of record exactly, in both rounds. Round 1's winner is therefore unambiguous — that is what
makes "round 1's winner" a meaningful term for the next round.

## 4. Round 2 — the real `E*_t → parent_{t+1}` transition

Five independent lines of evidence, all from KAPSO's own state or from git — the model's
transcript is never the source of a claim.

1. **Parent selection, observed inside the iteration.** KAPSO's `_select_parent`
   (`strategy.py:1373-1406`, `parent_policy = best`) was tapped and returned
   `{branch_name: generic_exp_0, node_id: 0}` — the round-1 node. The runtime's own log line
   `Implementing on branch: generic_exp_1 (from generic_exp_0)` is in `logs/round2.log`.
2. **Node lineage, from the restored node history.** node 1 carries
   `parent_node_id = 0` and `parent_branch_name = generic_exp_0`; node 0 carries
   `parent_branch_name = main`. Both nodes survive in `campaign-state-final.json` with their
   `score` and their `evaluation_attempts` (evaluator id `1c6cdec3…`, fidelity `full`,
   fraction `1.0`, seed `1337`) — i.e. the attempt ledger KAPSO uses for tier/score decisions
   is complete across the process boundary.
3. **Git lineage of the branch the round-2 session pushed.**
   `git merge-base generic_exp_0 generic_exp_1` = `04970f4820333974a6c57032053e22f1d9ba2bf3`
   = `generic_exp_0`'s tip exactly, and round 2's HEAD commit `4cd292d4…` has
   `04970f48…` as its parent (`round2.json.git.commits`). The round-2 session did not merely
   branch off `main`; it was stacked on round 1's committed artifact.
4. **What the round-2 session itself saw first.** Its first shell call was
   `ls -la && cat solution.py | head -20`; the tool output in its own transcript
   (`workspace/.kapso/sessions/generic_exp_1/stream.jsonl`) shows `solution.py` at 2808 bytes
   starting `"""Near-tie variant of c01_good_hex: one radius shrunk by 1e-4.` — the docstring of
   round 1's `c04_near_tie`, not the 1441-byte baseline (which is what round 1's session saw).
   It also inherited round 1's `changes.log` (1506 bytes). The parent's tree is a property of the
   filesystem the session was handed, not of the model's story.
5. **The committed delta is exactly the intended step.** KAPSO recorded node 1's
   `code_diff` against its parent branch (`round2.json.node.code_diff`): one line of `solution.py`,
   the radius `0.0942046354170505 → 0.0943046354170505` — precisely `c04_near_tie → c01_good_hex`.
   `git diff --stat generic_exp_0 generic_exp_1` = `solution.py | 9 ++++----` plus `changes.log`.

**Deliverable.** On the restored final state, KAPSO's own selectors return node 1
(`generic_exp_1`, `2.4519205208433132`) as both `get_best_experiment` and
`get_deliverable_experiment` (`get_deliverable_score = 2.4519205208433132`), and the campaign's
own closing move `checkout_to_best_experiment_branch()` returned `generic_exp_1`, leaving the
workspace checked out there (`active_before: main` → `active_after: generic_exp_1`). The
deliverable is node 1, whose branch is a descendant of round 1's winner — the deliverable derives
from round 1's winner by lineage, and the round-2 step over round 1 is
`1.0000000000021e-4` — decidable against epsilon `1e-9` (it is C\*'s documented near-tied pair,
`c01` vs `c04`).

## 5. Cost

| call | tokens (as the tool printed) |
|---|---|
| codex→DeepSeek lane smoke test (`logs/codex-smoke.log`) | 899 |
| round 1 session | 11,017 |
| round 2 session | 10,531 |
| **total** | **22,447** |

Every `E*` invocation and the registered evaluations are local CPU (no spend). KAPSO's codex
adapter reports no billing telemetry, so `node.cost_usd` is `0.0` and the ledger undercounts —
the token counts above are the CLI's own. At `deepseek-flash` rates this is well under one US
cent. No container was started or left running by this workstream, and
`adapdc-catalog-postgres-1` was not touched. The DeepSeek key was read from `~/gptapi.md` into a
shell variable inside the same command that used it; a grep for the exact key over
`runs/bridge-2round/` returns **no file** (checked; `codex-home/config.toml` carries only the
variable *name* `DS_KEY`). `~/.codex/config.toml` was not modified (mtime unchanged); all codex
state went to the isolated `CODEX_HOME`.

## 6. Findings worth the coordinator's attention

* **`EID_r` of the audited tree is `1c6cdec3…`, not the `5495c224…` in `runs/e2e-real/`.**
  `runs/e2e-real/registered_evaluation_source/` is the *pre-fix* tree: its `a0_locator.json` has
  no `allow_unfrozen_candidate` key and its `kapso_eval.py` still reads
  `A0_KAPSO_ALLOW_UNFROZEN_CANDIDATE` from the environment — the shape ADAPTER.md later replaced
  with a tree property. The A0.1 run (`runs/a0-01/a01`) and this bridge run both carry the fixed
  tree, so nothing in the audited chain is affected; but a reader joining `runs/e2e-real` to
  `runs/a0-01` on `EID_r` will see them differ, and the reason is the fix, not drift.
* **codex prints `Model metadata for 'deepseek-flash' not found. Defaulting to fallback
  metadata; this can degrade performance and cause issues.`** on every call, as the exit-closed
  workstream already recorded. It did not affect these two mechanical sessions, but a long
  campaign should supply `model_catalog_json` first.
* **codex appends `[projects."…"] trust_level = "trusted"` entries to `CODEX_HOME/config.toml`**
  — observed, harmless (two entries, the two session folders), and left in place as evidence that
  codex really ran in them.

## 7. What is UNVERIFIED / what this does not settle

* **The parent *choice* was not a discriminating one.** Before round 2 the restored history held
  exactly one finished node, and `_select_parent` with `parent_policy = best` returns
  `get_best_experiment()` — which is that node for *any* score. So this run observes the
  transition `E*_1 → node.score → node_history → _select_parent → parent_branch` end to end, but
  it does **not** show that the score value, rather than mere existence/recency, drove the pick.
  Score-vs-recency discrimination in-campaign needs ≥2 nodes before the decisive round (a third
  round whose parent is chosen between two finished nodes, or `node_expansion_value: 2` in round
  1). The seam-driven A0.2 `ordered_pair` / `reversed_order` scenarios are still the evidence
  that selection follows the score; this bridge connects that kernel to a real campaign, it does
  not replace those scenarios.
* **Ideation is still seamed.** The improvement each round is a frozen `C*` candidate the
  harness told the session to install. What is real is the session → artifact → registered
  evaluation → score-of-record → selection chain; a model *inventing* the improvement is not
  claimed and was not tested.
* **Deliverable flip vs. recency.** The deliverable moved to node 1 (higher score) and node 1 is
  also the most recent node, so this run does not separate score from recency there either. The
  margin (`1.0000000000021e-4`) is small by design — it is C\*'s near-tied pair — so the
  deliverable-flip claim rests on `E*`'s bit-reproducibility, which the run confirms
  (fresh `E*` reproduces both node scores exactly).
* **Single campaign, single seed, single model.** One run of the two-round bridge with
  `deepseek-flash`, `seed=1337`, one baseline. No repetition, no variance/robustness claim, and
  no claim that the same holds for the claude lane or for a killed/restarted mid-round process.
* **No failure path was exercised.** If round 1's session had produced no score,
  `_select_parent` would fall back to `main` (`strategy.py:1373-1405`) and the bridge would be
  unproven; that branch of the code was not run here.
* The `dryrun/` artifacts come from the *seamed* implementation path and must not be read as
  model-lane evidence; they exist to show the same runner/resume/verifier code path passes.

## 8. Exact commands a third party re-runs

**Re-run the verification only** (no model, no key, no network; seconds). This re-loads KAPSO's
state, re-executes KAPSO's own selectors, re-reads git, and re-runs `E*` three times
(`main`, round 1's branch, round 2's branch):

```bash
cd /home/ebt/rsi-dev/a0/runtimes/kapso
.venv/bin/python runs/bridge-2round/verify.py --run-dir runs/bridge-2round/real
# → prints {"verdict": "bridge_verified", ...}, exit 0; writes runs/bridge-2round/real/verification.json
```

**Re-buy the whole thing** (needs the DeepSeek key; ≈22.4 k tokens, ≈25 s of session time):

```bash
cd /home/ebt/rsi-dev/a0/runtimes/kapso
export PATH="$PWD/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1
export CODEX_HOME="$PWD/runs/bridge-2round/codex-home"
export DS_KEY="$(grep '^deepseek:' ~/gptapi.md | head -1 | cut -d: -f2- | tr -d ' ')"
timeout 1500 .venv/bin/python runs/bridge-2round/bridge.py round1 --run-dir runs/bridge-2round/real --cap 1500
timeout 1500 .venv/bin/python runs/bridge-2round/bridge.py round2 --run-dir runs/bridge-2round/real --cap 1500
.venv/bin/python runs/bridge-2round/verify.py --run-dir runs/bridge-2round/real
```

`round1` rebuilds `runs/bridge-2round/real/workspace` from scratch, so this is a fresh campaign.
(`--cap` is bookkeeping only; the hard cap is the `timeout` in front of each round.)

**The free self-test of the same code paths** (implementation seamed, no model call):

```bash
cd /home/ebt/rsi-dev/a0/runtimes/kapso
export PATH="$PWD/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1
timeout 300 .venv/bin/python runs/bridge-2round/bridge.py round1 --run-dir runs/bridge-2round/dryrun --seam-implementation --cap 1500
timeout 300 .venv/bin/python runs/bridge-2round/bridge.py round2 --run-dir runs/bridge-2round/dryrun --seam-implementation --cap 1500
timeout 300 .venv/bin/python runs/bridge-2round/verify.py --run-dir runs/bridge-2round/dryrun --seam-implementation
```

**The lane check** (one codex call, the cheapest possible proof the DeepSeek provider config in
`codex-home/` is live):

```bash
cd /home/ebt/rsi-dev/a0/runtimes/kapso/runs/bridge-2round/codex-smoke
export CODEX_HOME=/home/ebt/rsi-dev/a0/runtimes/kapso/runs/bridge-2round/codex-home
export DS_KEY="$(grep '^deepseek:' ~/gptapi.md | head -1 | cut -d: -f2- | tr -d ' ')"
codex exec --skip-git-repo-check --sandbox read-only "Reply with exactly the two characters: OK"
```
