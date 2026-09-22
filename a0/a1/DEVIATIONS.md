# `a0/a1/DEVIATIONS.md` — every place this workstream interpreted or departed

Two of these are departures from another worker's component and one is a hole in
its own deliverable; all three are load-bearing for what the evidence above may be
used to claim. Nothing here is silent.

---

## D-A1-1 — T1's `EID*` document is authored **here**, not by the maxcut worker

**What.** `a0/tasks/maxcut/` ships a frozen evaluator (`e_star.py`,
`e_star_child.py`), a frozen suite with a manifest sha256 (`47324fcc…`) and a
frozen candidate set, but **no `EID*` document** (`ls` of that directory: no
`*.EID*.json`, no contract spec). `INTERFACE.md` §2/§5 make the evaluator's
identity a first-class object (`evaluator_source_sha256` on every Outcome; §11
says T1 "只需新增自己的 `EvaluatorSource` 记录"), and principle (i) requires it to
be frozen and recomputable — so *some* document has to exist.

**What was done.** `a0/a1/t1_eid.py` supplies a **spec**
(`a0/a1/T1.contract.json`) and has the contract owner's own
`a0/contract/evalcontract.py` build the five components and the combined
`EID*` (`a0/a1/T1-EID.json`). `EID*` = `cddfa64ead571bbb09daa458c6b514377fba32e62612f5c2e17a6b49b7a78ab1`.
`python3 a0/a1/t1_eid.py check` rebuilds everything from the repository and
cross-checks the `EvaluatorSource` records against what `E*` itself hashes
(`e_star.py digest`), so the two ways of naming the evaluator cannot drift.

**Why this is a deviation.** The document's *home* is arguably
`a0/tasks/maxcut/`; putting it there would write into another worker's directory.
The file declares `"produced_by": "a0/a1/t1_eid.py"` and this entry records the
choice. If the maxcut owner authors one, this should be replaced by theirs and the
`eid_star` value re-frozen — nothing else in `a0/a1/` needs to change, because the
path is a parameter (`--eid`, `A1Campaign.eid_path`).

**Not claimed:** that this is the *only* reasonable T1 identity. It is a
recomputable one, built from the frozen material, with the recipe published.

---

## D-A1-2 — the KAPSO arm's T1 retarget is another workstream's; this directory's live KAPSO evidence is a plumbing run

**What.** `INTERFACE.md`'s CID rule ("if an object can change `P(Y|r)` it must be
inside `CID` or `AID_r`") makes `TaskID` a `CID` component: two arms measured on
different tasks cannot contribute to the same `Δ`. KAPSO's adapter
(`a0/runtimes/kapso/a0_adapter/`) is wired end to end for
`a0/tasks/circle-packing`: its `EidStar`, its registered evaluation tree
(`registered/kapso_eval.py`), its problem handler and its goal all describe
circle-packing. Retargeting it to T1 means a new registered evaluator tree, a new
`EidStar` binding and a new problem/goal — a workstream of its own.

**Status of the gap: closed by another workstream, not by this directory.**
`a0/a1/kapso_t1/` delivers the three missing pieces (the T1 registered evaluation
tree with `EID_r = manifest:6b1d6fcc…`, the max-cut `EidStar` binding and the T1
problem/goal) plus its own free dry run (26/26) and its own live T1 arm (15/15), and
it drives *this* directory's `a0/runtimes/kapso/a0_adapter/harness_manifest.py`.
What this directory added in response is the declaration: the tree is now pinned in
`AID_r.A_kapso.json` (D-A1-6), so the arm named there and the tree it ran can no
longer drift apart.

**Which live evidence belongs to which configuration** — the two must not be
conflated:

