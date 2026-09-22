# Adversarial verification of the A1 testbed — where a claim's evidence does not reach

Owner of this directory: the independent-verification workstream (`a0/verify/a1-testbed/**`).
Scope: items 1–5 of the assignment plus the gate machinery (item 6). **Nothing was fixed.**
Every finding is reported with a minimal reproduction; the probes are read-only except where
noted.

Zero model spend. No campaign was run. Every number below comes from a command in this
directory; the raw output of each is committed beside it (`out_*.txt`).

## How to re-run everything

```console
$ sh a0/verify/a1-testbed/run_all.sh          # v1, v1b, v2, v3, v4, v5, v6  (a few minutes)
```

Two of those commands are **not read-only** on the tree that contains them, which is itself a
finding:

* `a0/tasks/maxcut/conformance.py --check` rewrites `conformance.report.json` (v2 runs it);
* `a0/a1/verify.py` runs `a0/a1/declaration.py build`, which rewrites
  `a0/a1/declarations/CID.json` (v5 runs it; measured `96bad458… → 299d2e0f…`).

I restored both with `git checkout -- <path>` after each run, so the working tree holds only
this directory plus another workstream's `a0/a1/calibration/` edits (untouched).

---

## 1. Verdict table

| # | claim | verdict | evidence |
|---|---|---|---|
| 1 | suite is canonical, disjoint, independently sampled | **ACCEPTED** | `out_v1_suite.txt`: 60/60 canonical re-parse and manifest sha match, 60 distinct edge sets, 60/60 seeds re-derived from a role-keyed sha256 stream, 0 shared dev/eval seeds, worst same-slot Jaccard 0.089 |
| 1 | no solution leaks into a candidate-readable file | **REJECTED** | three independent failures in §2: the planted labels are *recoverable* from `graph.json`; the suite's own label store is stale; the eval set's reference partitions are readable and score exactly `R` |
| 2 | `E*`: cwd/PATH independence, determinism, failure semantics, child env, exact aggregation | **ACCEPTED** | `out_v2_estar.txt`: byte-identical Outcomes from 3 cwds and 4 PATHs, 2 processes equal `canonical_digest`, 12 non-ok C\*(T1) rows all `cut_edges: null`, child env exactly the 4 §4 keys, `Σcut/Σ|E|` reproduced with `Fraction` |
| 2 | network independence | **PARTIALLY ACCEPTED** | an honest candidate's number does not move with `--net-isolate`, but the child *can* reach `api.deepseek.com:443` when the flag is absent, and the frozen `c15` row is only an `error` *because* the table runs it with the flag |
| 2 | the interpreter-prefix launch makes the mode bit irrelevant | **ACCEPTED** | 0755/0644/0600/0400 of identical bytes give one `candidate_source_sha256` and one canonical Outcome; `#!/bin/false` does not matter; `exec: []` is honoured and a non-executable declared entry errors precisely |
| 2 | the staging regression fails against the pre-fix `E*` | **ACCEPTED** | `git show 11f55bf0:…` → `test_candidate_staging.py --e-star` rc=1 (`candidate_entry_failed`), working tree rc=0; `conformance.py --check` PASS with 21 rows + 14 top-level checks (7 probes + 7 invariants) and `p7`'s 5 named staging cases; `conformance.expected.json` byte-identical across the fix (`b3895951…`) |
| 2 | 2–3 `conformance.expected.json` rows reproduce by hand | **ACCEPTED** | `c01_ok_high_pc` (207/ok), `c13_error_non_deterministic` (null/error), `c19_timeout_process_group` (null/timeout, rc 4) all match, including `candidate_source_sha256` |
| 3 | `references/targets.json`: `R`, `U`, `OPT`, certification | **ACCEPTED** | `out_v3_references.txt`: 1908 stored partitions recomputed, `R` = max over them for all 60, `U ≥ R` for all 60, 42 certified ⇔ `OPT` non-null ⇔ `U = R`, one certified case checked against the SCIP log on disk |
| 4 | meter ledger arithmetic | **ACCEPTED** | `out_v4_meter.txt`: 27 rows / `ceq_total 187090` and 3 rows / 106 re-derived from each row's own `usage`; `verify_ledger.py` agrees |
| 4 | the framing fix, on the wire | **ACCEPTED** | my own tap: after → `Content-Length` / `chunked`, body byte-identical, 2 metered rows (`ceq 4128`); before (proxy at `86987235^`) → **no framing header**, upstream answers 400, every row unmetered |
| 4 | fail-closed | **ACCEPTED** | unframed body → 400 + `unmetered/request_body_unframed`, never forwarded; ledger file made unwritable → 500 "call refused rather than unmetered" and the log shows the refusal precedes the upstream leg; uncreatable ledger → the proxy does not start; CONNECT → 405 booked; non-allowlisted host → 403 booked |
| 5 | the score of record is the harness's, and no session line overrides it | **ACCEPTED** | `out_v5_wiring.txt`: SimpleLoop 132 = `E*`'s own value; KAPSO 2.4519… = `harness_score`, 3 manifest lines with the harness's last, the session's 9.75 recorded and not used; live `CEq` 8380 / 1104 re-derived |
| 5 | no unmetered model call is possible | **PARTIALLY ACCEPTED** | true for the arm (inside `unshare -rn`, 6/6 controls, 3 destinations BLOCKED); **not** true for the candidate lane — see finding F2 |
| 5 | hand the harness a value `E*` could not produce | **ACCEPTED (as designed), with a gap** | the service publishes `9999` with `true_value 132` beside it, and the frozen trace contract accepts a score of 9999; nothing in the chain bounds a score by `|E|` (finding F3) |
| 5 | "`verify.py` 6/6" | **REJECTED** | today `python3 a0/a1/verify.py` → rc=5, `t1-eid`, `wiring-simpleloop`, `skeleton-dryrun` fail (finding F1) |
| 6 | gate: thresholds not softened, ρ/Δ recomputed, `NOT_ADMISSIBLE`, proposal numbers | **ACCEPTED** | `out_v6_gate.txt`: 48 checks, 0 problems — thresholds identical to `A1-INTERIM.md`/`A1-CONTRACT-AUDIT.md`, all 24 dev rows recomputed, both medians and all family counts match, verdict `NOT_ADMISSIBLE`, dev **and** eval k-variant tables match the stored variants |

