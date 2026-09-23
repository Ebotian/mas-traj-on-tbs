# Mechanism A feasibility: a long-lived CLI session with the repository hidden

**Question.**  Can an *agent* CLI session — the process that writes the candidate — run
inside a mount namespace with the repository, `.git`, `~/gptapi.md` and the answer stores
unreachable, while still reaching exactly one peer (its campaign's metering proxy) and
completing a real model call?

**Answer.**  **Yes, for every lane tested** — codex (the KAPSO T1 invocation shape) and
claude — with one operational caveat that is *not* about the namespace (host HTTP-proxy
environment) and one enforcement caveat that is (the driver must launch through the lane;
the kernel does not force it).  Measured, not inferred: both CLIs report their version and
complete a metered `deepseek-flash` call from inside the lane, with the answer stores and
the git objects gone from the filesystem.

Owner: `a0/a1/epistemic-ns/**`.  Nothing outside this directory was modified.  The T1
config, the frozen suite, `references/**`, the gate and the thresholds are untouched; the
required driver change is a **proposal**, below, not applied.

---

## 1. Verdict per lane

| lane | invocation shape tested | verdict | residual / where it breaks |
|---|---|---|---|
| **codex** (KAPSO `CodexCodingAgent`) | `codex exec --sandbox danger-full-access --skip-git-repo-check --color never --output-last-message … -m deepseek-flash -c model_reasoning_effort="low"`, argv rendered by the pinned adapter | **feasible** | the host's `http_proxy`/`https_proxy` must be stripped (else the CLI reroutes its egress to a proxy the closed netns cannot reach); the model must be one the meter serves (`deepseek-flash`), not the zjapi `gpt-5.6-terra` |
| **codex resume** (KAPSO inbox continuation) | the above + `--json` + `resume <thread> -` | **feasible** | needs `CODEX_HOME` bound back (or the thread store is lost) — supplied |
| **claude** | `claude -p "<task>" --output-format json`, DeepSeek Anthropic route | **feasible** | needs `CLAUDE_CONFIG_DIR` bound back; sends one `GET /api/hello` that the meter refuses (`path_not_routed`, unmetered, nothing forwarded) |
| **codex `workspace-write`** | the codex lane's *closed* sandbox posture | **not feasible for a model call** | codex's own sandbox blocks `socket()`, so it cannot reach the meter; the read jail must be the mount namespace, not the codex sandbox — the T1 lane's `danger-full-access` is what permits the call |
| **candidate lane** | (already built) `a0/a1/candidate_sandbox.py` | out of scope here | unchanged; this work adds the *agent* lane the review found missing |

There is **no** "not feasible" verdict for any lane we would actually run.

---

## 2. What was built

```
a0/a1/epistemic-ns/
├── session_sandbox.py    the boundary: mount-hide + netns + meter forwarder + supervisor
├── probe_inside.py       what a process sees from inside (runs under the sandbox)
├── probe_session_ns.py   the orchestrator that produces every artifact below
├── shim/codex            reference launcher shim (part of the proposal, not wired in)
├── REPORT.md             this file
└── evidence/             raw outputs: 10 JSON steps, raw meter ledgers, receipts
```

**The namespace stack** is `unshare -rmnpf --mount-proc` (user + mount + network + PID).
Inside, the sandbox:

1. `mount --make-rprivate /` — nothing propagates back;
2. brings the fresh netns' loopback up;
3. stages the allow-list, then mounts a **fresh tmpfs over `/home`, `/tmp`, `/var/tmp`,
   `/run/user`** and binds the allow-list back at its real paths;
4. runs `a0/a1/candidate_sandbox.py`'s own self-check (the mount is a tmpfs *of this
   namespace*, the device changed, the root is empty, egress is blocked, there is a PID
   namespace);
5. starts a **TCP→unix-socket forwarder** on the lane's loopback — the campaign's meter is
   exposed over a filesystem object (a unix socket), the only route out;
