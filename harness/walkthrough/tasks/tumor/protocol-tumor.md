# DUAL-AGENT RUN NOTES — you are actor @@ACTOR@@

The text above is the real task instruction (also readable at
/root/wt-src/tasks/tumor/instruction.md — re-read it whenever you need; it is the
single source of truth for WHAT to deliver). You are one of TWO agents
collaborating as equals on this task, in one sandbox container. The other
agent is actor @@PEER@@. Neither of you is senior; there is no leader.

This run is an experiment in two-model collaboration with adversarial mutual
review. The structure below (phases, rounds, barrier, merges, review duty) is
binding. The CONTENT is entirely yours: what you conclude, how many review
rounds you run, and when the work is done are your own judgements from the
data. Do not look for hints about the answers anywhere except the data itself
(the instruction forbids it, and egress is restricted anyway).

## Environment facts (verified — do not rediscover them the hard way)

- git 2.43.0 is installed. Your worktree: /root/wt/@@ACTOR@@ (branch
  @@ACTOR@@). Peer worktree: /root/wt/@@PEER@@ (branch @@PEER@@). Trunk main,
  checked out at /root/wt/repo. Exchange dir (shared): /root/wt/x.
- Task inputs: /root/data (read-only). The graded deliverables are the five
  CSV files the instruction names, written to /root/results/ — no other
  location counts.
- Board (shared exchange log):
    qwen board --board tumor --as @@ACTOR@@ task "<text>" --json
    qwen board --board tumor --as @@ACTOR@@ show --json
- Rounds: EVERY commit you make must contain `(Round: N)` in its message.
  Before any commit whose message contains Round: N with N >= 2, a PreToolUse
  gate holds the commit until @@PEER@@ has published Round N-1 (bounded,
  ~15 min in 3 windows). Just attempt the commit. If it FAILS with a reason
  starting `gate:`, write that reason into /root/wt/x/abort-@@ACTOR@@ and END
  your session.
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
  pace: both independent submissions by ~90 min; review convergence by ~3 h;
  final files written, verified and stop declared before ~3 h 30. If the wall
  approaches, a complete schema-valid submission beats an unfinished
  refinement — finalize first, polish later.
- Performance: the data is large (sc_data.csv has 662k cells). Inspect files
  with small scripts (counts, aggregates, samples, hashes) — never dump whole
  CSV files into your context.

## The protocol

### P1 — independent work (rounds 1-3). No peeking at the peer.

