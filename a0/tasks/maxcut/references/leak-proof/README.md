# `references/leak-proof/` — the hostile candidate and what it can reach

Owner: this workstream. This directory is evidence, not part of any frozen
identity: nothing here is in C*(T1), no manifest hashes it, and it computes
nothing that a verdict reads.

## What is here

| path | what it is |
|---|---|
| `hostile_candidate.py` | a candidate that tries *every* route to a stored answer and writes down each outcome beside its artifact |
| `run_leak_probe.py` | runs that candidate in three environments and compares what the harness **books** (`cut_edges`), never what the candidate claims |
| `out_leak_probe.pre_seal.json` / `.txt` | the recorded three-mode run, made **before** the witness vectors were removed: it is what shows the defect and what the fix closes |
| `out_leak_probe.json` / `.txt` | the `fixed` mode re-run against the sealed tree |
| `out_verifications.txt` | the transcript of every check this workstream re-ran (`maxcut_suite.py verify`, `audit_labels.py verify`, `verify_targets.py` in both modes, `seal_witnesses.py verify --corpus`, `test_candidate_staging.py`, `conformance.py --check`, the leak probe) |

## The three environments

```bash
python3 leak-proof/run_leak_probe.py --modes prefix,open,fixed
```

* **`prefix`** — the pre-fix evaluator, materialised from
  `git show HEAD:a0/tasks/maxcut/{e_star.py,e_star_child.py}`. No isolation, and
  the candidate is handed the suite file's own path. This is the verifier's
  reproduction (`a0/verify/a1-testbed/REPORT.md` §2c).
* **`open`** — the fixed evaluator with `--no-fs-isolate`: the reduced view is
  handed, but the answer stores are readable.
* **`fixed`** — the fixed evaluator with its default isolation.

`G_eval_0001` is the target because the reference table certifies its optimum:
`R = OPT = 217` on `|E| = 254`. A booked 217 is a copied answer; ~127 is an
honest guess; the candidate writes `index % 2` when it recovers nothing.

## The attack list (each one is an attempt in the dump)

| attempt | what it does |
|---|---|
| `handed_graph` | reads the graph it was handed |
| `handed_graph_generator_block` | does the handed graph carry `generator`? |
| `suite_file` | reads `suite/eval/<graph_id>.json` directly |
| `suite_manifest` | reads `suite/manifest.json` |
| `targets_json` | reads the reference table |
| `witness_by_name`, `witness_all_names`, `witness_glob` | reads `references/logs/partitions/<graph_id>__*` |
| `scip_witness` | reads the SCIP primal solution |
| `raw_stdout_solution` | parses MQLib's `Solution:` line out of `references/logs/raw/` |
| `generators_provenance`, `generators_source` | reads the planted labels and the generator that replays them |
| `git_show_head_witness`, `git_log_all`, `git_cat_file_blob`, `git_rev_parse_cwd` | recovers the removed vectors out of git history |
| `state_root_siblings` | reads another candidate's partition for the same graph out of the shared default state root (a real witness is planted there by the driver first) |
| `task_tree_scan`, `filesystem_scan`, `filesystem_answer_sweep` | scans the task tree / the machine for any partition file |
| `mountinfo_tmpfs_masks` | lists the masks from `/proc/self/mountinfo` |
| `umount_first_mask_then_read` | tries to unmount every tmpfs mask, then read the witness |
| `proc_root_escape` | reads the witness through another process's `/proc/<pid>/root` |
| `nested_userns_then_read` | tries a second user namespace to escape the mount namespace |
| `credential_file` | reads `~/gptapi.md` (the model lane's credential, not an answer) |

## What the recorded run shows

`out_leak_probe.pre_seal.json` is the full table. In summary:

* `prefix`: the candidate copies a stored witness and the harness books **217 = R
  = OPT** — the defect, reproduced end to end.
* `open`: the same **217**, but recovered only by reading the witness file: the
  *handed* graph no longer carries `generator`, so the replayed-planted-partition
  route is gone. This is the row that shows the filesystem sandbox, not the
  redaction, is what stops the direct copy.
* `fixed`: every route fails and the booked score is the candidate's own honest
  guess (136). The mount masks are visible in `/proc/self/mountinfo` and cannot be
  unmounted ("must be superuser"), the process runs as uid 0 inside the namespace
  with an empty capability set, `/proc` shows one process, so the
  `/proc/<pid>/root` escape has nothing to point at, and `git` reports "not a git
  repository" because `.git` is masked with the rest.

The one residual the probe *measures* rather than argues: `credential_file` still
succeeds (`~/gptapi.md`, 591 chars). That is the model-budget lane's vector, not
an answer to any instance; the sandbox can hide it with one more mask
(`--fs-mask /home/ebt`), and the decision to hide a user's whole home directory is
left to the coordinator rather than taken here.

## Limits of this evidence

* The filesystem audit is a *text* scan: a compressed or encoded copy of a
  witness is not detected by it, and a copy on a filesystem outside the scanned
  roots is not either. The scan is exhaustive over `/home/ebt`, `/tmp`,
  `/var/tmp`, `/opt`, `/srv` and `/root` (dependency trees pruned).
* The candidate's own scans keep a 20 s budget, because tau is 10–30 s: an
  unbounded scan is not a plausible attack, so the probe does not pretend to have
  performed one.
* The mounts are per-invocation and private; `out_leak_probe.json` records the
  mask set each run used rather than asserting a global property.

## Composition with the lane sandbox

`a0/a1/candidate_sandbox.py` (the lane closure, landed in parallel) runs E* inside
`unshare -rmnpf --mount-proc` and hides `/home`, `/tmp`, `/var/tmp` and
`/run/user`; `e_star_child.py` then builds a namespace of its own inside that one
and masks the task directory, `.git`, the state roots and `/tmp`/`/var/tmp`
again.  The two are additive and were checked to compose: `out_lane_composition.txt`
runs frozen C*(T1) candidates through the lane and gets the frozen values
(`c01_ok_high_pc` → 207 on `G_dev_0001`, which is the conformance row; 205 on
`G_eval_0001`; `c12_error_exit30` → `error` with no number).

## The verifier's own probes, re-run

`out_verifier_probes.txt` re-runs `a0/verify/a1-testbed`'s three leak candidates
(`cand_replay`, `cand_provenance`, `cand_reference`) — the programs that produced
REPORT.md §2a and §2c — against the fixed tree, both through E* and through
`a0/a1/eval_service.py`. All four cases now book **no number at all** (`error`,
`handed_value: null`), where before the fix `cand_reference` booked
`217 = R = OPT` on `G_eval_0001` and `cand_replay` booked the replayed planted
partition on `G_dev_0019`. The verifier's driver itself (`v1b_leak_live.py`) now
stops at its first candidate, because that candidate raises where it used to
return a number; that is the intended change in behaviour, and it is why the
re-run is driven separately here.