---

## 2. Item 1 — the leakage probe (the important one)

I wrote my own probe (`v1_suite.py`, §C1.5) rather than trust the suite's. Needles: the exact
label vector, both spellings, every relabeling of the same set partition (`k!  ≤ 24`), the class
membership lists, the 0/1 string, its reversal, and the decimal/hex bitmask — against the narrow
surface (`suite/**`, 62 files) and a scoped broad surface (`a0/tasks/maxcut`, `a0/a1`, `a0/meter`;
24 115 files). **Narrow-surface text hits: 0.** On the narrow reading the suite is clean, and I
reproduced its own claim rather than trusting it.

Three things the narrow reading does not cover, all measured:

**(a) The planted labels are recoverable from the file the candidate is handed.** `graph.json`
carries `generator.{name,params,seed}`, and the generator that consumes them is in the repository.
Replaying it reproduces all 15 Planted instances' **edge lists exactly** and produces labels whose
intra/inter densities match each graph's declared `p_in`/`p_out`:

```
G_dev_0019: declared p_in=0.100 p_out=0.020 | replayed intra=0.103 inter=0.022 | provenance intra=0.062 inter=0.062
```

Live: a candidate that only reads its `--graph` argument recovers the planted partition and E*
books it (`cand_replay`: `cut_edges 89/505`). For **max-cut** that partition is a trap
(cut fraction 0.139–0.321, below a random 0.50), so this is a *label* leak, not a score leak —
which is exactly what the assignment asked me to check, and the answer is not the one the suite's
README asserts.

**(b) The suite's own label store is stale, so its 30 leakage needles are inert.** I verified
`provenance.json`'s `planted_labels` are *not* the labels of the shipped graphs: the label vector
differs for **15/15**, the recorded seed differs from the graph's, and the density test above
shows provenance's vector carries no community structure at all. The README's §5(b) check passes
while searching for vectors no shipped graph encodes — and the numbers it quotes elsewhere
("the planted partition cuts 0.14–0.32") are the *true* ones, so two artifacts disagree about the
same object.

