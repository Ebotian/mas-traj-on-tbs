# `a0/verify/a1-delta/DEVIATIONS.md` — how this pass departed from the brief, and why

Owner of `a0/verify/a1-delta/**`. Nothing here fixes anything; it re-derives the fixes,
reports, and names what it could not reach. Findings are in `REPORT.md`; this file records
the interpretations I had to make and the two things a reader should not mistake for the
artifacts' own claims.

---

## D-VD-1 — "the fixes themselves" are the object of study, so the fixes' own scripts are evidence, not ground truth

Every probe recomputes from bytes with its own implementation of the recipe, and reads the
author's artifact only to ask whether the recorded value equals the recomputed one:

* `EID*` — canonical JSON (`sort_keys`, `(",", ":")`, `ensure_ascii`) plus the
  `a0/evalcontract/v1` domain separator, re-implemented from the rule `evalcontract.py`
  documents, not imported from it. `d1` then also calls `t1_eid.build_spec()` so the
  *material* is the author's, never the hash.
* the tree's `EID_r` — KAPSO's `sha256(json.dumps(manifest, sort_keys, separators))`, taken
  from the quote in `tree.py`'s docstring. `build_tree.py check` is a step of
  `kapso_t1/verify.py` and is reported as the author's own claim, separately.
* the gate leaf diff — my own walker (`d3`), not `restamp_evidence.py`'s `refreeze_evidence.walk`.
* the sandbox — my own canary files, my own lane reader, my own positive control. I did not
  read their canary, their receipt or their hostile probe.

## D-VD-2 — `d2` monkeypatches two module constants, in-process

`declaration.KAPSO_T1_TREE` and `declaration.KAPSO_T1_BINDING` are pointed at a scratch tree
for the disagreement construction. The module documents this use (`_rel`'s fallback: "the
unit tests do, to build the disagreement case"), and the patch is undone in a `finally`.
Nothing on disk moves; the scratch tree is a `tempfile` directory.

## D-VD-3 — running two entry points rewrote a committed artifact; both were restored

* `python3 a0/tasks/maxcut/gates/restamp_evidence.py` (its **documented** invocation, no
  `--before`) rewrites `a0/tasks/maxcut/gates/restamp.evidence.json` with
  `before_revision: HEAD`. Restored with `git checkout -- a0/tasks/maxcut/gates/restamp.evidence.json`
  and compared against a pre-run copy: byte-identical. The meaningful invocation
  (`--before 7bf8a14b`) is run with `--out` inside this directory.
* `python3 a0/tasks/maxcut/conformance.py --check` rewrites
  `a0/tasks/maxcut/conformance.report.json`. Restored the same way.

`git status --porcelain` is empty apart from this directory afterwards. The report says
what each rewrite changed.

## D-VD-4 — I wrote four files outside the working directory, transiently, because the brief asked for that test

`d4_canary.py` writes one canary under `/tmp`, `/var/tmp`, `/home/<user>` and
`/run/user/<uid>`, plus one allowed control under `/tmp` and `/var/tmp`, and deletes all six
at the end (its output lists them). Those are the only writes outside `a0/verify/a1-delta/`
apart from the two artifact restorations above. No byte of any other file was read:
`/home/<user>` was touched only to create and remove the canary; `~/gptapi.md` was never
opened; `/proc/*/environ` was never read.

## D-VD-5 — the sandbox canary is a *reader inside the lane*, so it needs a control

A "not readable" result is worthless if the reader is broken. `d4` therefore hands the lane
a control file under the *same* hidden root through the allow-list and requires it to come
back byte-equal, and it runs the pre-fix module on the identical canaries. Both are in the
output; the pre-fix run is what makes "the fix is a real change" a measurement.

## D-VD-6 — `d6`'s labelling judgement is a heuristic, and it is printed

The criterion is "asserts the digest *as current*". For JSON the test is structural (a digest
under a `before_side`/`pre_fix`/`comparison` path is a past value, even when the marker is
hundreds of lines away — a line window cannot see that). For prose the test is line-scoped
plus the enclosing heading: a window of ±N lines mislabels a present-tense claim because an
unrelated row nearby names the current value, which is exactly what happens in
`WIRING-REPORT.md`'s verdict table. The per-line judgement is in
`out_d6_superseded.txt`, and §5b of the report names the three items the heuristic flags but
which I read as labelled by context.

## D-VD-7 — what I did not do

* No fix, no threshold change, no gate re-run, no `B_hard` rewrite, no `T1-EID.json`
  re-freeze, no edit to `a0/a1/kapso_t1/**`, no campaign, no paid probe, no model call.
* I did not touch `/home/ebt/kapso_ck/`, `/tmp/eve/`, or the `adapdc-catalog-postgres-1`
  container; I did not read any credential file.
* I ran `a0/a1/probes/hostile_candidate.py` with `--out-dir /tmp/a1delta-hostile`: it makes
  the hostile candidate's own TCP connects (that is the probe) but no model call and no
  CEq, and it left the repository untouched (`git status` checked).
* I committed **only** `a0/verify/a1-delta/**`.

## D-VD-8 — the one claim I make about another workstream's *mechanism*, and its limit

§2 says the causal audit does not catch a `CID`-vs-tree content disagreement. That is a
finding about a gap in a check, demonstrated by constructing the state (a stale tree with a
binding re-stamped to match). It is *not* a claim that the current artifacts disagree — they
agree, and I recomputed both sides. Whether to close the gap is the declaration owner's call;
it is a change to another workstream's file.