6. writes a receipt **before** the CLI runs, then supervises the CLI as a child (PID 1 is
   the supervisor, so the forwarder thread stays alive for the session's whole life).

The mount half is **imported whole** from `a0/a1/candidate_sandbox.py` — the same
`_hide`/`_restore`/`_self_check` the candidate lane probed 13/13 — so this is not a second,
independently-written hiding implementation.  What is new is the session half: its own
`HOME`/config, a writable workspace, the network path, and a long-lived supervisor.

---

## 3. Reachability — with a host-side control

`codex`/`claude` resolve under `/usr` and `/opt`, which are **not** hidden; the answer
stores, the repository and the key all live under `/home` and are.  From **inside** the
lane (`evidence/01_reachability_no_meter.json`), every forbidden path is absent — and the
control proves each exists on the host, so "absent" is *hidden*, not *never there*:

| path | exists on host | readable inside | error |
|---|---|---|---|
| `/home/ebt/rsi-dev` (repo) | true | **false** | FileNotFoundError |
| `/home/ebt/rsi-dev/.git` | true | **false** | FileNotFoundError |
| `/home/ebt/gptapi.md` (key) | true | **false** | FileNotFoundError |
| `…/references/targets.json` (R/OPT/U/R_source/role) | true | **false** | FileNotFoundError |
| `…/references/witnesses/commitments.json` | true | **false** | FileNotFoundError |
| `…/suite/eval/G_eval_0001.json` (held-out graph) | true | **false** | FileNotFoundError |
| `/tmp/maxcut` (scratch) | — | **false** | FileNotFoundError |

`/home` and `/tmp` list **empty** from inside (`entries: []`).  The **git route** the review
flagged is closed for this lane because the *repo is not there*: `git -C <repo> rev-parse
HEAD` is not executable (`git_route.executed = false`, reason "repo path is not present
inside the lane").

Both CLIs run: `codex-cli 0.155.1`, `2.1.278 (Claude Code)`.

---

## 4. Network — the meter, and nothing else

From inside, egress to `1.1.1.1`, `8.8.8.8`, `123.148.116.184` and DNS resolution of
`api.deepseek.com` are all blocked, while the campaign's meter is reachable **end to end**:
`evidence/02_reachability_with_meter.json` records an in-lane `GET /v1/models` through the
forwarder answered by the real provider, **HTTP 401 `Authentication Fails (governor)`** —
the request left the machine, so the loopback→unix-relay→proxy→DeepSeek path is live, and
an unauthenticated request is refused.  The sandbox's own self-check is written to a
receipt *before* the CLI runs (`evidence/codex_session_receipt.json`: `pass: true`,
`hidden_roots_are_tmpfs: true`, `hidden_roots_are_the_filesystems_this_lane_made: true`,
`egress: BLOCKED:gaierror`, `pid_namespace_is_private: true`, `meter: reachable`).

---

## 5. The real metered calls (the point)

Each was a genuine CLI session inside the lane, routed through `a0/meter/`, model
`deepseek-flash`.  Raw ledger rows are committed verbatim under `evidence/ledger_*.jsonl`
and re-derived by `a0/meter/verify_ledger.py` (`verify.returncode = 0` in each step JSON).

| session | left the CLI | meter rows | `CEq` | metered | note |
|---|---|---|---|---|---|
| codex, fresh (`08`) | `last_message: "OK"`, rc 0, **1.388 s** | 1 | **1020** | 1/1 | KAPSO `CodexCodingAgent` argv |
| codex, `--json` + `resume <thread>` (`09`) | **codeword `MARLIN7` recalled** across processes, rc 0 | 2 | **397 + 424 = 821** | 2/2 | `CODEX_HOME` state survived the resume |
| claude (`10`) | `stop_reason: end_turn`, rc 0, 2.46 s | 2 | **17399** | 1/1 | the other row is a **refusal** (`path_not_routed:/api/hello`) — nothing forwarded, nothing spent |
| PATH-shim proposal (`ledger_SHIM.jsonl`) | `last_message: "OK"`, receipt pass | 1 | **1020** | 1/1 | the driver-shim path, below |

**Committed-evidence cost: 20,260 `CEq`** (≈ $0.02 at the frozen `CEq`↔miss-token rate).
Including the host-side configuration checks and the failed first attempts, the whole round
is ≈ 41,000 `CEq` — cents, inside the "few hundred thousand" band.

The codex call is 1,020 `CEq` for a session whose *system prompt* is ~860 tokens; the
claude call is 17,399 `CEq` because Claude Code ships a ~17 k-token system prompt.  That
gap is the CLI's, not the mechanism's.

---

## 6. Operational cost and fragility

**Startup latency.**  `unshare` + the mount hide + the forwarder add a **median 51 ms per
session** (`evidence/03_latency.json`: bare `python -c pass` ≈ 0.006 s, in-lane ≈ 0.058 s).
Negligible beside a model call.

**What must be bound back** (the allow-list): the **workspace**, the session **`HOME`**, the
CLI **config home** (`CODEX_HOME` / `CLAUDE_CONFIG_DIR`), and the relay socket's directory.
System paths (`/usr`, `/lib`, `/etc`, `/opt`, `/dev`) are *not* hidden and need no entry.
This was proved, not assumed: `evidence/05_allow_under_hidden_root.json` places a workspace
**under `/tmp`** (a hidden root), binds it back, and shows it visible inside with its file
present — while a **sibling** of it under the same hidden root stays hidden
(`hidden_sibling_readable: false`).  The KAPSO live probe's run dirs are under `/tmp`, so
this case is real.

**What the CLI writes, and where.**  codex writes a lot, all under `CODEX_HOME`
(bound back): `sessions/**/rollout-*.jsonl`, `state_5/queue_1/thread_history_1/logs_2/
goals_1/memories_1.sqlite`, `shell_snapshots/`, `thread-writer-locks/`, `skills/.system/`,
`installation_id`, `tmp/arg0`, `.sandbox_migration` — **and `$HOME/.codex/tmp`**, a second
location, so `HOME` must be bound too.  claude writes under `CLAUDE_CONFIG_DIR`
(`projects/`, `sessions/`, `.claude.json`, `backups/`, and a `telemetry/1p_failed_events…`
queue because telemetry cannot leave the netns).  Nothing silently fails for lack of a
bound path in these runs.  Writes that *would* land outside the allow-list land in the
fresh tmpfs and vanish: the canary test
(`evidence/07_canary_leak.json`) writes `/tmp/.a0a1_epistemic_leak_canary` and
`/home/.a0a1_epistemic_leak_canary` **inside** the lane and both are **absent on the host**.

**Entered differently / nested.**  The lane tolerates nesting: inside it, `unshare -r` and
`unshare -m` both succeed (`rc 0`), and a **child that unshares the mount namespace still
sees the hidden `/home`** (`child_mountns_sees_home_entries: 0`) — the hide is inherited, so
a CLI that spawns its own namespace (both do, for their sandboxes) does not escape it.  All
visible PIDs share the lane's mount namespace (`all_visible_share_my_mountns: true`, 2
visible PIDs).  codex's `workspace-write` sandbox sets up fine inside the lane and then
**cannot call the model**: it reaches `ERROR: Reconnecting... waiting for network` — its
own seccomp blocks `socket()` (consistent with
`a0/notes/exit-closed/local-model/evidence/codex_and_netns.txt`).  So for a *metered* lane,
`danger-full-access` is required and the read jail is the namespace, not the codex sandbox.

**The one non-namespace caveat (measured, and it cost a wasted run).**  The host exports
`http_proxy=https_proxy=http://127.0.0.1:7890`.  A CLI that honours it reroutes its model
request to that proxy — reachable on the host, **unreachable inside the closed netns** — and
every call dies with `Connection failed: error sending request` /
`Reconnecting... waiting for network` while the meter stays empty.  The lane must **strip
every proxy variable** (`http_proxy`, `https_proxy`, `all_proxy`, `no_proxy` and the
upper-case forms).  This is true of the *closed* netns; on an allowlist network it would be
a silent egress leak.  The orchestrator does this in one place (`_base_env`).

**Locking / lifecycle.**  The sandbox is PID 1 and supervises the CLI as a child, so the
forwarder thread outlives the whole session — but killing the supervisor without killing
its child can orphan the CLI; the harness should kill the process group.  Nothing else is
stateful.

**Cost of the relay.**  The relay socket is created under `/dev/shm` (world-writable) so the
in-lane forwarder can reach it; it is reachable by any host process too.  It is a byte pump
with no policy — the policy is in the metering proxy — but it is not a private channel.  If
the harness puts it under a hidden root, `prefix()` binds its directory back.

---

## 7. Enforcement posture

**ENFORCED** (a correctly launched session cannot break it):
- **File hiding.** A process in a mount namespace has no handle to the parent's mount
  table; the only paths the session can read are the allow-list plus the shared system
  directories.  A nested `unshare -m` child still sees the hidden roots.
- **Network closure.** A fresh netns with only its own loopback; the sole reachable peer is
  the forwarder, which relays to exactly one unix socket.
- **PID privacy.** A fresh PID namespace and `/proc`; the session cannot enumerate or read
  other processes (so it cannot read the runtime's key out of `/proc/<pid>/environ`).
- **Fail-closed.** No `unshare`, a failed mount, an unreadable mount table, a hidden root
  that is not this lane's own tmpfs, reachable egress, no PID namespace, or an unreachable
  meter forwarder ⇒ exit 3 **and no measurement** (the receipt records the refusal).

**PROBED** (measured here, each with its raw artifact): the reachability table and its host
control (`01`), the end-to-end meter path (`02`), both CLIs' versions (`01`), the three
metered calls and the resume (`08`–`10`, `ledger_*`), the bind-back under a hidden root
(`05`), the canary (`07`), latency (`03`), nesting (`04`), the workspace-write failure
(`06`), and the PATH-shim launch (`ledger_SHIM`, `shim_receipt`).

**DECLARED** (true of the mechanism but **not** enforced by the kernel here):
- **The launch site is the enforcement.** A session the driver starts *without*
  `session_sandbox.prefix()` (or the shim) is not in the namespace at all and is
  unconstrained.  There is no kernel-level guard that a future call site uses the lane — the
  guard is that the call site *is* the lane.  This is exactly the residual the candidate
  lane also has, and it is why §8 proposes a launch-site change rather than a config flag.
- **Shared system directories and kernel.** `/usr`, `/lib`, `/etc`, `/opt`, `/dev` and the
  kernel are shared with the host.  They carry no evaluation material, but they are not
  hidden and a kernel exploit is out of scope.
- **The relay and the meter are trusted components.** The proxy is the whole metering
  claim; the relay adds no policy.
- **Proxy-env hygiene is the runner's job**, not the sandbox's (see §6).
- **The blinding is of *files*, not of *everything an agent could infer*.** The mount
  namespace hides the answer stores; it does not address the review's other points
  (evaluator accessibility, selection conditioning) — those are KID/contract questions,
  outside this assignment and not touched.

---

## 8. Proposal: how the driver must launch the lane (a diff, not applied)

In the current T1 build the codex lane is **not actually exercised** — the adapter's seams
replace the model-dependent phases (`a0/runtimes/kapso/a0_adapter/seams.py`), and the T1
config's codex lane is a placeholder whose model (`gpt-5.6-terra` via zjapi) the closed
topology cannot reach.  So the change below is for the *future* campaign that runs the real
codex lane; it is the minimal way to make that lane blinded, and it touches **only where the
lane is launched**, not the frozen tree.

**The enforcement point.**  The upstream adapter resolves `codex` by name
(`shutil.which("codex")`, then `subprocess.Popen(["codex", …])`) and copies its own
environment into the child.  The project already uses this lever: `a0/runtimes/kapso/
a0_adapter/closure.py:108-109` prepends a directory to `PATH` to pin `python`.  The same
lever, a directory holding one shim named `codex`, makes the adapter's own call site run
inside the lane — **with no edit to the upstream adapter**:

```diff
--- the process that launches the T1 campaign (where it assembles the child env,
+++ e.g. the runner around `a0/a1/kapso_t1/runtime_t1.py::prepare`, or `live_t1.py`)
@@
+from pathlib import Path
+SHIM_DIR = REPO_ROOT / "a0" / "a1" / "epistemic-ns" / "shim"
+os.environ["PATH"] = str(SHIM_DIR) + os.pathsep + os.environ["PATH"]   # mirrors closure.py:108-109
+os.environ["A0_EPISTEMIC_NS_REAL_CODEX"] = "/usr/bin/codex"            # absolute: no shim recursion
+os.environ["A0_EPISTEMIC_NS_PORT"]  = str(campaign_meter_port)
+os.environ["A0_EPISTEMIC_NS_SOCK"]  = str(relay_sock)                  # host relay unix socket
+os.environ["A0_EPISTEMIC_NS_RECEIPT"] = str(run_dir / "epistemic_ns_receipt.json")
+os.environ["CODEX_HOME"] = str(run_dir / "session" / "codex_home")     # bound back, writable
+os.environ["HOME"]       = str(run_dir / "session" / "home")           # bound back, writable
+for name in ("http_proxy","https_proxy","all_proxy","no_proxy",
+             "HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","NO_PROXY"):
+    os.environ.pop(name, None)                                         # §6: never reroute egress
```

`a0/a1/epistemic-ns/shim/codex` (committed here) is the referenced shim; it `exec`s
`session_sandbox.py shim`, which reads the env above and re-launches the real binary inside
the lane.  **This path is verified end to end** (`evidence/shim_receipt.json`,
`evidence/ledger_SHIM.jsonl`): with the shim first on `PATH`, a bare `codex` invocation —
exactly the adapter's shape — ran in the lane, wrote a passing receipt, returned `"OK"`, and
left one metered row of **1020 `CEq`**.

**Alternatives, weaker.**  A config-only change
(`coding_agent.agent_specific.env_overrides.PATH = "<shim>:/usr/bin:/bin:…"`) works but
hard-codes `PATH` and would conflict with `closure.py`'s venv prepend; the code path above
composes with it.  Do **not** try to blind the lane with
`agent_specific.sandbox = workspace-write`: that is a write/network restriction, not a read
jail, and it also blocks `socket()` (§6) so the lane could not call the model.

**Two consequences the campaign owner must decide, not this report:**
1. A blinded lane in the *closed* topology can only use a model the meter serves
   (`deepseek-flash`).  The T1 placeholder's `gpt-5.6-terra` is unreachable once the netns
   is closed; either the lane's model changes or the lane is (metered and) allowlisted to
   its provider.
2. This is a launch-site change; it belongs with the contract revision the user holds,
   because it makes the agent lane's knowledge a *stated and enforced* part of the design.

---

## 9. The one command a third party reruns

Spends cents (the metered calls above).  The key is read into an env var in the same
command and never printed or written:

```bash
cd /home/ebt/rsi-dev && export DEEPSEEK_API_KEY=$(awk -F: '/^deepseek:/{sub(/^deepseek:[ ]*/,""); print; exit}' ~/gptapi.md) \
 && python3 a0/a1/epistemic-ns/probe_session_ns.py --out /dev/shm/a0a1-epistemic/evidence
```

No spend, for the reachability/network/fragility half only:

```bash
cd /home/ebt/rsi-dev && python3 a0/a1/epistemic-ns/probe_session_ns.py --out /tmp/ns-nospend --skip-real-calls
```

Independent re-derivation of any committed ledger:

```bash
python3 a0/meter/verify_ledger.py a0/a1/epistemic-ns/evidence/ledger_NS_CODEX.jsonl
```

---

## 10. What I could not verify (and other honest limits)

- **Enforcement against a hostile *harness*.**  The lane is enforced *for sessions launched
  through it*; I did not and cannot prove a future call site uses it.  That is the §8
  proposal, and it is a policy decision, not a measurement.
- **A real KAPSO campaign through the lane.**  The T1 build's seams skip the real codex
  session, so I tested the adapter's **invocation shape** (argv rendered by the pinned
  adapter) rather than a full KAPSO iteration.  The argv is the adapter's own; the
  surrounding strategy loop is not exercised here.
- **The zjapi `gpt-5.6-terra` route inside a closed netns.**  It is not metered and not on
  an allowlist, so I did not run it; §8 states the consequence instead of guessing.
- **Newer/other lanes** (opencode/kilo/loreley), which the review also flagged as
  unmeasured, are still unmeasured here — the assignment asked for codex and claude.
- **`no_proxy`-style bypasses and non-HTTP transports** (websockets): codex 0.155.1 is
  Responses-over-HTTP and worked; a lane using `responses_websocket` was not tested.
- **The host `/tmp` artifacts** (`/tmp/claude-1000`,
  `/tmp/codex-bwrap-synthetic-mount-targets-*`) are from the **host-mode** configuration
  checks, not from any in-lane run: their mtimes (11:12, 11:17) predate the in-lane runs
  (11:24–11:25) which left them unchanged, and the canary test independently shows in-lane
  `/tmp` writes do not reach the host.
- **Signal/orphan hygiene** (killing the supervisor without its child) is stated as a
  fragility, not fixed — the driver should kill the process group.
