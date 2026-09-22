# `a0/a1/kapso_t1/DEVIATIONS.md` — every place this retarget departed, and why

Seven departures, all load-bearing for what the evidence in `README.md` may be used to
claim. Nothing here is silent. The binding authority is `a0/tasks/maxcut/INTERFACE.md`;
where an example in that file disagrees with a formula, the formula wins.

---

## D-KT1-1 — T1's registered tree is built here, not by the adapter's tree writer

**What.** `a0/runtimes/kapso/a0_adapter/registered_tree.py` writers the plumbing task's
tree. It cannot write T1's:

* its `WRAPPER_SOURCE` is `a0_adapter/registered/kapso_eval.py`, which runs the
  *plumbing* `E*` with `--fidelity/--fraction/--n/--runs/--runtime-budget-ms`;
* its `build_locator` reads `theta["n"]`, `theta["runs"]` and
  `theta["runtime_budget_ms"]`, and T1's `theta_e_canonical` is `{seed, timeout_s}` —
  T1 has no fidelity classes and no subsampling (`T1-EID.json` Config
  `theta_e_semantics`), so the plumbing keys do not exist.

**What was done instead.** `a0/a1/kapso_t1/tree.py` supplies T1's counterpart, with the
same contract: two files, a locator that pins the evaluator's identity, and
`EID_r = manifest_fingerprint(tree)` computed by KAPSO's own function
(`evaluation_integrity.py:112-119`), imported rather than re-implemented (with a local
fallback that says so when the import is unavailable outside the adapter's interpreter).
`runtime_t1.bind_t1_task()` points `KapsoRuntime.prepare` at it.

**Not claimed:** that T1's locator schema (`a0.kapso.registered_locator/v2`) is the
plumbing schema. It is a superset in the fields T1 needs (graph sets and their
visibility, the candidate ABI, the metric's failure semantics) and a subset in the ones
T1 does not have (fidelity classes, `n`, `runs`).

---

## D-KT1-2 — the T1 task text is bound by rebinding three names in the adapter module

**What.** `a0/runtimes/kapso/a0_adapter/runtime.py` holds the plumbing task's text as
module constants (`GOAL`, `PROBLEM`) and imports the plumbing tree writer
(`install_registered_tree`).

**What was done instead.** `runtime_t1.bind_t1_task()` rebinds those three module
attributes before `prepare()` (`runtime.py` reads them as globals at call time), and
records what it replaced in the artifact. No file under `a0/runtimes/kapso/` is edited —
it is another workstream's tree — and the same idiom (`install_seams`) is what the
adapter itself uses to replace upstream call sites.

**Consequence.** The rebinding lasts for the life of the process, so a T1 run must be its
own process, separate from any plumbing run. Both probes are; `runtime_t1` says so in the
binding record (`notice`).

---

## D-KT1-3 — C*(T1) is loaded here, because the adapter's loader cannot read it

**What.** The adapter's `common.load_candidate_set` requires `path` and
`solution_sha256` per candidate. C*(T1)'s manifest
(`a0.candidateset/v1`) records `dir` plus a `files[]` digest list instead.

**What was done instead.** `t1_binding.load_candidates` reads T1's schema, re-hashes every
`solution.py`, cross-checks it against the manifest's own record, and returns the
adapter's own `Candidate` objects (so `KapsoRuntime` needs no change). The manifest file's
sha256 is also what `EID*`'s `DataManifest` records for it, which the binding reports.

---

## D-KT1-4 — the T1 spec is located here, because the two conventions differ

**What.** `evalcontract.py verify` looks for the spec relative to the EID document's own
directory by default, and the adapter's `verify_eid_star` helper additionally tries
`config.a0_root / spec`. Both are the plumbing convention: `plumbing.EID.json` records
`"spec": "contract/plumbing.contract.json"` (a0-root-relative). `T1-EID.json` records
`"spec": "a0/a1/T1.contract.json"` (repository-root-relative), so neither lands on it, and
the adapter's helper raises `EID* verification failed` on a *valid* T1 document.

**What was done instead.** `t1_binding.locate_spec` tries the a0 root, the repository
root and the document's own directory, and passes `--spec` explicitly. `T1-EID.json` is
another workstream's frozen document and is not edited.

**Worth passing on:** the two documents disagree about what `spec` is relative to. A
consumer that follows either convention will mis-resolve the other's document.

---

## D-KT1-5 — the T1 stub **reports** C* membership and does not **enforce** it

**What.** The plumbing tree's `kapso_eval.py` refuses to run (exit 3, no manifest line)
when the candidate's `solution.py` is not a member of the frozen set, unless the locator
sets `allow_unfrozen_candidate`.

**What was done instead.** T1's stub reports `candidate_identity`
(`present`, `solution_sha256`, `in_frozen_set`, `candidate_id_if_frozen`) in its manifest
line and never refuses on that basis. Reason: in an A1 campaign the arm under test writes
*new* bytes — that is what a search is — and a registered evaluation that refuses them
would be unrunnable in the very campaign this tree exists for. The frozen `C*(T1)` set is
the A0 conformance set, not the campaign's candidate space.

**Consequence, stated plainly.** The C* gate is not an integrity gate in T1's tree: a
candidate outside C* is measured, and its membership is visible in the recorded line.
What still cannot happen is a *doctored* evaluation: the tree is fingerprinted into
`EID_r` and re-synced into every frame run, so a candidate that edits `kapso_evaluation/`
gets `evaluation_valid=False`, `score=None` (measured, `dryrun_t1.json` node 3).

---

## D-KT1-6 — the frame-run path is not supported, and it is (measured) unreachable here

**What.** KAPSO's `execute_registered_evaluation` (`registered_evaluation.py:162-285`)
does `score = float(manifest["score"])` on the registered command's line. T1's stub prints
no `score` key — deliberately, because the harness authors the score after the session —
so a frame run raises `KeyError: 'score'`.

**Measured, not assumed.** `evidence/dryrun_t1.json` → `controls.frame_run.outcome.raised
= "KeyError: 'score'"`.

**Why it is unreachable in this configuration.** The frame run has exactly two callers:
`_run_validate` (a VALIDATE fidelity grant) and `run_bridge_evaluation` (an evaluator
transition). `config/mode.maxcut.yaml` sets `budget.fidelity.mode: "off"`, under which the
grant is always `FULL_PASSTHROUGH` (`fidelity.py:318-324`), and
`evaluation_maintainer.max_change_requests: 0`, which admits no change request and
therefore no transition.

**What it would take to close it.** Either the stub gains a declared scalar for the
frame-run path (which must come from the harness, or it is a fabricated measurement), or
the two frame-run entry points are declared out of scope for the T1 arm. Both are
campaign-design decisions, and neither is made here; a campaign that enables fidelity
profiles or accepts a change request will hit this.

---

## D-KT1-7 — the `AID_r` factors for the registered tree are proposed, not adopted

**What.** `a0/a1/declaration.py` (another workstream's file) builds `CID` and the two arms'
`AID_r`. The KAPSO arm's `AID_r` names the mechanism
(`runtime.outcome_lane`, `runtime.checkout`, `runtime.grant_triple`,
`runtime.attribution_caveat`, `runtime.substrate`) but **not** the registered evaluation
tree it runs, whose identity is `EID_r`.

**What was done instead.** `binding.json` carries `proposed_aid_r_factors`
(`runtime.registered_evaluation_tree`, `runtime.registered_evaluation_tree_files`) with
the identities and the rationale, for the declaration's owner to adopt. The declaration
file itself is not edited.

**Why it matters.** Until it is adopted, two different registered trees could sit under
one `AID_r` — one arm with two measurements, which the CID rule ("if an object can change
P(Y|r) it must be inside CID or AID_r") does not allow.

---

## Not a deviation, but worth recording

* **The adapter labels its harness request with the node, not the candidate.**
  `PostSessionManifest.amend` composes `candidate_id=f"node{node_id}"`. A1's evaluation
  ledger is per-candidate (`a0/a1/eval_service.py`'s `--override` map is keyed by candidate
  id), so the probes wrap the client (`runtime_t1.T1HarnessEvalClient`) and relabel on
  their side; every substitution is recorded in `relabelled_requests`. The row's
  `candidate_source_sha256` is unaffected either way, so both identities stay joinable.
* **`protected_data_paths` is a T1 addition.** The plumbing mode config has none. Naming
  `kapso_datasets/maxcut/dev` there makes KAPSO hash the visible instances into the
  evaluator version and void any node that rewrites them — the executable half of
  `INTERFACE.md` §12's "the eval set must not enter an agent workspace", extended to
  "the dev set must not be edited either".
* **`deepseek-flash` answers inside `reasoning_content`** on the DeepSeek chat face
  (`content: ""`, `finish_reason: "length"`, `completion_tokens_details.reasoning_tokens
  = 256`). The probe reads both fields and records which one carried the answer; a lane
  that read only `content` would look like a model that never answered.
* **The candidate ABI is a declaration in two places** (`task.py::CANDIDATE_ABI` and the
  locator's `candidate_abi`), and the dry run asserts they are equal, so the text the
  agent is shown and the configuration the tree registers cannot drift apart silently.