**(c) The eval set's near-optimal partitions are readable and score exactly `R`.** 720 files at a
predictable path (`references/logs/partitions/G_eval_*__*.partition.json`), one full assignment
each, filename keyed by `graph_id`. A candidate that copies the best one scores:

```
G_eval_0001: E* cut_edges=217 | harness handed_value=217 | targets.json R=217 OPT=217
G_eval_0019: E* cut_edges=377 | harness handed_value=377 | targets.json R=377
```

`G_eval_0001` is certified optimal, so that candidate attains the optimum on the hold-out by
reading a file. This holds through `a0/a1/eval_service.py`, not just through E*, and nothing in
E* or the service restricts a candidate's filesystem access (`INTERFACE.md` §12 requires eval not
to be visible in "any path a candidate can read").

---

## 3. The four findings

**F1 — the A1 tree is not self-consistent after the T1 fix; `verify.py` is not 6/6.**
```console
$ python3 a0/a1/verify.py ; echo rc=$?
{"verdict": "fail", "steps": {"t1-eid": false, "declarations": true, "wiring-simpleloop": false,
 "wiring-kapso": true, "skeleton-dryrun": false, "tests": true}, ...}
rc=5
$ python3 a0/a1/t1_eid.py check
{"on_disk": "cddfa64ead571bbb…", "pass": false, "reason": "eid_star drifted",
 "recomputed": "6682ff6a85088cbb…"}
```
The SimpleLoop adapter says it in one line (`adapter: contract mismatch: evalcontract.py verify
reported drift against T1.contract.json: DRIFT EID* changed cddfa64e… -> 6682ff6a…`). Cause: the
T1 fix `6dd717c2` changed `e_star.py` and `e_star_child.py`; the gate was re-frozen after it, the
A1 side was not. The recorded A1 evidence carries `evaluator_source_sha256 08281d21…` (pre-fix)
while E* now reports `4afff01f…`, so "verify.py 6/6" describes the tree *before* that commit.
Re-freezing `T1-EID.json` / `T1.contract.json` is a change outside my directory, so I report it.
Independently reproduced by the calibration workstream in `6602d943` (it blocked its own pilot on
the same two digests: `cddfa64e -> 6682ff6a`, `fa0932b4 -> 670f02ee`); neither of us fixed it.

**F2 — the closed topology does not cover the candidate lane.**
`eval_service.py`'s frozen `maxcut` argv never passes `--net-isolate`, so the child E* spawns runs
in the host network namespace. Measured from inside such a child:
`{'1.1.1.1': 'TimeoutError', 'api.deepseek.com': 'open'}` — arbitrary literals are blocked, the
provider is not; `/home/ebt/gptapi.md` exists as a readable file for that same uid (I did **not**
read it). A runtime could therefore put model spend inside a candidate the harness evaluates
outside the campaign budget. Claim 8 holds for the arm, not for the candidates.

**F3 — nothing bounds a score by the task.** The `--override` hook is deliberate (it is how the
"runtime consumes, it does not measure" property is shown), and the harness records
`true_value`/`handed_value` honestly. What is missing is any *guard*: the service happily
publishes `9999 > |E| = 265`, and the frozen trace contract validates a real fixture with every
score set to 9999 (`a0/contract/trace_validate.py validate --trace …` → `valid: 11 event(s)`).
Applied to `gate_config.json`'s own definitions that value yields `Δ = 37.23` and `ρ = −106.25`;
no threshold check rejects either.

**F4 — the suite's label audit is inert (details in §2b).** The check that proves "no labels leak"
searches 30 vectors that are not the labels of any shipped graph.

---

## 4. What I could not verify

* **The MQLib ensemble.** By instruction I verified only what is stored: 1908 partitions, their
  digests, the recomputed cuts, and one SCIP log/partition pair. I did not rebuild or re-run
  MQLib, and I cannot confirm the ensemble behind `R` independently of its artifacts.
* **The two paid live runs** (`live_simpleloop.json`, `live_kapso.json`). Re-running them spends
  money, so I verified their recorded artifacts and the ledger arithmetic, not the runs.
