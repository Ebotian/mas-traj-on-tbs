# `a0/a1/kapso_t1/` — T1's KAPSO registered evaluation tree, and the arm that runs it

This directory closes the gap `a0/a1/WIRING-REPORT.md` §1 row 10 and
`a0/a1/DEVIATIONS.md` **D-A1-2** record: the KAPSO arm was wired end to end but on the
**plumbing** (circle-packing) task, so it could not be placed in the A1 skeleton's `CID`
whose `TaskID` is `T1-maxcut`. What was missing was exactly three things — a T1
registered evaluation tree, a max-cut `EidStar` binding, and a T1 problem/goal — and
that is what is here.

Nothing upstream was touched: `/home/ebt/kapso_ck/kapso` (KAPSO @ `7d99b152`) is
read-only, and so are the other workstreams' trees
(`a0/runtimes/kapso/a0_adapter/`, `a0/a1/T1-EID.json`, `a0/tasks/maxcut/`). Where the
adapter was the plumbing task's, this directory rebinds it from its own side, and every
such rebinding is in `DEVIATIONS.md`.

## The one command

```bash
python3 a0/a1/kapso_t1/verify.py          # rebuild, dry run, rehearse; exit 0 = pass
python3 a0/a1/kapso_t1/verify.py --list   # what it runs
```

The paid run is **not** re-run by that command (it spends money):

```bash
cd /home/ebt/rsi-dev
DEEPSEEK_API_KEY=$(python3 -c "
import re,pathlib
t=pathlib.Path.home().joinpath('gptapi.md').read_text(errors='replace')
print(re.search(r'deepseek:\s*([A-Za-z0-9_\-]+)',t).group(1))") \
python3 a0/a1/kapso_t1/probes/live_t1.py arm --out-dir /tmp/a1t1/live
```

The key is read into the environment in that one command and is never printed or
written to an artifact. `probes/live_t1.py rehearse` runs the same arm inside the same
closed topology with the model call skipped — free, and part of `verify.py`.

`verify.py` was green on five consecutive full runs from the committed state (and each
step alone more often), with **one** transient failure of the `rehearse` step observed
once and not reproduced; that run's reason was lost with the process, so `verify.py` now
prints a failing step's stdout and stderr instead of only the summary. The rehearsal
depends on `unshare -rn` and on a KAPSO workspace under `/tmp`, so a contended host is
the place to look first if it recurs.

## What is here

| path | what it is |
|---|---|
| `config/adapter.maxcut.json` | the KAPSO adapter's `AdapterConfig`, retargeted to T1: T1's `E*`, `T1-EID.json`, `C*(T1)`, this mode config, this tree |
| `config/mode.maxcut.yaml` | the T1 mode: `parent_policy: best`, `budget.fidelity.mode: off`, `max_change_requests: 0`, the front-door closure, T1's design axes, and `protected_data_paths: [kapso_datasets/maxcut/dev]` |
| `task.py` | T1 as KAPSO is shown it: `T1_PROBLEM` / `T1_GOAL`, the candidate ABI (`INTERFACE.md` §3-§4), the objective's semantics, and the **dev-only visibility rule** as executable code |
| `t1_binding.py` | the max-cut `EidStar` binding: config + EID* + C*(T1), and the contract owner's `evalcontract.py verify|recompute` |
| `tree.py` / `build_tree.py` | T1's registered evaluation tree (`EID_r`): build, check, and the `EID_r -> EID*` mapping |
| `tree_src/kapso_eval.py` | the registered command's implementation — the **declared stub**: E*'s identity and the granted class triple, and no measurement |
| `tree/` | the built tree, committed: `kapso_eval.py` + `a0_locator.json`, whose bytes `EID_r` names |
| `tree_record.json` / `binding.json` | `EID_r`, the file digests, the `EID_r -> EID*` recipe, and the `AID_r` factors the retarget adds |
| `runtime_t1.py` | the retarget: rebind the adapter's task text and tree builder, T1's runtime subclass, the workspace data materialization, the harness-client helpers |
| `probes/dryrun_t1.py` | model-free: the tree loads, the class triple is derived from the runtime, the harness's line is the score of record, selection follows it |
| `probes/live_t1.py` | the live session through the meter in the closed topology (`arm`), and its free counterpart (`rehearse`) |
| `evidence/` | the verbatim output of the two probes, as committed |
| `tests/` | the unit invariants (`python3 -m pytest a0/a1/kapso_t1/tests -q`) |
| `verify.py` | the re-runnable entry point: tree check, binding check, dry run, rehearsal, tests |
| `DEVIATIONS.md` | every departure, with its justification and its consequence |

## The chain this directory establishes

```
        a0/a1/T1-EID.json            EID* = cddfa64e…  (frozen evaluator identity)
                 │
                 │ a0/a1/kapso_t1/tree.py builds two files and fingerprints them with
                 │ KAPSO's own manifest_fingerprint (evaluation_integrity.py:112-119)
                 ▼
        tree/{kapso_eval.py, a0_locator.json}      EID_r = manifest:6b1d6fcc…
                 │
                 │ KapsoRuntime.prepare → EvaluationMaintainer.setup (KAPSO's own code:
                 │ copy, calibration, fingerprint, registry, commit)
                 ▼
        <run>/workspace/kapso_evaluation/          registration.evaluator_id == EID_r
                 │                                  (checked by the dry run, from KAPSO's
                 │                                   own recorded state)
                 │ the session runs the registered command = the stub: identity + class
                 │ triple, no score, so `manifest_of_record` returns None rather than a
                 │ fabricated number
                 ▼
        after the session: harness_manifest.PostSessionManifest appends the harness's
        KAPSO_EVAL_MANIFEST line with the score `E*` produced outside the session
                 │
                 ▼
        node.score = the harness's number; KAPSO's own _select_parent /
        get_best_experiment / get_deliverable_score follow it
```

