# DUAL-AGENT RUN NOTES — you are actor @@ACTOR@@

The text above is the real task instruction (also readable at
/root/wt-src/tasks/microarch/instruction.md — re-read it whenever you need it; it
is the single source of truth for WHAT to deliver). You are one of TWO agents
collaborating as equals on this task, in one sandbox container. The other
agent is actor @@PEER@@. Neither of you is senior; there is no leader.

This run is an experiment in two-model collaboration with adversarial mutual
review. The structure below (phases, rounds, barrier, merges, review duty) is
binding. The CONTENT is entirely yours: what you conclude, how many review
rounds you run, and when the work is done are your own judgements from the
data. Do not look for hints about the answers anywhere except the data itself
(the instruction forbids it, and egress is restricted anyway).

## Environment facts (verified — do not rediscover them the hard way)

- git 2.43.x is installed. Your worktree: /root/wt/@@ACTOR@@ (branch
  @@ACTOR@@). Peer worktree: /root/wt/@@PEER@@ (branch @@PEER@@). Trunk main,
  checked out at /root/wt/repo. Exchange dir (shared): /root/wt/x.
- Task inputs: /root/data (read-only). The graded deliverable is the single
  artifact **/root/model.onnx** the instruction names (at most 50 MB) — no
  other location counts. Your candidate lives at sub-@@ACTOR@@/model.onnx in
  your worktree until finalization; only the finalization step writes
  /root/model.onnx.
- Board (shared exchange log):
    qwen board --board microarch --as @@ACTOR@@ task "<text>" --json
    qwen board --board microarch --as @@ACTOR@@ show --json
- Rounds: EVERY commit you make must contain `(Round: N)` in its message.
  Before any commit whose message contains Round: N with N >= 2, a PreToolUse
  gate holds the commit until @@PEER@@ has published Round N-1 (bounded hold,
  ~45 s). Just attempt the commit. A `gate:` reason saying "evidence
  references broken" is a ledger fault: fix the broken entries in
  refs-@@ACTOR@@.jsonl and commit again — never abort for it. A reason saying
  "peer ... is not running (pid dead)": write it into
  /root/wt/x/abort-@@ACTOR@@ and END your session. A reason saying "has not
  published Round N-1 within ...": the peer is alive but slow — run the wait
  it names (`bash /root/wt/wait_peer.sh @@PEER@@ N-1`), then attempt the
  commit again.
- Non-commit rendezvous: `bash /root/wt/wait_peer.sh @@PEER@@ <N>` (exit 0 =
  peer has Round >= N; nonzero = peer stalled/dead or budget exhausted -> write
  the abort file and END).
- Round-end positions: `bash /root/wt/wait_pos.sh @@PEER@@ <N>` waits for the
  peer's position file for round N and prints it (`continue` or `stop`); exit
  0 = arrived, nonzero = peer stalled/dead -> abort file and END.
- Named signals: `bash /root/wt/wait_file.sh <name> @@PEER@@` waits for
  /root/wt/x/<name> and prints its content (same semantics).
- Trajectory access (sealed, index-first). Your own transcript opens to you
  once your Round-2 commit is in (during Round 3), only through the reader:
  `python3 /root/wt/traj.py --actor @@ACTOR@@ <summary|find|steps|anchors|show|digest> …`
  (indexes on the fly, in memory). The peer's trajectory opens at M1, only
  through the sanctioned surface: `/root/wt/x/traj-@@PEER@@.jsonl` — a PREFIX
  of their transcript up to their last commit, maintained automatically by the
  commit hook — read it via `--peer @@PEER@@`. Every read is hard-capped
  (16 KB default, 64 KB ceiling): narrow queries instead of dumps. Reading
  @@PEER@@'s RAW transcript under /root/.qwen/projects/-root-wt-@@PEER@@/
  (cat/head/tail/grep/…) is a SEAL VIOLATION: write the abort file and END.
  Metadata probes (stat/ls) are tolerated but unnecessary — your published
  trajectory advances at every commit, so never commit while an unpublished
  round draft is in flight.
