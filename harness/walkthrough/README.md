# walkthrough — dual-agent harness (task-independent `common/` + per-task `tasks/`)

Dual-agent runs of the H2 collaboration protocol: two continuous qwen sessions
in one sandbox container, rounds demarcated by git (`Round: N` commit trailers
+ tags), exchange recorded on the built-in board, and a PreToolUse hook gate
that makes the inter-agent barrier a kernel-side wait (bounded: the verdict
lands within a ~45 s hold, ahead of the tool client's 60 s hook wall; a
live-but-slow peer is handed to wait_peer.sh, then the commit is re-attempted).
Since 2026-10-11 the
tree is split into a task-independent layer (`common/` — reused as-is) and thin
per-task layers (`tasks/`); nothing in `common/` is copied per experiment and
nothing task-specific lives in `common/`.

## Layout

| path | role |
|---|---|
| `common/launch.sh` | **the** harbor launcher for dual-agent runs: task dir, mount, env-file, node/npm mirrors, `PYTHONPATH` (common + `$WT_AGENT_DIR`), `--artifact`, `--no-delete`; **cleanup policy**: a run whose collected `state.json` says `"normal": true` has its two Docker images removed (`task-restricted__<suffix>__{env-main,verifier__trial-main}`); any other outcome keeps them for forensics. Usage `launch.sh <job> <agent-spec> <mult>` (task launchers set `WT_AGENT_DIR`); `EXTRA_AE="K=V …"` adds `--ae` pairs |
| `common/dual_agent.py` | shared harbor agent base `DualAgentBase` (qwen-code install chain + wrapper exec parameterized by `run_script`/`run_timeout`/`run_log`) |
| `common/{gate.py,wait_*.sh,post-commit.sh,traj.py,traj_index.py,refs.py,recover.py,git_structure.py,front_phase.py,traj_stats.py,reference-transaction.sh}` | in-container harness tools (incl. the v3 front phase + SOP dispatch, recovery wake, and the ckpt-m* milestone-stats pipeline); each task's `run.sh` copies them into `/root/wt/` |
| `common/tests_{traj,refs,gate,recover,stats}.py` + `common/fixtures/` | TDD suites for the tools (run in place; self-contained fixtures = captured real dual-agent transcripts) |
| `common/harness-note.txt` | wait-semantics note (added during tumor-1) |
| `tasks/walkthrough/` | rehearsal task: `run.sh` (in-container wrapper; `WT_PROMPT` selects a prompt variant), `prompt.md` (v2 script), `prompt-w45.md` (v1 archive), `agent.py` (`WalkthroughAgent`), `launch.sh` |
| `tasks/tumor/` | tumor task: `run.sh`, `instruction.md`, `protocol-tumor.md`, `agent.py` (`TumorAgent`), `monitor_tumor.sh` (status ticker), `launch.sh` |
| `tasks/microarch/` | electrical-engineering task (`microarch-modeling`): `run.sh`, `protocol.md`, `instruction.md` (canary-free upstream copy), `agent.py` (`MicroarchAgent`), `launch.sh` (sets `WT_TASK_DIR` to `build/task-microarch`) |
| `verify/verify_acceptance.sh` | **unified** host-side acceptance for a finished job dir (families auto-dispatched; `--all <jobs-dir>` = full sweep; `verify_acceptance_tumor.sh` = compat shim) |
| `run_walkthrough.sh`, `run_tumor_launch.sh` | compatibility aliases to `tasks/*/launch.sh` |
| `walkthrough.env` | per-side credentials (A = deepseek, B = Token Plan), mode 600 |

Adding a task = a new dir under `tasks/` with its `run.sh` + prompts +
`agent.py` + a 4-line `launch.sh` calling `common/launch.sh`; no copies of
`common/` and no task names inside it.

## Acceptance (2026-10-10 ruling)

Normal exit (trial 0 exceptions; wrapper NORMAL in state.json), collection
complete under the job dir (protocol.bundle + git-log.txt + boards/ + chats/ +
x/ + state.json), and the collaboration reconstructible from the bundle:
`git clone protocol.bundle <scratch> && git log --graph --all` must show
the trunk with its round trailers and the milestone tags
`ckpt-m00/ckpt-m01/ckpt-m1/ckpt-m2` (2026-10-12 structure gate: exactly `main`
plus these four tags — side branches merged into main and removed at close-out,
`ckpt-final` no longer retained; see `common/recover.py` + `common/git_structure.py`).

**One command (2026-10-14):** `bash verify/verify_acceptance.sh <job-dir>` — the unified
entry (sections 0–6: runtime · NORMAL verdict · collection manifest · **top-level** bundle
clone + structure gate · verifier record · traj seal · `x/stats`). `--all <jobs-dir>` sweeps
every job dir; modern-era runs (ckpt-m00 / `x/stats` present) are strict, legacy eras
auto-downgrade to WARN; `sub-a/sub-b` may live only under `collect/snapshot/` when the
recover wake pruned the worktrees (accepted with a note).

## Cleanup (2026-10-11)

`common/launch.sh` removes the run's two images on a NORMAL verdict (kept
otherwise); verified ×10 across the w6-4×2 waves (2026-10-11). To check on a
future run: the launcher output carries `cleanup[<job>]`, and a NORMAL run's
suffix is gone from `docker images`.