* **KAPSO's internals** (an upstream runtime, read-only by rule). I reproduced the recorded
  attribution caveat and its consequence, not the code path that causes it.
* **Interpreter-version independence of `E*`.** Only `python3.14` is installed here, so I could
  not test a second interpreter. Note the launch prefix is `sys.executable`: the launch is a
  function of the candidate's bytes *and* of the interpreter that invokes `E*`. The Outcome
  records that interpreter, so the dependence is visible, but "a function of the bytes alone" is
  true only modulo it.
* **A campaign end-to-end.** The task is `NOT_ADMISSIBLE`, so there is no campaign to run.
* **Wiring evidence produced against the pre-fix E\*** is internally consistent, and every number
  I could re-derive matches the current E* (`c02 → 132`), but the recorded `Outcome` digests
  belong to a superseded evaluator (F1).

## 5. Places a report claims more than its evidence supports

1. `a0/tasks/maxcut/suite/README.md` §5 "no solution leaks": true of label *text*; false as a
   statement about what a candidate can recover, and its needles search stale vectors (§2a, §2b).
2. The commit message of `bfbe74c2` ("built and verified") and the A1 wiring report's
   `verify.py`-based re-runnability: not reproducible on the committed tree (F1).
3. `INTERFACE.md` §12's "eval must not enter … any path a candidate can read": not enforced
   anywhere in the A1 chain (§2c).
4. The A1 report's "no unmetered model call is possible": true for the arm, not for the candidate
   lane (F2).
5. `a0/meter/evidence/selftest_on_prefix_proxy.txt` records **36/65**; my reproduction of the same
   claim is **37/65**. The difference is exactly `FAIL S16 the refusal names the offending host`,
   whose committed failure is `ModuleNotFoundError: No module named 'meter_core'` — an artifact of
   copying only `meter_proxy.py` without `meter_core.py`. The "the new checks are not vacuous"
   claim survives (28 framing/upstream failures in my run), but that one row measures the staging
   mistake, not the defect.
6. `E*`'s `score_exact` uses `Σcut / Σ|E|` (dev `2381/3218 = 0.7399`), while `INTERFACE.md` §5's
   text reads as the accumulation of per-graph rates (dev `360273725615380207845617419 /
   19833043538429067855216000 = 18.1653`). With `|E|` ranging 192–713 the two differ materially.
   `DEVIATIONS.md` D-T1-6 does not record the reading (the function docstring does), and no
   consumer of `score_exact` exists in `a0/a1` or `gates/`, so the divergence is inert today.
7. Minor: `targets.json` is tri-state in one field and boolean in another — `opt_certified: false`
   but `R_is_optimal: null` on the 18 uncertified graphs. Harmless, but a consumer that tests
   `is False` will see `None`.

## 6. Two observations that are not findings

* `c15_error_network_attempt` is **`ok`** (exit 0, `cut_edges 136`) when E* is invoked without
  `--net-isolate`; the frozen table's `error/candidate_refused` row exists only because
  `conformance.py` passes the flag for that candidate. The default invocation enforces nothing.
* `a0/a1/verify.py` is not read-only, and neither is `conformance.py --check` (see the note at the
  top). A "verify" that mutates the tree it verifies is worth fixing at the source, and it is why
  I restored both files after running them.

## 7. Deviations from the brief

* I did **not** re-run MQLib or the paid live probes (both explicitly out of scope; the brief says
  recorded state settles them).
* I ran `a0/a1/verify.py`, `conformance.py --check`, `a0/meter/selftest.py` and
  `a0/meter/raw_tap.py --proof` — all read-only in intent, but the first two write the two files
  named above; both restored with `git checkout`, and the behaviour is reported rather than hidden.
* The broad leakage surface in `v1_suite.py` is scoped to `a0/tasks/maxcut`, `a0/a1` and
  `a0/meter` (24 115 files) rather than all 144 574 files of the repository; the scoping is stated
  in the output. A hit does not depend on the scope, only a miss does.
* `/tmp/prefix-meter/` holds the pre-fix meter tree (`git archive 86987235^ a0/meter`), which the
  pre-fix framing and selftest rows need. `run_all.sh` recreates it if missing, so the "before"
  halves are reproducible from the committed repository alone.