| evidence | task | registered tree | `AID_r` |
|---|---|---|---|
| `a0/a1/evidence/live_kapso.json` (this directory's probe) | plumbing | the plumbing tree `8128cf91…` | **not** the file that describes it |
| `a0/a1/kapso_t1/evidence/live_t1.json` (that workstream's probe) | T1 | `manifest:6b1d6fcc…` | `declarations/AID_r.A_kapso.json` |

The plumbing run is kept because it is *this* probe's own record and is what a
re-run of the committed code reproduces; it is not offered as T1 evidence for that
arm. **Why this directory did not simply re-run its own probe on T1:** that would
mean building a second driver for the same arm, and two implementations of one arm
diverge — a worse outcome than citing the one that exists and is verified.

**What was done here.** The KAPSO wiring was implemented *task-agnostically*
and verified in two places:

* `probes/wiring_kapso.py` (model-free, 7/7): the injection, the class-triple
  derivation, the ordering rule and the attribution caveat;
* `probes/live_probe.py --arm kapso` (10/10): a real campaign with a real metered
  model turn, the same ordering test, and the meter evidence.

For the live arm the harness was pointed at the **plumbing** evaluator
(`--evaluator circle-packing`), which is the task KAPSO is actually wired to.

**Consequence, stated plainly.** The A1 skeleton's `CID` names `TaskID =
T1-maxcut`; the KAPSO arm cannot be placed in it until the retarget is done. So
the skeleton's dry-run is a proof of the *machinery*, not a licence to run the 8
campaigns with two arms. What the KAPSO work *does* establish is the thing that
was open: that an externally authored score can be landed after the session and
cannot be overridden by the session, with the class triple derived from the
runtime. All of that is task-independent.

**What is left.** The calibration pilot and the frozen `B_hard`
(`INTERFACE.md` §9) — machinery that belongs to the A1 orchestration and not to
either adapter. Once those exist, the two arms can be run in one `CID`.

---

## D-A1-3 — `a0/meter` dropped every request body; a repair hop compensated, then was **deleted**

**Status: RESOLVED and the workaround removed.** Historically: the hop existed in
commit `9e836f36`; `a0/meter` fixed the defect in `86987235`; this revision deletes
the hop, its flag and its `CID` factor. The audit trail is kept because a campaign
whose `CID` has one more factor than this file lists was run inside that window.

### The defect (reproduced, and it was not ours to fix)

`a0/meter/meter_proxy.py` built the upstream request with
`putrequest` / `putheader` / `endheaders(body)` (`:283-291`) after stripping
`Content-Length` as a hop-by-hop header (`HOP_BY_HOP`, `:103`). Python's
`http.client.endheaders(message_body)` does **not** re-add `Content-Length`, so the
upstream received the body bytes with **no framing header at all**. Captured
verbatim by a raw TCP tap behind the proxy during the probe:

```
POST /v1/chat/completions HTTP/1.1
User-Agent: curl/8.22.0
Authorization: Bearer …
Content-Type: application/json
Host: 127.0.0.1:8898
Accept-Encoding: identity
<blank line>
{"model":"m1","messages":[…],"max_tokens":8}      <- unframed
```

A conforming HTTP/1.1 server reads no body. Every real DeepSeek call answered
`400 Failed to parse the request body as JSON: EOF while parsing a value at line 1
column 0` and was booked `unmetered` with reason `unparseable_response_body` —
i.e. **no campaign could ever have a real `CEq`**, which is what §8's budget rests
on. The component's own selftest could not see it (`fake_upstream.py:239` read the
body from `content-length`, got 0 bytes, and the tests asserted on the *response*
usage): 55/55 passed with every request body silently discarded.

### What was done at the time

Because `a0/meter/` belongs to another worker and `INTERFACE.md` forbids silent
deviation, the fix was a **declared compensating hop** in this directory,
`a0/a1/meter_body_repair.py`, inserted *below* the meter:

```
runtime ─plaintext─▶ meter_proxy ─plaintext─▶ repair hop ─TLS─▶ api.deepseek.com
                      (books the row)          (restored framing)
```

It read the unframed body (a short idle window delimited it — the proxy sent head
and body in one `sendall`), added `Content-Length`, forwarded over
certificate-verified TLS to `api.deepseek.com` and nothing else, and logged every
repair. `CID` carried a `harness.meter_body_repair` factor with its sha256, and
`live_simpleloop.json` (recorded then) contains one such row:
`{client_framing: "unframed_repaired", request_body_bytes: 2697, status: 200}`
alongside a real `ceq = 3600`.

### The residual risk it carried, which deletion removes

The hop re-framed whatever it was handed with `Content-Length`. `a0/meter`'s fix
now **preserves the client's framing choice** — a chunked request stays chunked
(`encode_chunked=True`, `meter_proxy.py:369-373`). Had the hop still been in the
path, a chunked client's chunk-encoded bytes would have been re-labelled with a
`Content-Length` equal to the *encoded* length: the upstream would read a
truncated body (the first chunk's data, then framing bytes as data), silently.
That is a corruption mode the hop introduced and the fix exposes, and removing the
hop is what eliminates it. Nothing in `a0/a1/` depends on the hop now.

### What was removed, exactly

* `a0/a1/meter_body_repair.py` (deleted), `MeterBodyRepairHop`, `use_body_repair`,
  `repair_upstream`, and the `meter.aid.json: body_repair` fragment;
* the `harness.meter_body_repair` **`CID` factor** — so `CID` is re-frozen at 13
  factors. `declaration.py` carries a comment where it used to be;
* the probe's dependence on the hop's log for its "one row per upstream call"
  cross-check. It is replaced by two `a0/meter`-owned artifacts: the proxy's own
  per-call sidecar (`events.jsonl`, one `kind: "call"` record per upstream call)
  and `a0/meter/verify_ledger.py`, which re-derives every metered row's `ceq` from
  that row's usage. The new check is *stronger* than the old one — it no longer
  needs a second process in the path to be able to count calls.

### One consumer had to be updated, and it was not this directory's file

`a0/a1/kapso_t1/probes/live_t1.py` (another workstream's delivery inside this
tree) read `MeterProxy.hop` at line 230 and used `report["repair_records"]` in its
"one row per upstream call" check, so deleting the hop would have raised
`AttributeError: 'MeterProxy' object has no attribute 'hop'` in its `arm` *and*
`rehearse` paths — i.e. in that workstream's free `verify.py` too. Per the
instruction not to force a deletion over a live dependency, the minimal replacement
was applied in that file, and only those lines:

* the topology diagram and check (d) in its module docstring;
* `report["repair_records"] = self.meter.hop.records() …` →
  `report["meter_call_events"] = [event for event in self.meter.call_events() if event.get("kind") == "call"]`
  plus `report["meter_verify_ledger"] = self.meter.verify_ledger()`;
* the check → the row count against `meter_call_events`, plus a
  `the_meter_s_own_verifier_re_derives_every_row` check.

`MeterProxy.call_events()` and `MeterProxy.verify_ledger()` are provided here for
exactly that replacement. That workstream's `verify.py` passes 5/5 with the change
(tree, binding, dryrun, rehearse, tests), and its **committed paid evidence
`a0/a1/kapso_t1/evidence/live_t1.json` now predates the edit** — it still records
`repair_records` and the old check. Refreshing it is a one-command re-run for that
workstream (~1,100 `CEq`, cents); it was not done here because that evidence file
is theirs and the two edits this task specified did not include it.

**Not claimed:** that the fixed proxy is correct in general — only that the
defect this hop compensated for is fixed at `86987235`, that the hop is gone, and
that `python3 a0/a1/verify.py` passes without it.

---

## D-A1-4 — `a0/a1/` follows the SimpleLoop adapter's convention for `--evaluator`

`evidence/*.json` names the evaluator per arm (`maxcut` for SimpleLoop,
`circle-packing` for KAPSO, per D-A1-2). The ABI, the token, the ledger and the
fail-closed ordering are identical for both; only the argv and the score field
differ (`EVALUATORS` in `eval_service.py`). This is an extension of §5, which
defines the Outcome for T1 only, and it exists so the KAPSO ordering test could be
run against a real runtime rather than a mock (D-A1-2).

---

## D-A1-5 — two small extensions inside the SimpleLoop adapter

Both are inside the wire-up, both are visible in the traces, neither changes a
selection rule:

1. `traces.failure_stage_for` maps **exit code 4 to `timeout`**. T1's `E*` gives a
   timeout its own exit code (`e_star.py:99`); the plumbing evaluator reports it as
   exit 3 with `failure.kind = runtime_budget_exceeded`. Same trace stage, one more
   reachable code. The frozen plumbing table is untouched.
2. `policy.scalar_of` reads a field from `outcome.fields` when the Outcome has
   one and from the Outcome's top level otherwise, and preserves the integer type
   of T1's `cut_edges` so the argmax is exact integer comparison rather than an
   IEEE-754 equality that merely happens to be exact. `load_policy` accepts
   `outcome.<name>` as well as `outcome.fields.<name>` for the same reason.

---

## D-A1-6 — the KAPSO T1 registered evaluation tree is adopted into `AID_r`

**What.** `a0/a1/kapso_t1/` (another workstream) delivered KAPSO's T1 registered
evaluation tree (`EID_r = manifest:6b1d6fcc…`) and its D-KT1-7 observed that the
tree was **not** a factor of any `AID_r`, with `binding.json` proposing the names
`runtime.registered_evaluation_tree(_files)`.

**Decision: adopted, at full resolution rather than as a coarse `EID_r` label.**
The causal-role rule settles it: the registered tree *is* KAPSO's registered
evaluator, it is what the session's `KAPSO_EVAL_MANIFEST` line comes from, and a
campaign that ran a different tree ran a different measurement. It can change
`P(Y|r)`, so it must be inside `CID` or `AID_r` — and it is arm-varying (only
KAPSO registers an evaluation tree), so it is `AID_r`.

Why not a coarser factor carrying only the `EID_r` string: because `EID_r` is a
*hash of a manifest*, so recording only it would make the factor un-recomputable
without the tree, and would hide the failure the rule exists to catch — a tree
that was *rebuilt* with the same claimed `EID_r` label but different bytes. Two
factors are recorded:

| factor | identity |
|---|---|
| `runtime.registered_evaluation_tree` | `value:{eid_r: manifest:6b1d6fcc…, native_scheme: manifest_fingerprint, fingerprint_rule, tree, binding}` |
| `runtime.registered_evaluation_tree_files` | `value:{"a0_locator.json": "5a0c99ff…", "kapso_eval.py": "6759ef05…"}` — the fingerprint's exact inputs |

Both are **recomputed from the tree's bytes by `declaration.py`**
(`registered_tree()`), not copied from `binding.json`, and the result is
cross-checked against that binding's `registered_tree.files`, `eid_r_value` and
`eid_r`; a disagreement is recorded as an audit problem of kind
`registered_tree_disagreement` and **fails the verdict**. A declaration that
merely quoted another file's claim could not notice that file going stale.

The `SimpleLoop` arm declares the *same factor name* with the value `{mechanism:
"none", …}`: it has no registration surface at all (`native_scheme = none`,
`mapping_mode = adapter_declared_injection`), so the factor is arm-varying by
value, and a reader comparing the two arms sees the mechanism difference instead
of an asymmetry in the paperwork.

**Not adopted:** factors for the tree's *generator* (`build_tree.py`, `tree.py`,
`tree_src/`). The campaign runs the *frozen tree*, and the per-file map pins
exactly the bytes it runs, so a generator change that alters the tree already
changes `AID_r`; one that does not alter the tree cannot change `P(Y|r)`.
Adding generator hashes would pin machinery that has no causal path of its own to
the score.

---

## Not a deviation, but worth recording

* **`deepseek-flash` answers inside `reasoning_content`** on the DeepSeek chat
  face, leaving `content` empty (measured: `content: ""`, `finish_reason: length`,
  the text in `reasoning_content`). The model lane reads both and records which one
  carried the answer (`solvers.py`, `ModelSolver._chat`). A lane that read only
  `content` would look like a model that never answers.
* **`--meter-token=<value>` is passed with `=`** in the probes: a
  `secrets.token_urlsafe` token may begin with `-`, which argparse would then read
  as another option (measured: `error: argument --meter-token: expected one
  argument`).
* **The live SimpleLoop arm's model proposal is degenerate** (`ds_i001` scores
  `cut_edges = 0`, i.e. a trivial assignment). The probe measures the wiring, not
  the model's search skill; the harness's number for that candidate still enters
  the selection (`132 > 0`, the baseline stays champion).

---

# This revision — the re-freeze, the candidate lane, and the bound on a score

Four defects were reported by the independent verifier
(`a0/verify/a1-testbed/REPORT.md`, findings F1–F4). Three of them are closed here;
each closure names the probe that measures it and the hostile attempt behind it.
Two of them touch an interface, and those two are marked **INTERFACE** so the
coordinator can decide whether to amend `a0/tasks/maxcut/INTERFACE.md` (this file
is the workstream's own record; `INTERFACE.md` is the authority).

## D-A1-7 — `EID*` was re-frozen: both values, and why the drift was not a silent edit

**Both values.** `a0/a1/T1-EID.json` carried `EID*` =
`cddfa64ead571bbb09daa458c6b514377fba32e62612f5c2e17a6b49b7a78ab1` (frozen by
`bfbe74c2`, i.e. before the T1 fix). It now carries
`eccd859c921ae724602f09bb137f6081c8dced8631d758db9b6d0db110d7b861`, rebuilt with
`python3 a0/a1/t1_eid.py build` (the same command as `write`; the alias was added
because this assignment names `build`).

**Why it moved, and it is a dependency move, not an edit of the identity scheme.**
The `EvaluatorSource` component is built from `a0/tasks/maxcut/e_star.py` and
`e_star_child.py`. Commit `6dd717c2` ("the candidate launch must be a function of
the candidate's bytes alone") changed both files:

| file | before `6dd717c2` | at HEAD | working tree, when frozen |
|---|---|---|---|
| `e_star.py` | `670f02ee…` (43 410 B) | `fa0932b4…` (44 332 B) | `83d55e80…` (53 802 B) |
| `e_star_child.py` | `013f3e33…` (15 128 B) | `c08f0c36…` (16 397 B) | `7392915d…` (32 825 B) |

The document, the spec, the recipe and the five components are unchanged; what
changed is the material they are built from. `T1.contract.json` is byte-identical
across the re-freeze (`git diff` shows only `T1-EID.json` among the two): the spec
carries no evaluator hash material, so there is nothing in it to update — the
drift lives entirely in the EID document, which is exactly where a reader should
look for it.

**The consequence it had.** Every arm refused at its identity preflight, so the
calibration pilot could not measure a rate (`a0/a1/calibration/`), and
`python3 a0/a1/verify.py` was rc=5 with `t1-eid`, `wiring-simpleloop` and
`skeleton-dryrun` failing — the recorded A1 evidence described the tree *before*
`6dd717c2`. It is 6/6 again.

**What a third party re-derives.** `python3 a0/a1/t1_eid.py check` rebuilds every
component from the repository, cross-checks the `EvaluatorSource` records against
what `E*` itself hashes (`e_star.py digest`) and prints the recomputed `EID*`;
`python3 a0/a1/verify.py` prints the digest of every committed evidence file.

## D-A1-8 — **INTERFACE** — the candidate lane is closed by the *harness*, and `--net-isolate` alone was demonstrably not enough

**What was wrong.** `eval_service.py`'s frozen `maxcut` argv never passed
`--net-isolate`, so the candidate ran in the host's network namespace, and
nothing anywhere restricted what a candidate could *read*: the stored reference
partitions (`a0/tasks/maxcut/references/logs/partitions/**`) are one file per
graph at a predictable path, and a candidate that copies the best one scores
exactly `R` — on a certified instance, the optimum.

**What was done.** Two mechanisms, both on the harness side of the boundary:

1. `EVALUATORS["maxcut"]["argv"]` now carries `--net-isolate` (the task's own
   §4 mechanism, `D-T1-5`). It is inside the *frozen argv*, so a caller cannot
   forget it.
2. The service runs `E*` — and therefore every candidate `E*` spawns — inside
   `a0/a1/candidate_sandbox.py`: `unshare -rmnpf --mount-proc`, i.e. a fresh
   user + mount + network + PID namespace, with `/home`, `/tmp`, `/var/tmp` and
   `/run/user` replaced by empty tmpfs mounts and the invocation's own inputs
   bound back (`E*`'s two files, the interpreter's installations, the one graph
   the request names, the candidate's bytes, and the state/out directory). The
   lane's own self-check runs *before* `E*` is exec'd and refuses to measure if
   the roots are not hidden, the network is reachable or there is no PID
   namespace; the result is written to `<out>/sandbox_receipt.json`.
   `--candidate-isolation none` exists for a labelled control run and says so in
   `harness_identity.json` and on every response (`labelled_unsafe: true`).

**Is `--net-isolate` sufficient? No — measured, not argued.**
`a0/a1/probes/hostile_candidate.py` runs one hostile candidate (it tries the
network, the key file, `/proc/*/environ`, the stored witnesses — and *uses* the
best witness it can read as its answer) through four lanes. The harness's own
number, not the candidate's story, is the evidence:

| lane | network | `~/gptapi.md` | reference witnesses | key in `/proc` | harness score |
|---|---|---|---|---|---|
| `raw_pre_fix` (HEAD's `E*`, no flags) | **REACHED** | readable | **30 read, best used** | **found** | **224 = R = OPT** |
| `service_net_isolate_only` (`--candidate-isolation none`) | BLOCKED | **readable** | **30 read, best used** | — | **224** |
| `service_sandbox` (the default) | BLOCKED | not readable | 0 visible | not found | 0 (its honest fallback) |
| working-tree `E*` inside the sandbox | BLOCKED | not readable | 0 visible | not found | 0 |

13/13 checks pass on that probe (`a0/a1/evidence/hostile_candidate.json`). The
third row is the point: the lane still *measures* (status `ok`, a real Outcome,
`cut_edges = 0` for the all-zeros fallback) while every attack fails.

**INTERFACE change proposed, for the coordinator.** `INTERFACE.md` §12 forbids
letting the eval set into "any path a candidate can read" and §4 says a candidate
must not depend on external files, but no §4/§12 sentence says *who* enforces the
filesystem half, or that the harness does it with a namespace. The sentence I
would add, if the coordinator wants it binding:

> §4 (addition): the harness runs `E*` and every candidate it spawns inside a
> user+mount+network+PID namespace in which the repository is replaced by an
> empty tmpfs and only the invocation's own inputs are bound back
> (`a0/a1/candidate_sandbox.py`). `--net-isolate` closes the network;
> the mount namespace closes the filesystem; the PID namespace closes
> `/proc`. A campaign whose harness cannot establish it must not start.

## D-A1-9 — the harness no longer hands `E*` its own environment

**What was wrong.** The service spawned `E*` with `subprocess.run(...)` and no
`env=`, so `E*` inherited everything the harness process had been launched with —
including the provider key on any machine where the harness was started with it in
the environment. `/proc/<pid>/environ` is readable by the same uid, and the
hostile probe confirms the attack is real: in the unconfined lane the candidate
found `DEEPSEEK_API_KEY` in its ancestor's environment.

**What was done.** `E*` now receives `HOME`, `LANG`, a minimal `PATH`, `TMPDIR`
and `PYTHONDONTWRITEBYTECODE` and nothing else (`_evaluator_environment` in
`eval_service.py`), and the two places that start the service
(`probes/live_probe.py`, `skeleton.py`) launch it *without* the key at all. Two
independent closures: the key is not in the tree, and the PID namespace makes
`/proc/<pid>/environ` unreadable even if it were.

## D-A1-10 — **INTERFACE** — a harness-supplied score is bounded by the task

**What was wrong.** `--override` is deliberate: it is how "the runtime consumes,
it does not measure" is shown. But nothing bounded it. The service published
`9999` beside `true_value 132` for a graph with `|E| = 265`, `a0/contract`'s
trace validator accepted a fixture with every score at `9999`, and the gate's own
definitions would have computed `Δ = 37.23`, `ρ = −106.25` without complaint.

**What was done.** The bound is `0 <= cut_edges <= edges_total` for `maxcut`,
where `edges_total` is the Outcome's **own** number (the evaluator's statement
about this instance, not a constant the service keeps), and it is enforced at the
boundary where the service publishes a value:

* every published value is checked, including `E*`'s own — an Outcome whose own
  number is out of bound is refused (`failure.kind: implausible_outcome`);
* an override outside the bound is **refused by default**: `value: null`,
  `status: error`, `failure.kind: implausible_override`, booked with
  `override_rejected: true` and no handed value, so a number the task cannot
  produce never reaches a runtime's selection;
* `--override-mode labelled_implausible` publishes it **with the label** —
  `plausibility` on the response, on the handed Outcome and on the ledger row
  (`within_bound: false`, `verdict: accepted_labelled_out_of_bound`).

**Why refused-by-default and labelled-by-request, rather than merely flagged.**
A flagged-but-published number is still a number a selection can act on, and the
defect was precisely that nothing objected. The deliberate-lie probe must keep
working (it is the evidence for principle (ii)), so the mode that allows it
exists — but it cannot be reached by accident, and it cannot be silent.
`a0/a1/probes/score_bound.py` measures both sides through the real ABI: 5 cases,
7/7 checks, including `9999` refused in the default mode and published with its
label in the labelled mode, and `-5` refused too.

**The plumbing evaluator has no bound.** `sum_radii` has no `|E|`-like
denominator in its Outcome, so there is nothing to enforce; the service records
`score_bound: null` for it rather than inventing a constant. Named, not implied.

**INTERFACE change proposed, for the coordinator.** §5 makes `cut_edges` the
authoritative integer; the addition would be that a *harness-supplied* value for
it is bounded by the Outcome's `edges_total`, that the bound is enforced where the
service publishes, and that the deliberate-override mode is explicit. The
response schema also gains three fields (`plausibility`, `candidate_isolation`,
`override_mode`) and one on the refusal path (`override_rejected`) — additive, no
existing field changes meaning.

**Not fixed, in another workstream's directory — a minimal diff to consider.**
`a0/contract/trace_validate.py` validates a score event's `outcome` but never
compares `search_signal` against the metric's declared range, even though the
sample metric file already declares one (`a0/contract/fixtures/sample/metric.json`
has `"range": [0.0, 0.7853981633974483]`). The minimal diff, in the score branch
of `_check_event`, would be to take the metric definition in force (the file the
run's contract names) and, when it declares `range`, refuse a `search_signal`
outside it. That closes the trace-level half of the same defect; it is not this
directory's file, so it is reported rather than made.

## D-A1-11 — the evidence was refreshed; what is pre-fix and what is not

The recorded artifacts that carried the pre-fix evaluator digest
(`08281d21…`) were re-run against the current bytes. The table is in
`a0/a1/evidence/README.md`; in short:

| artifact | status |
|---|---|
| `wiring_simpleloop.json` | **refreshed** (carried `08281d21…`; now records the current evaluator, and one new check for the labelled override) |
| `live_simpleloop.json` | **refreshed** (paid; 1 model call) |
| `live_kapso.json` | **refreshed** (paid; 1 model call) |
| `live_controls.json` | **refreshed** (free) |
| `wiring_kapso.json`, `skeleton_dryrun.json` | **refreshed** (free; they carried no pre-fix digest but are re-produced so every artifact in the directory is from one run) |
| `score_bound.json`, `hostile_candidate.json` | **new** (this revision) |

The pre-fix versions are not duplicated: they are the committed bytes at
`4b94503e`, and `git show 4b94503e:a0/a1/evidence/<file>` retrieves any of them.

## D-A1-12 — another workstream is editing `E*` in the same working tree, and this freeze is a snapshot

While this workstream worked, `a0/tasks/maxcut/e_star.py` and
`e_star_child.py` were being edited *in place* by another workstream (they are
adding candidate filesystem isolation inside the loader —
`FS_ISOLATE_DEFAULT`, a mask policy, `ISOLATE_KEEP` — and the witness store under
`references/witnesses/`). `EID*` was therefore frozen against the bytes on disk
at the moment of the freeze (`e_star.py 83d55e80…`,
`e_star_child.py 7392915d…`), and `verify.py` is 6/6 for *that* revision.

**If those files change again before their commit lands, `EID*` is stale again**
and the one-command repair is:

```console
$ python3 a0/a1/t1_eid.py build && python3 a0/a1/verify.py
```

This is not a defect of the freeze; it is what a shared working tree does to a
content-addressed identity. It is recorded here because a reader who finds
`verify.py` red again should know which two files to blame, and that the identity
scheme itself is not in question.

**Overlap, stated plainly.** Their change and D-A1-8 close the same door from two
sides: theirs inside `E*` (masking the task directory, `.git` and the state roots
around the candidate), ours at the harness (the namespace `E*` itself runs in).
The hostile probe runs the working-tree `E*` *inside* this sandbox as a fourth
lane and finds it closed there too, so the two mechanisms compose rather than
conflict. If the coordinator prefers one mechanism, the harness-side one is the
one that also covers the *plumbing* evaluator, whose argv carries no
`--net-isolate` and which no other lane confines.

## What still cannot be enforced without root

The closure is namespaces, not virtualisation, and it is honest about the line:

* the candidate shares the kernel, so a kernel exploit is out of scope;
* `/usr`, `/lib`, `/etc`, `/dev` and `/proc/sys` remain readable: they carry no
  evaluation material, and hiding them breaks the interpreter rather than the
  attack. A secret placed under `/usr` would still be readable;
* there is no memory/CPU/disk cgroup, so a candidate can still exhaust the host
  (the anti-`fork` defence is still `τ` and the process-group `SIGKILL`, §7);
* the sandbox is a *user* namespace, so a candidate that finds a way to create
  another namespace with `CAP_SYS_ADMIN` inside it can mount things — inside its
  own mount namespace, which does not reach the host's;
* the harness process itself is not sandboxed: it holds the ABI directory, the
  ledger and the responses. A campaign that must survive a hostile *harness* needs
  a different boundary, and no such claim is made here.