## Verdicts, with the evidence each rests on

| # | claim | verdict | evidence |
|---|---|---|---|
| 1 | the T1 tree loads and `EID_r` is T1's tree, computed by KAPSO | **CONFIRMED** | `evidence/dryrun_t1.json` (26/26 checks): `tree_check.pass`, and `registration.evaluator_id == tree_record.manifest_fingerprint` = `6b1d6fcc…` |
| 2 | the class triple is derived from the runtime, not hardcoded | **CONFIRMED** | same file: under a `fast/0.15` grant the derived line is adopted and a hardcoded `full/1.0/1337` line returns `None`; the stub echoes whatever triple it is invoked with |
| 3 | the harness manifest line is the score of record and the selection follows it | **CONFIRMED** | same file: node scores `3 / 9999 / 3` are the harness's `handed_value`s (`E*` measured `207 / 132 / 207`), node 1 parents on node 0 and node 2 parents on node 1, `get_best_experiment()` and `get_deliverable_score()` return the 9999 node — i.e. the *inverse* of the true ranking |
| 4 | the session's own manifest line cannot override it | **CONFIRMED** | same file (session claims `777777`, not recorded; three manifest lines on the node, the harness's last), and `evidence/live_t1.json` in a real session |
| 5 | a live session on T1, metered, in the closed topology | **CONFIRMED** | `evidence/live_t1.json` (15/15): one DeepSeek call, `rows: 1`, `ceq: 1116`, `unmetered: 0`, one repair record, direct egress `BLOCKED` from inside `unshare -rn` |
| 6 | the tree is T1's, not a generic stub: dev visible, hold-out absent, dev instances protected | **CONFIRMED** | `evidence/dryrun_t1.json`: 24 dev instances sha256-checked into the workspace, 0 hold-out bytes anywhere, 25 entries in KAPSO's registered data manifest, and a candidate that rewrites one dev graph gets `score=None` with `Protected evaluation data changed…` |
| 7 | the tree cannot be produced from a different `E*` | **CONFIRMED** | same file, `controls.e_star_drift`: a locator that still records EID*'s digests pointed at one changed byte of `e_star.py` → exit 3, no manifest line |
| 8 | the T1 tree is ready to run an A1 **campaign** | **NOT YET** | D-KT1-6 (the frame-run path) and D-KT1-7 (the `AID_r` factor is proposed, not adopted); no campaign has been started, and the calibration pilot / frozen `B_hard` come later |

## Spend

Model `deepseek-flash`, temperature 0, reported from the **meter ledger** (the runtime's
self-report is diagnostic only).

| run | rows | unmetered | tokens (hit / miss / completion) | `CEq` |
|---|---|---|---|---|
| `live_t1` (committed evidence) | 1 | 0 | 0 / 92 / 256 | 1116 |
| the same probe before a code change (not committed) | 1 | 0 | 0 / 92 / 256 | 1116 |
| `rehearse` (in `verify.py`; run several times) | 0 | 0 | 0 / 0 / 0 | 0 |
| **session total for this workstream** | | | 0 / 184 / 512 | **2232** |

`CEq = miss + floor(hit·2/100) + 4·completion = 92 + 0 + 1024 = 1116`, per
`INTERFACE.md` §8. Two paid runs were made because the probe's own code changed between
them and the committed evidence has to be the current code's output; the difference in
spend is cents, and both numbers are given rather than only the smaller one.

## What this does **not** cover

1. **No campaign has run on this tree.** What is verified is that the tree loads, that
   KAPSO's own registration produces the identity this workstream records, and that the
   harness's post-session number lands in the selection. A campaign also needs the
   calibration pilot and the frozen `B_hard` (`INTERFACE.md` §9), which are later steps
   and belong to the A1 orchestration, not to this directory.
2. **The frame-run path is not supported** (D-KT1-6): KAPSO's `execute_registered_evaluation`
   does `float(manifest["score"])`, and the stub deliberately prints no `score`. The path
   is unreachable in this configuration (measured: `controls.frame_run.raised = "KeyError: 'score'"`,
   and the two ways in — a VALIDATE grant and an evaluator bridge — cannot occur with
   `fidelity.mode=off` and `max_change_requests=0`). A campaign that enables fidelity
   profiles or accepts a change request would hit it.
3. **The registered tree is not yet an `AID_r` factor.** `binding.json` proposes two
   factors (`runtime.registered_evaluation_tree` and `..._files`); adopting them is
   `a0/a1/declaration.py`'s owner's call. Until then two different trees could sit under
   the same `AID_r`.
4. **The per-node graph is the probe's choice, not a campaign policy.** T1's aggregate
   is over a graph set (`INTERFACE.md` §5); the dry run and the live probe bind the
   harness's `graph_path` to one dev instance, `G_dev_0001`, and the A1 campaign's
   harness must decide the per-node instance set. Nothing here claims that choice.
5. **The model's contribution is not measured.** One metered model call proves the
   metering chain inside the closed topology; it does not make the arm's search a model's
   search. The seams inject frozen `C*(T1)` candidates, exactly as in the plumbing probe.