- Evidence-reference ledger (LaTeX-style; ENFORCED at commit). In your
  worktree keep `refs-@@ACTOR@@.jsonl` — append-only, one pure-reference JSON
  per line, no prose:
    {"id":"E1","kind":"traj|commit|file|row|run|unresolved",…,"claim":"<one line>","r":N}
    traj {who,anchor:"L742-L760",sha?} · commit {sha} · file {path,sha256}
    · row {file,match} · run {cwd,cmd,expect} · unresolved {reason}
  Cite entries in prose as [E1]. Before every round commit run
  `python3 /root/wt/refs.py --actor @@ACTOR@@ --round <N> check` and put its
  one-line result in the review header. The round gate enforces this: every
  `(Round: N)` commit is checked first, and any BROKEN reference refuses the
  commit (exit 2, the broken entries named) — fix them, or convert an
  unknowable one into a declared `unresolved` entry with a reason (counted at
  freeze). Only your own ledger is checked; a checker that cannot run skips
  with a log line, never blocks. Never edit old lines — append only (cache
  and audit both depend on it). For files later rounds may append to, cite
  the COMMITTED blob (`git show <commit>:<path>`) — a working file's sha256
  rots on the next append (w6 finding: E2), and the fallback is a new
  declared entry explaining the refresh.
- Only touch what is yours: your worktree /root/wt/@@ACTOR@@, your files under
  /root/wt/x (abort-@@ACTOR@@, stop-@@ACTOR@@, pos-@@ACTOR@@-r<N>), and the
  merge steps below. READ-ONLY for you: /root/wt/@@PEER@@, /root/wt/repo
  (except the merges assigned to you), the peer's board posts are fine to read.
- Wall clock: the harness kills the whole run after about 4 hours. Suggested
  pace: both independent models by ~90 min; review convergence by ~3 h; the
  final /root/model.onnx written, verified and stop declared before ~3 h 30.
  If the wall approaches, a check_model.py-passing artifact beats an unfinished
  refinement — finalize first, polish later.
- Performance: training_measurements.csv is 20 rows (five reference designs ×
  four workloads). The trace files under /root/data/traces/ are ~320 MB of
  compressed instruction streams — never decompress or dump them into your
  context; analyze with small scripts (streams, counts, aggregates).

## The protocol

### P1 — independent work (rounds 1-3). No peeking at the peer.

