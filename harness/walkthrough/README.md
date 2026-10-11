# walkthrough — dual-agent harness (task-independent `common/` + per-task `tasks/`)

Dual-agent runs of the H2 collaboration protocol: two continuous qwen sessions
in one sandbox container, rounds demarcated by git (`Round: N` commit trailers
+ tags), exchange recorded on the built-in board, and a PreToolUse hook gate
that makes the inter-agent barrier a kernel-side wait. Since 2026-10-11 the
tree is split into a task-independent layer (`common/` — reused as-is) and thin
per-task layers (`tasks/`); nothing in `common/` is copied per experiment and
nothing task-specific lives in `common/`.

## Layout

| path | role |
|---|---|
| `common/launch.sh` | **the** harbor launcher for dual-agent runs: task dir, mount, env-file, node/npm mirrors, `PYTHONPATH` (common + `$WT_AGENT_DIR`), `--artifact`, `--no-delete`; **cleanup policy**: a run whose collected `state.json` says `"normal": true` has its two Docker images removed (`task-restricted__<suffix>__{env-main,verifier__trial-main}`); any other outcome keeps them for forensics. Usage `launch.sh <job> <agent-spec> <mult>` (task launchers set `WT_AGENT_DIR`); `EXTRA_AE="K=V …"` adds `--ae` pairs |
| `common/dual_agent.py` | shared harbor agent base `DualAgentBase` (qwen-code install chain + wrapper exec parameterized by `run_script`/`run_timeout`/`run_log`) |
| `common/{gate.py,wait_peer.sh,wait_pos.sh,wait_file.sh,post-commit.sh,traj.py,traj_index.py,refs.py}` | in-container harness tools; each task's `run.sh` copies them into `/root/wt/` |
| `common/tests_{traj,refs,gate}.py` + `common/fixtures/` | TDD suites for the tools (run in place; self-contained fixtures = captured real dual-agent transcripts) |
| `common/harness-note.txt` | wait-semantics note (added during tumor-1) |
| `tasks/walkthrough/` | rehearsal task: `run.sh` (in-container wrapper; `WT_PROMPT` selects a prompt variant), `prompt.md` (v2 script), `prompt-w45.md` (v1 archive), `agent.py` (`WalkthroughAgent`), `launch.sh` |
| `tasks/tumor/` | tumor task: `run.sh`, `instruction.md`, `protocol-tumor.md`, `agent.py` (`TumorAgent`), `monitor_tumor.sh` (status ticker), `launch.sh` |
| `verify/verify_acceptance{,_tumor}.sh` | host-side acceptance checks for a finished job dir |
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
branches a/b/main, tags ckpt-m1/ckpt-m2/ckpt-final and the round trailers.

## Cleanup (2026-10-11)

`common/launch.sh` removes the run's two images on a NORMAL verdict (kept
otherwise); first-run verification of this behavior is pending the next
experiment launch (check `cleanup[<job>]` in the launcher output and that
`docker images` no longer shows the run's suffix).