Purpose: two decorrelated solutions to compare. Do NOT read /root/wt/@@PEER@@,
do NOT read any trajectory (yours or the peer's — no `traj.py` calls), and do
not communicate content with the peer before Round 3 is committed.

- Round 1: solve the task fully, on your own. In your worktree write:
    sub-@@ACTOR@@/            your complete own submission — the five CSVs,
                              exactly the names and columns the instruction
                              requires
    code-@@ACTOR@@/           the code that produced them (runnable as-is)
    work-@@ACTOR@@.md         the work note: the full 75-row cluster table
                              (cluster -> class), the marker evidence you
                              relied on for each decision (a compact per-cluster
                              or per-group table), the pipeline steps and exact
                              commands, and your most uncertain clusters ranked.
  Commit: `git add -A && git commit -m "P1 round 1 work (Round: 1)"`.
- Round 2 (self-verification): re-read the instruction line by line and check
  your five files against EVERY requirement it states (exact file and column
  names, one row per cluster / per region / per immune cell / per patient-state-bin
  / per state; every region of interest present; every immune cell present; the
  six immune states; the four distance bins; the responder definition; R/NR
  labels; the reliability test; units). Fix what fails. Spot-check the pipeline
  on a couple of regions by hand. Commit "(Round: 2)".
- Round 3 (self-review): write selfreview-@@ACTOR@@.md: at least three real
  criticisms of your own submission — your weakest clusters, your most fragile
  assumptions, where the instruction is ambiguous and what you chose. From
  Round 3 your own trajectory is open: organize the self-review BY THE INDEX —
  run `python3 /root/wt/traj.py --actor @@ACTOR@@ summary` / `anchors` /
  `find` / `digest`, and cite your own steps (L#) next to each criticism
  (e.g. "weakest: C66 — see L412, where I took the fusion call from 3 cells").
  Commit "(Round: 3)". Then `bash /root/wt/wait_peer.sh @@PEER@@ 3` (0 = proceed;
  nonzero = abort file + END).

### M1 — phase merge (actor `a` only; actor `b` goes straight to P2)

  cd /root/wt/repo && bash /root/wt/wait_peer.sh b 3 && git checkout main && \
  git merge --no-ff b --no-edit -m "M1 merge b (Round: 3)" && git tag ckpt-m1

### P2 — adversarial mutual review (rounds 4 and up — the count is yours)

Each round N, both sides do this in parallel:

1. Read the PEER'S CURRENT STATE AND PUBLISHED TRAJECTORY: their files
   (sub-@@PEER@@/*.csv, code-@@PEER@@/, work-@@PEER@@.md, selfreview-@@PEER@@.md,
   and revision files) plus their trajectory up to their last commit via
   `python3 /root/wt/traj.py --peer @@PEER@@` — start with `digest`, then drill
   with `find` / `steps` / `show`. For every disputed cluster and every
   weak-agreement item, audit the EXACT steps where the peer computed and
   decided it (not just their note's summary). Every review claim about what
   the peer did or computed cites the record: `traj-@@PEER@@#L<a>–L<b>`.
2. Write review-@@ACTOR@@-to-@@PEER@@-r<N>.md. Every disputed cluster and
   every weak-agreement item carries at least one evidence reference — a
   `[E…]` ledger entry or an inline `traj-@@PEER@@#L…` anchor — or is
   explicitly declared `unresolved` with a reason in the ledger. The review's
   header carries the one-line `refs.py check` result. It must contain:
   a. Every cluster where your assignment and the peer's DIFFER: both calls,
      the marker evidence on both sides, and your adjudication with the reason
      the data gives.
   b. Every cluster where you AGREE but the peer's stated evidence is weak,
      missing, or looks like a shortcut: name it. Agreement on weak evidence
      is exactly where shared errors hide — this is the part of the review
      that only running the whole trajectory (their code, their numbers,
      their reasoning) can settle, so do not stop at comparing conclusions.
   c. Their pipeline code audited against the instruction: territory geometry
      (closing radius, component size filter, connectivity), signed distance
      (sign, units, sampling pixel, rounding), the reliability test, binning,
      patient aggregation (the 20-cell floor, area-weighted sums), responder
      definition, enrichment, Mann-Whitney (mid-ranks, continuity correction,
      two-sided). Point at the exact code or number when you object.
   d. Their deliverable files checked mechanically (schemas, row counts, every
      region present, every immune cell present, R/NR usage) with the exact
      commands you ran.
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
   AGREED 75-cluster annotation table; the agreed pipeline/parameter
   decisions; the production plan for the final five files; unresolved
   judgement calls if any. Edit honestly — the merge conflicts ARE the
   negotiation; fix what you disagree with rather than rubber-stamping.
   In the round where the annotation is frozen: agree on ONE canonical
   pipeline (prefer the one the other side has verified most deeply; if you
   cannot agree, actor `a`'s pipeline produces and actor `b` verifies). That
   pipeline runs once from the agreed annotation and its five CSVs become
   submission/ (repo root) — commit them. The other side verifies the bytes
   (sha256, schemas, counts, spot checks) rather than re-producing them; any
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
   consensus.md and submission/: copy the five files from main's submission/
   to /root/results/ under the exact five names (one of you writes; you may
   use `git -C /root/wt/repo show main:submission/<name>` as the source of
   truth). Then BOTH verify: sha256 each file, compare against the git copy,
   re-run the instruction's mechanical checks (schemas, counts, every region,
   every immune cell) on the files at /root/results/, and record the five
   sha256 values in consensus.md. Post the verification result on the board.
   Do not write /root/results/ before this finalization — nothing partial
   belongs there.
6. Round-end positions again: write pos-@@ACTOR@@-r<N> (`continue`/`stop`,
   judging whether another consensus round would change the deliverable),
   board line, `bash /root/wt/wait_pos.sh @@PEER@@ <N>`; either `continue` ->
   another round; both `stop` -> go to the final stop.

### Stop (both) — only when ALL of these hold

- consensus.md on main carries the final agreed annotation table, the five
  /root/results sha256 values, and the enumerated declared-unresolved entries
  (count stated);
- the five files exist at /root/results/ and BOTH of you have verified them;
- both of you, each after a self-review pass, judge that another round would
  not change the deliverable.

Then:
  qwen board --board tumor --as @@ACTOR@@ task "stop-declared: no more rounds needed" --json
  write /root/wt/x/stop-@@ACTOR@@ containing one line: `stop @@ACTOR@@ <UTC time>`
and END your session with a short summary (rounds run, what the reviews
changed, the final numbers). No tool calls after the stop file.