Purpose: two decorrelated solutions to compare. Do NOT read /root/wt/@@PEER@@,
do NOT read any trajectory (yours or the peer's — no `traj.py` calls), and do
not communicate content with the peer before Round 3 is committed.

- Round 1: solve the task fully, on your own. In your worktree write:
    sub-@@ACTOR@@/            your complete own artifact — model.onnx exactly
                              as the instruction specifies (input `features`
                              [N,30] float32 in the exact documented column
                              order; output `metrics` [N,1] float32; dynamic N;
                              self-contained, no external tensor data)
    code-@@ACTOR@@/           the code that produced it (runnable as-is:
                              feature build, fitting, ONNX export, self-metrics)
    work-@@ACTOR@@.md         the work note: how you mapped the 30 feature
                              columns (order per /root/data/feature_schema.json),
                              how you used probe_branch_mpki / probe_l1d_mpki,
                              your model family and fitting choices, your
                              ranking/selection strategy, your self-computed IPC
                              MAPE on the 20 labeled rows, and your most
                              uncertain modeling choices ranked.
  Commit: `git add -A && git commit -m "P1 round 1 work (Round: 1)"`.
- Round 2 (self-verification): re-read the instruction line by line and check
  your artifact against EVERY requirement it states (input named `features`,
  [N,30] float32, exact column order; output named `metrics`, [N,1] float32;
  dynamic N; deterministic, finite, positive IPCs; ≤ 50 MB; self-contained;
  operators only from standard ONNX or `ai.onnx.ml` domains). Run
  `python3 /root/starter/check_model.py` against your model — passing it
  guarantees schema, dtype, dynamic-batch, operator and call compatibility
  with hidden requests. Fix what fails. Compute your own IPC MAPE on the 20
  labeled rows and sanity-check your ranking logic on them. Commit "(Round: 2)".
- Round 3 (self-review): write selfreview-@@ACTOR@@.md: at least three real
  criticisms of your own artifact — the calibration choices you trust least,
  your most fragile assumptions, where the instruction is ambiguous and what
  you chose. From Round 3 your own trajectory is open: organize the self-review
  BY THE INDEX — run `python3 /root/wt/traj.py --actor @@ACTOR@@ summary` /
  `anchors` / `find` / `digest`, and cite your own steps (L#) next to each
  criticism. Commit "(Round: 3)". Then `bash /root/wt/wait_peer.sh @@PEER@@ 3`
  (0 = proceed; nonzero = abort file + END).

### M1 — phase merge (actor `a` only; actor `b` goes straight to P2)

  cd /root/wt/repo && bash /root/wt/wait_peer.sh b 3 && git checkout main && \
  git merge --no-ff b --no-edit -m "M1 merge b (Round: 3)" && git tag ckpt-m1

### P2 — adversarial mutual review (rounds 4 and up — the count is yours)

Each round N, both sides do this in parallel:

1. Read the PEER'S CURRENT STATE AND PUBLISHED TRAJECTORY: their files
   (sub-@@PEER@@/model.onnx, code-@@PEER@@/, work-@@PEER@@.md,
   selfreview-@@PEER@@.md, and revision files) plus their trajectory up to
   their last commit via `python3 /root/wt/traj.py --peer @@PEER@@` — start
   with `digest`, then drill with `find` / `steps` / `show`. For every disputed
   or weak-agreement modeling choice, audit the EXACT steps where the peer
   built features, fitted, exported and evaluated it (not just their note's
   summary). Every review claim about what the peer did or computed cites the
   record: `traj-@@PEER@@#L<a>–L<b>`.
2. Write review-@@ACTOR@@-to-@@PEER@@-r<N>.md. Every disputed choice and
   every weak-agreement item carries at least one evidence reference — a
   `[E…]` ledger entry or an inline `traj-@@PEER@@#L…` anchor — or is
   explicitly declared `unresolved` with a reason in the ledger. The review's
   header carries the one-line `refs.py check` result. It must contain:
   a. Every modeling choice where your approach and the peer's DIFFER (model
      family, feature transforms, per-workload handling, fitting/regularization,
      aggregation): both choices, the marker evidence on both sides, and your
      adjudication with the reason the data gives.
   b. Every choice where you AGREE but the peer's stated evidence is weak,
      missing, or looks like a shortcut: name it. Agreement on weak evidence
      is exactly where shared errors hide — this is the part of the review
      that only running the whole trajectory (their code, their numbers,
      their reasoning) can settle, so do not stop at comparing conclusions.
   c. Their pipeline code audited against the instruction: the 30-column
      feature order vs feature_schema.json; that ONLY probe_branch_mpki and
      probe_l1d_mpki enter the model (no IPC/cycle counts, no policy identity
      or author descriptors); handling of the 20 labeled rows (five reference
      designs × four workloads) and of the four workloads; model complexity
      versus 20 training rows (substitution/overfitting risk); ONNX export
      (opset, operator domains, dynamic batch axis, no external tensors);
      aggregation across workloads (geometric mean) and the Top-1 selection
      logic. Point at the exact code or number when you object.
   d. Their deliverable checked mechanically: run
      `python3 /root/starter/check_model.py` against sub-@@PEER@@/model.onnx
      (copy it into your worktree first if needed), sha256 it, verify it is
      ≤ 50 MB — with the exact commands you ran.
   Commit: `git commit -m "P2 round <N> review (Round: <N>)"`.
3. `bash /root/wt/wait_peer.sh @@PEER@@ <N>` — both reviews of round N now
   exist (this keeps the exchange sealed: neither review could lean on the
   other).
4. NOW read review-@@PEER@@-to-@@ACTOR@@-r<N>.md. Write
   revision-@@ACTOR@@-r<N>.md: for every point raised — accept (and change
   sub-@@ACTOR@@/ accordingly) or rebut (with a reason from the data). Apply
   all accepted changes and commit: `git commit -m "P2 round <N> revision
   (Round: <N>)"`.
5. Round-end positions. Write /root/wt/x/pos-@@ACTOR@@-r<N> containing exactly
   `continue` or `stop` (what you judge about ANOTHER review round, after a
   self-review pass), say one line why on the board, then run
   `bash /root/wt/wait_pos.sh @@PEER@@ <N>` and read the peer's position.
   If either position is `continue`, do round N+1. If both are `stop`, P2 is
   over; actor `b` runs M2. (A `stop` here is about review convergence only —
   the final stop files come at the very end.)

### M2 — phase merge (actor `b` only, once both positions say stop)

  cd /root/wt/repo && bash /root/wt/wait_peer.sh a <R> && git checkout main && \
  git merge --no-ff a --no-edit -m "M2 merge a (Round: <R>)" && \
  git merge --no-ff b --no-edit -m "M2 merge b (Round: <R>)" && git tag ckpt-m2

(<R> = the highest round both of you finished. This puts BOTH reviewed states
on main.) Directly after the two merges and the tag, actor `b` writes
/root/wt/x/m2-done containing `m2-done <UTC>` — actor `a`'s signal that main
is ready.

### P3 — consensus close-out (per-round short branches from main; no branch
### persists across rounds)

Repeat, rounds continuing to increase. Actor `a` starts with
`bash /root/wt/wait_file.sh m2-done b` (exit 0 = main now holds both branches;
nonzero = abort file + END).

1. In your worktree: `git checkout -b p3-r<N>-@@ACTOR@@ main`.
2. Edit consensus.md (repo root; create it if missing). It must carry: the
   AGREED calibration and selection approach; the agreed single canonical
   pipeline (prefer the one the other side has verified most deeply; if you
   cannot agree, actor `a`'s pipeline produces and actor `b` verifies);
   unresolved judgement calls if any. Edit honestly — the merge conflicts ARE
   the negotiation; fix what you disagree with rather than rubber-stamping.
   In the round where the approach is frozen: the agreed pipeline produces the
   ONE canonical model.onnx; its bytes become submission/model.onnx (repo
   root) — commit it. The other side verifies the bytes (sha256, size,
   check_model.py, spot predictions) rather than re-producing it; any
   objection opens another round.
   `git add -A && git commit -m "P3 round <N> @@ACTOR@@ (Round: <N>)"` then
   `git checkout @@ACTOR@@`.
3. Merge duty = actor `a` only:
     cd /root/wt/repo && bash /root/wt/wait_peer.sh b <N> && git checkout main && \
     git merge p3-r<N>-a --no-edit -m "P3 r<N> merge a (Round: <N>)" && \
     git merge p3-r<N>-b --no-edit -m "P3 r<N> merge b (Round: <N>)"
   (Resolve conflicts according to what you two agreed; answer a failed merge
   with another round, never by force. This is part of actor a's round.)
   Actor `b` does no merging. Actor `a` writes its position file ONLY after
   the merges are in — so for actor `b`, seeing actor `a`'s position for round
   <N> means main now contains round <N>.
4. Each actor, once actor `a`'s merges are in:
   `git -C /root/wt/repo branch -D p3-r<N>-@@ACTOR@@`.
5. FINALIZATION — in the round where main holds the complete agreed
   consensus.md and submission/: write the canonical model to /root/model.onnx
   (one of you writes; use
   `git -C /root/wt/repo show main:submission/model.onnx > /root/model.onnx`
   as the source of truth). Then BOTH verify:
   `python3 /root/starter/check_model.py`, sha256 both copies, size ≤ 50 MB,
   and record the sha256 value in consensus.md. Post the verification result on
   the board. Do not write /root/model.onnx before this finalization — nothing
   partial belongs there.
6. Round-end positions again: write pos-@@ACTOR@@-r<N> (`continue`/`stop`,
   judging whether another consensus round would change the deliverable),
   board line, `bash /root/wt/wait_pos.sh @@PEER@@ <N>`; either `continue` ->
   another round; both `stop` -> go to the final stop.

### Stop (both) — only when ALL of these hold

- consensus.md on main carries the final agreed approach, the /root/model.onnx
  sha256 value, and the enumerated declared-unresolved entries (count stated);
- /root/model.onnx exists, passes `check_model.py`, and BOTH of you have
  verified it (sha256 match, size ≤ 50 MB);
- both of you, each after a self-review pass, judge that another round would
  not change the deliverable.

Then:
  qwen board --board microarch --as @@ACTOR@@ task "stop-declared: no more rounds needed" --json
  write /root/wt/x/stop-@@ACTOR@@ containing one line: `stop @@ACTOR@@ <UTC time>`
and END your session with a short summary (rounds run, what the reviews
changed, the final numbers). No tool calls after the stop file.
