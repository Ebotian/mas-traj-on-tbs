# Mechanism C — can the agent lane run inside a container that sees only the workspace?

Owner: `a0/a1/epistemic-container/**`. All measurements 2026-09-23 (CST, UTC+8) on this host.
Everything below is **verified by running it** unless the line says *read from source* or
*inferred*. Raw transcripts are in `evidence/`; every number in this report comes from a file in
that directory.

---

## 0. Verdict

**Yes — the agent lane runs in a container whose only read-write mount is the session workspace,
and the repository, its git objects, the answer stores and the provider key are simply not in that
filesystem view.** Measured end to end: the CLI starts, completes real `deepseek-flash` turns
through the metering proxy, is metered (`CEq`, 4 rows, 2 634 `CEq` for the whole round), and writes
a file the host can execute. The container's entire visible filesystem is 4 918 files; none of the
21 experimenter-only paths I named can be opened; its only reachable peer is the metering proxy.

**Cost is negligible in latency and disk** (image already local, 0.79 s from `compose up` to a
listening metered endpoint, 0.03 s per `docker exec`).

**One blocker, measured, and it is not about containment: codex's own `read-only` and
`workspace-write` sandboxes cannot run inside a container at all.** They are bubblewrap-based and
need namespaces that Docker denies; under the strict container posture the CLI *panics*
(`bubblewrap is unavailable`), and even with `bwrap` bind-mounted it fails at every posture short
of `--privileged`. T1's mode config gives two of its three roles `sandbox: read-only`. So the
container-as-boundary is only usable if every role is granted `danger-full-access` — a **mode
config change, which is the user's pending decision and is not made here.** Under the strict
container posture I measured, `danger-full-access` is the exact posture the leak analysis flagged,
and here it is *safe*, because the boundary is outside the CLI instead of inside it.

**Second verdict, on the two shapes:** variant **C2** (`--network none` + a bind-mounted unix
socket) is strictly stronger than C1 (`--internal` network + dual-homed proxy) at identical cost,
and both are metered through the same `meter_proxy.py`. Its container has **no route at all** — the
route table comes back empty.

**Recommendation for this project's constraints: ship Mechanism A
(`a0/a1/epistemic-ns`) now, and treat C as the migration target.** Reasons, all measured, in §5.

---

## 1. What was built

```
a0/a1/epistemic-container/
  compose.yaml        C1's session shape (networks, metering proxy, agent container)
  registry.json       the meter's campaign registry: EC_C1_0001:8801, EC_C2_0001:8802
  codex/C1.config.toml, codex/C2.config.toml    per-session CODEX_HOME config
  run.sh              env | up | probe | call | tool | verify | down | all
  probe_inside.py     the in-container probe (runs inside the lane, stdlib only)
  sock_forward.py     C2's in-container TCP 127.0.0.1:8802 -> unix socket pump
  sock_relay.py       C2's host-side unix socket -> 127.0.0.1:8802 (reuses
                      a0.a1.topology.UnixRelay, imported not re-implemented)
  probe_bwrap.sh      is codex's OWN sandbox usable in a container? (no model spend)
  evidence/           every transcript this report cites
```

Nothing outside this directory was modified. `a0/meter/` is mounted **read-only** into the
metering container (its `ledger.jsonl` is written to a separate writable mount); `a0/a1/topology.py`
is imported by `sock_relay.py`, not edited. The mode config, the frozen suite, `references/**` and
the upstream runtimes were not touched.

### C1 — internal network, one dual-homed proxy

```
a0ec-egress (bridge, has uplink)        a0ec-internal (--internal, no default route)
        │                                        │
   a0ec-meter  ── dual-homed ────────────────────┘ 172.31.78.10
        │   a0/meter/meter_proxy.py, --allowlist api.deepseek.com,
        │   listen 0.0.0.0:8801/8802, ledger on the host bind mount
        │                                        │
   (uplink, TLS to api.deepseek.com)      a0ec-cli  172.31.78.2
                                          base_url = http://a0ec-meter:8801/v1
```

### C2 — no network at all

```
host:  sock_relay.py  /tmp/a0ec/run/c2.sock ──> 127.0.0.1:8802 (published meter port)
                     │ (a unix socket is a filesystem object)
a0ec-cli-c2  --network none   /run/a0ec ← bind mount of the run dir
   sock_forward.py  127.0.0.1:8802 ──> /run/a0ec/c2.sock
   base_url = http://127.0.0.1:8802/v1
```

Both containers carry `--cap-drop ALL --security-opt no-new-privileges` and run as uid 1000 (the
harness's uid, so nothing the agent writes into the workspace comes back root-owned).

---

## 2. Q1 — the image, and how the CLI gets in

### The image: `python:3.12-slim`, already local. Why that one

| candidate | verdict |
|---|---|
| **`python:3.12-slim`** (Debian 13 trixie, glibc 2.41) — **CHOSEN** | already in the local store, so **nothing was pulled**; glibc loader present; and it is the *same* image the project's own closure work used for the same job (`a0/notes/exit-closed/proxy-closure/REPORT.md` §1), so this is not a new dependency surface |
| `alpine:3.21` (12.2 MB) | rejected: musl. `codex` is a glibc-linked ELF (`/lib64/ld-linux-x86-64.so.2`); making it load would mean installing `gcompat`, i.e. a new package — the thing the assignment asks to avoid |
| `postgres:16`, `redis:8`, `temporalio/*` | present but wrong shape (multi-hundred-MB services with their own entrypoints) |
| a purpose-built image with the CLI installed | rejected: needs a network pull, duplicates 250 MB, and **forks the CLI away from the bytes the campaign actually runs** |

Reported size: **179 MB on disk / 177 220 457 bytes compressed-equivalent (169.0 MiB
uncompressed)**. Marginal cost of this mechanism on a host that already has the image: **zero**.

### How the CLI gets in: bind-mount, not install — and the trade-off stated

I bind-mount the host's `/usr/bin/codex` read-only (250 292 704 bytes) plus **one** shared object.

Measured (`evidence/00_environment.txt`): the binary has **11 `DT_NEEDED` entries**; the image
satisfies 10 of them; the only gap is

```
libonig.so.5 => not found
```

so the second mount is `/usr/lib/libonig.so.5.5.0 → /usr/lib/x86_64-linux-gnu/libonig.so.5:ro`
(host package `oniguruma 6.9.10`, 614 400 bytes). With that one object, `codex --version` returns
`codex-cli 0.155.1` inside the image.

*Trade-off.* Bind-mounting keeps the CLI's **byte identity** with the campaign (no drift, no
rebuild, no pull) and keeps the image free of the CLI entirely. The price is that the image's libc
and its shared libraries must stay ABI-compatible with the binary, and this mount list must track
`ldd` if the CLI is upgraded. That is a two-line list, and `run.sh env` re-derives it — installing
the CLI into the image would instead make the mount list disappear but silently create a second
version of the CLI that the campaign is not testing.

`/usr/lib/libonig.so.5` is itself a symlink to `libonig.so.5.5.0` on the host; I mount the **target
file** to avoid any question about how the daemon resolves the link.

---

## 3. Q2 — the session, the metered call, the ledger

Session shape (C1, and identical for C2 except the network): workspace bind-mounted **read-write**
at `/workspace`; session `CODEX_HOME` bind-mounted read-write at `/codex-home`; the CLI and its one
missing library read-only; the probe read-only; **the repo absent**; the network restricted to the
metering proxy. The codex provider config is the recipe from
`a0/notes/exit-closed/codex-0.155.1/REPORT.md` §7 with `base_url` pointed at the campaign's metered
listener instead of at DeepSeek, plus the meter's optional attribution header:

```toml
model = "deepseek-flash"
model_provider = "ds"
[model_providers.ds]
base_url = "http://a0ec-meter:8801/v1"
env_key  = "DS_KEY"
wire_api = "responses"
http_headers = { "X-A0-Meter-Token" = "a0ec-c1-6f2b41d9c8a34e70" }
```

The key was read from `~/gptapi.md` into `DS_KEY` **inside the same shell command that used it**,
handed over with the valueless `docker exec -e DS_KEY` form, and never printed, never written to a
file, and never placed in a container's persisted config.

### The rows (`evidence/41_ledger_final.jsonl`, re-derived by `a0/meter/verify_ledger.py`)

```
41_ledger_final.jsonl: 15 rows, 4 metered, 11 unmetered, ceq_total=2634
  EC_C1_0001/A_container_internal ceq=2257
  EC_C2_0001/A_container_netnone ceq=377

metered rows (each = one upstream `POST /v1/responses`; endpoint, usage triple, ceq):
  EC_C1_0001  call #1, the trivial turn            hit=7808 miss=817  completion=8   ceq=1005
  EC_C2_0001  call #1, the trivial turn            hit=8448 miss=177  completion=8   ceq=377
  EC_C1_0001  call #2, tool loop, model turn 1     hit=8448 miss=204  completion=92  ceq=740
  EC_C1_0001  call #2, tool loop, model turn 2     hit=8576 miss=221  completion=30  ceq=512
```

**Total spend for this round: 2 634 `CEq`** — cents, and inside the assignment's ceiling. The
arithmetic re-derives by hand (`miss + (hit*2)//100 + 4*completion`): 817+156+32 = 1005 ✓,
177+168+32 = 377 ✓, 204+168+368 = 740 ✓, 221+171+120 = 512 ✓.

Note the row count is **not** the call count: three `codex exec` invocations produced four rows,
because the tool loop is two model turns (tool call, then final answer) and a metering boundary that
collapsed them into one number would be losing a fact. This is the ledger behaving correctly.

The 11 `unmetered` rows are **by design and are themselves evidence**: 10 are my probe's
`GET /v1/models` calls, correctly refused `403 attribution_token_mismatch` (the probe deliberately
sends no token) or booked `unmetered` with a named reason when they did reach the upstream; and the
rest are the `host_header_not_allowlisted` / `path_not_routed` refusals of §5.4. None is an estimate
and none is a zero.

The session really works: `A0EC-C1-OK`, `A0EC-C2-OK` (both exit 0), and a **tool loop** —

```
$ docker exec -e DS_KEY -w /workspace a0ec-cli codex exec --skip-git-repo-check \
    --sandbox danger-full-access "Create a file named hello_a0ec.py … then run it with python3"
… exit=0
== verified from the HOST, not from the transcript:
-rw-r--r-- 1 ebt ebt  22 Sep 23 11:18 hello_a0ec.py
  hello_a0ec.py content: print('A0EC_TOOL_OK')
  host-side execution:   A0EC_TOOL_OK
```

The agent wrote into its workspace with its **shell tool**, not `apply_patch` — the transcript
records the command it ran, `evidence/32_call_C1_toolloop.txt:19`:

```
/usr/bin/bash -lc "printf \"print('A0EC_TOOL_OK')\n\" > hello_a0ec.py && python3 hello_a0ec.py" in /workspace
```

so both halves of the container that matter were exercised: the CLI's shell tool wrote a file into
the read-write mount, and **the image's own `python3 3.12.14`** executed it. The file comes back
owned by `ebt`, not root.

Startup cost (`evidence/timings.txt`):

```
compose_up_seconds=0.22
compose_up_to_meter_ready_seconds=0.79
first_docker_exec_codex_version_seconds=0.03
image_pull_seconds=0.00            # already local
call_C1_seconds=1.24   call_C2_seconds=1.27
```

---

## 4. Q3 — what is absent, what is unreachable (with the controls that make it a measurement)

Full report: `evidence/20_probe_C1.json`, `evidence/21_probe_C2.json`.

### 4.1 The controls, first

An "absent" result is worthless without a positive control on the same code path. Two were planted
and both fire:

```
_walk_control_ok: true    walk found /workspace/a0ec-canary-visible.txt and did NOT find
                          $RUN_DIR/host-only/a0ec-canary-host-only.txt (same body, a path
                          that is not mounted)
_read_control_ok: true    open(/workspace/a0ec-canary-visible.txt) returns the body
```

So the search walks 4 918 files (C1) / 4 923 (C2) across the whole visible filesystem, and the read
path works.

### 4.2 The filesystem

```
_opened_count: 0 / 21      every named experimenter-only path failed to open
_leak_basenames_found: []  no targets.json / commitments.json / fs_policy.json / G_eval_0001.json
_leak_dirs_found: []       no .git, no witnesses/, no references/ anywhere in the container
```

and the 21 named targets, `open()`ed (not merely `stat`ed):

```
/home/ebt/gptapi.md                    FileNotFoundError
/home/ebt                              FileNotFoundError
/home/ebt/rsi-dev                      FileNotFoundError
/home/ebt/rsi-dev/.git                 FileNotFoundError
…/references/targets.json              FileNotFoundError
…/references/witnesses/commitments.json FileNotFoundError
…/references/witnesses/fs_policy.json  FileNotFoundError
…/suite/eval/G_eval_0001.json          FileNotFoundError
…/suite/eval, …/suite, …/a1/kapso_t1   FileNotFoundError
…/a0/meter/meter_proxy.py              FileNotFoundError
/home/ebt/kapso_ck, /tmp/eve, /tmp/a0ec FileNotFoundError
/home/ebt/.codex/{auth.json,config.toml} FileNotFoundError
/root/.codex                           PermissionError (the IMAGE's own /root, uid 0700)
/var/run/docker.sock, /run/docker.sock, /run/containerd/containerd.sock  FileNotFoundError
```

The git route the briefing named is closed for a different reason than a file permission: the
object `9020082d8329036e244b6882a5e9ede2ad1d1b1b` (a 332-byte blob, **packed**, resolved on the
host) lives inside `/home/ebt/rsi-dev/.git`, and that directory does not exist in the container.
There is no `git` binary either (§4.5), so both ends of that attack surface are gone.

The mount table, verbatim (`evidence/23_mountinfo_binds.txt`) — **five** bind mounts and nothing
else:

```
/a0ec/codex-home/c1           /codex-home                              rw
/a0ec/ws                      /workspace                               rw
/home/ebt/rsi-dev/a0/a1/epistemic-container/probe_inside.py
                              /opt/a0ec/probe_inside.py                ro
/usr/lib/libonig.so.5.5.0     /usr/lib/x86_64-linux-gnu/libonig.so.5  ro
/usr/bin/codex                /usr/local/bin/codex                     ro
```

*Residual, stated rather than implied:* `/proc/self/mountinfo` is readable inside the lane, so a
curious agent learns the **source path strings** of these mounts — including that a directory
`/home/ebt/rsi-dev/a0/a1/epistemic-container/` exists on some host. It learns a string, not a byte
of the repository. If even that is unwanted, the probe and the CLI would have to be baked into the
image so the mount sources are not host paths.

### 4.3 The `/proc` escape route

```
/proc/1/cmdline                 "sleep infinity"        (the container's own init)
/proc/1/root listing            .dockerenv bin boot codex-home dev etc home lib lib64 …
/proc/1/root/home               []                      (empty — the host's /home is not there)
/proc/1/root/workspace          README.txt, a0ec-canary-visible.txt, probe_C1.json
proc1_environ_has_DS_KEY        false
```

PID 1 is the container's own init, so `/proc/1/root` lands back inside the same container. No key
material is in any process environment until a call is made, and then only in that one `exec`ed
process.

### 4.4 The network, C1

```
dns  a0ec-meter            resolved:172.31.78.10
dns  api.deepseek.com      BLOCKED:gaierror
dns  example.com           BLOCKED:gaierror

egress literals (bare IPs, so DNS cannot mask the result):
  123.148.116.184:443  BLOCKED:OSError     <- this IS api.deepseek.com's address
  1.1.1.1:443          BLOCKED:OSError
  8.8.8.8:53           BLOCKED:OSError
  140.82.121.4:443     BLOCKED:OSError

lateral (networks the lane is not on):
  172.17.0.1:443  BLOCKED:OSError     172.17.0.1:5432  BLOCKED:OSError
  172.17.0.2:5432 BLOCKED:OSError     127.0.0.1:5433   BLOCKED:ConnectionRefusedError
  127.0.0.1:2375  BLOCKED:ConnectionRefusedError

the pre-existing container's real address, probed from inside (evidence/22_lateral_postgres.txt):
  172.19.0.2:5432  BLOCKED:OSError [Errno 101] Network is unreachable   (adapdc-catalog-postgres-1)
  172.19.0.1:443   BLOCKED:OSError [Errno 101] Network is unreachable

sweep of 172.31.78.0/24 x {80,443,2375,5432,5433,6379,8801,8802}, 2 037 connections:
  listeners_found: only 172.31.78.10:8801 and 172.31.78.10:8802   <- the metering proxy, both campaigns

positive control on the same code path:  a0ec-meter:8801  REACHED
```

`/proc/net/route` for C1 has **one** route — `172.31.78.0/24` on-link — and **no default route**.
For C2 the route table is **empty** and its only listener is the in-container forwarder.

The pre-existing container was untouched, and that is measured, not asserted
(`evidence/50_verify_host.txt`):

```
non-a0ec containers, before vs after:  IDENTICAL to the before fingerprint
adapdc-catalog-postgres-1: id=ec2bbaf1… running=true restarts=0
  before: id=ec2bbaf1… running=true started=2026-09-22T01:04:21.916233832Z restarts=0
  after:  id=ec2bbaf1… running=true started=2026-09-22T01:04:21.916233832Z restarts=0
```

Same container id, same start time, zero restarts, and the six pre-existing containers and four
networks are unchanged. Teardown (`evidence/60_down.txt`) leaves exactly that set.

### 4.5 What the CLI's toolchain does *not* have

`evidence/24_toolchain.txt` — inside the container vs on the host:

| tool | in the container | on the host (what Mechanism A inherits) |
|---|---|---|
| `python3` | 3.12.14 | 3.14.7 |
| `git`, `node`, `npm`, `gcc`, `make`, `jq`, `patch`, `rg`, `curl`, `wget`, `ssh`, `docker` | **all ABSENT** | all present |

The CLI itself works (it is one static-ish binary), and `apply_patch` is built in. But an agent
that wants to `git diff` its work, or run a build, or use `rg`, gets nothing — and the image's
python is not the host's python. For a lane whose job is to write a Python candidate that the
*host* will later evaluate, that is a real fidelity gap to price in.

---

## 5. Q4 — cost, fragility, how the harness drives it, and the metering/closure stories

### 5.1 Cost

| item | measured |
|---|---|
| image | 179 MB reported / 169.0 MiB uncompressed, **already local** — 0 pulled, 0 built |
| CLI in the image | none — bind-mounted (250 MB stays on the host, one copy, byte-identical) |
| extra disk for a session | the workspace + `CODEX_HOME` scratch (a few MB) |
| `compose up` → containers started | **0.22 s** |
| `compose up` → metered endpoint listening | **0.79 s** |
| first `docker exec codex --version` | **0.03 s** |
| one trivial model call, wall | **1.24 s / 1.27 s** |
| round's model spend | **2 634 `CEq`** |

Against ~30-minute sessions and tens of campaigns, a sub-second container start and one container
per campaign is not a constraint. The real cost is not time or disk — it is §5.3.

### 5.2 How the campaign harness would drive it

**`docker exec`.** `run.sh` is the prototype: a long-lived `sleep infinity` container per session,
and every phase — probe, `codex exec`, tool loop — is a `docker exec` from the host, with
`-e DS_KEY` passed per call so the credential exists only for that process. The container's exit
code is the CLI's exit code, stdout/stderr stream back unchanged, and the session's `CODEX_HOME`
survives between calls (so `codex exec resume` has somewhere to resume from — *not tested here*).

**A mounted docker socket is rejected.** Mounting `/var/run/docker.sock` would give the agent
root-equivalent control of the host — it could start a privileged container and read anything —
which would dissolve the boundary this mechanism exists to create. Measured present: neither
container has `/var/run/docker.sock` (§4.2), and neither has a `docker` client. The harness must
stay outside the container; that is a feature.

### 5.3 Fragility — the CLI needs things the container does not have

**Blocking, and measured.** codex 0.155.1 implements `read-only` and `workspace-write` with
bubblewrap (`linux-sandbox/src/launcher.rs`). In the strict container posture the CLI does not
degrade, it **panics**:

```
thread 'main' (450) panicked at linux-sandbox/src/launcher.rs:51:13:
bubblewrap is unavailable: no system bwrap was found on PATH and no bundled
codex-resources/bwrap binary was found next to the Codex executable
```

`evidence/26_sandbox_postures.txt` — `codex sandbox` is model-free, so this costs nothing:

| `sandbox_mode` | container, `cap_drop ALL` | container, best relaxation | `unshare -rmpf` (Mechanism A's shape) |
|---|---|---|---|
| `danger-full-access` | **works** (socket OK, workspace writable) | works | works |
| `workspace-write` | **panic: bubblewrap is unavailable** | `bwrap: Can't mount proc on /proc: Operation not permitted` | works |
| `read-only` | **panic: bubblewrap is unavailable** | same | works (socket() → `PermissionError`) |

`evidence/28_bwrap.txt` walks the whole ladder, with a `--privileged` positive control proving the
failure is the container and not `bwrap`:

```
A. container default caps                      bwrap: No permissions to create a new namespace …
B. cap_drop ALL + no-new-privileges  (ours)    bwrap: No permissions to create a new namespace …
C. cap_drop ALL + seccomp=unconfined           bwrap: setting up uid map: Operation not permitted
D. cap_drop ALL + seccomp=unconfined, no --unshare-all
                                               bwrap: setting up uid map: Operation not permitted
E. --cap-add SYS_ADMIN                         bwrap: pivot_root: Operation not permitted
F. --cap-add SYS_ADMIN + seccomp=unconfined    INSIDE_BWRAP_OK   <- first posture that works
G. POSITIVE CONTROL --privileged               INSIDE_BWRAP_OK
H. codex read-only under posture F             bwrap: Can't mount proc on /proc: Operation not permitted
I. POSITIVE CONTROL codex read-only --privileged
                                               PermissionError  <- the posture applied
under unshare -rmpf --mount-proc               INSIDE_BWRAP_OK; codex read-only → PermissionError
```

So the honest statement is: **you can have a strict container, or you can have the CLI's own
per-command sandbox, but not both** — recovering the latter needs `CAP_SYS_ADMIN` *and*
`seccomp=unconfined`, and even that fails, leaving `--privileged`. Since the whole point of C is that
the boundary is the container, the right answer is to keep the container strict and stop asking the
CLI to sandbox itself. But T1's frozen mode config says `sandbox: read-only` for
`feedback_generator` and `evaluation_maintainer`; under C those two roles **crash**. Adopting C
therefore requires a mode-config revision — **reported, not applied** (see §7).

**Non-blocking, priced in.** auth state: none is needed (the CLI authenticates with the injected
key), but the host's `~/.codex` is deliberately *not* mounted, so no session/plugin/AGENTS memory
carries over — the harness supplies `config.toml` and the session dir. Device access: none needed.
Toolchain: §4.5.

### 5.4 Does this complicate the metering story? No — measured in both directions

The container's egress still terminates on `a0/meter/meter_proxy.py`, unmodified, and the budget
authority is intact. The three ways an agent could try to go around it were probed from inside:

```
going direct:            123.148.116.184:443 (= api.deepseek.com)  BLOCKED:OSError
asking the meter for a non-allowlisted destination (evidence/25_…):
  Host: example.com      -> 403  reason=host_header_not_allowlisted:example.com      [ledgered]
  Host: api.openai.com   -> 403  reason=host_header_not_allowlisted:api.openai.com   [ledgered]
asking the meter for the ledger itself (evidence/27_…):
  /var/lib/a0ec/ledger.jsonl  -> 403 reason=path_not_routed:…                        [ledgered]
  /../../var/lib/a0ec/ledger.jsonl -> 403 reason=path_not_routed:…                   [ledgered]
```

Every refusal lands in the ledger **against the right campaign**, which is the property that makes
`CEq` a number the runtime could not have lied about. And the metered calls themselves are ordinary
rows: endpoint `https://api.deepseek.com/v1/responses`, `model_reported: deepseek-flash`,
`stream: true`, a full usage triple, and a `ceq` that an independent program
(`a0/meter/verify_ledger.py`) re-derives. Streaming through the meter's terminal-event hold
survived intact — the CLI saw complete Responses streams.

One honest note: a container adds a **new egress-bearing object** to the topology (the metering
container, which is dual-homed and therefore has real uplink). It is not an open relay — the
allowlist and the routed-path check both bind from inside the lane — but it is a second thing whose
configuration matters, and the closure claim for it rests on `a0/meter/`'s own evidence, not on
anything I measured here.

### 5.5 Does this complicate the closure story? It changes what "closed" means

C1 is the established `--internal` + dual-homed-proxy shape, and its closure is probed, not
asserted: no default route, no external DNS, four bare-IP negatives blocked, 2 037-connection sweep
finding only the meter, and the pre-existing containers' addresses unreachable with `ENETUNREACH`.

**C2 is strictly stronger and costs nothing extra**: `--network none`, an empty route table, no
resolvable names at all, and a single unix socket as the container's only exit. The socket is a
filesystem object, so its *identity* is the campaign's identity — there is no hostname or port a
client could vary to reach a different campaign. This is the same device `a0/a1/topology.py` already
uses for the `unshare -rn` arm, and `sock_relay.py` imports `UnixRelay` rather than reimplementing
it. If C is adopted, I would adopt C2's socket shape and keep C1 only as the fallback for a host
where a published loopback port is not acceptable.

---

## 6. Q5 — comparison with Mechanism A, and the recommendation

Mechanism A is `a0/a1/epistemic-ns/` (another worker's; **read from source**, and one measurement
I made myself, labelled). Its shape: `unshare -rmnpf --mount-proc`, `mount --make-rprivate /`, a
fresh tmpfs over each of `/home`, `/tmp`, `/var/tmp`, `/run/user` (the candidate lane's `_hide`,
imported whole), the session's allow-list bound back, a TCP→unix-socket meter forwarder, then the
CLI — with a fail-closed self-check written to a receipt before the CLI runs.

| dimension | **C — container** | **A — namespace** |
|---|---|---|
| default policy | **deny**: the agent's view is an image + 5 mounts; everything else does not exist | **allow-minus-a-list**: hides 4 named roots; `/usr`, `/opt`, `/etc`, `/dev`, `/srv`, `/mnt` stay shared with the host |
| what that means for a new secret store | a path under a *new* location (say `/opt/a0-answers`) is invisible **by construction** | a path outside the 4 roots would be **visible** — the property is a policy about a list |
| the CLI's own sandbox | **broken** (measured, §5.3) | **works** (measured: under `unshare -rmpf`, codex read-only → `PermissionError`) |
| toolchain fidelity | must be reproduced in the image: `git`, `node`, `gcc`, `jq`, `curl` all absent; `python3` is 3.12 vs the host's 3.14 | inherited exactly — the harness's own interpreter and virtualenvs |
| enforcement point | the kernel/docker, from outside; **the agent cannot opt out** | the launch site; a session started without `prefix()` is unconstrained (A's own docstring says so) |
| added latency | 0.79 s to a listening metered endpoint, 0.03 s per exec | none (namespace syscalls) |
| added disk | 0 (image already local); 169 MiB uncompressed if it were not | 0 |
| root needed | no (docker group) | no (`unshare -r`) |
| meter path | C1 internal net + dual-homed proxy, or C2 unix socket | unix socket (same device as C2) |
| failure modes seen | missing `libonig`; missing `bwrap`; `docker compose` refuses a network-scoped alias on the default bridge | none new; the hidden-root check was already repaired once (`a0/a1/candidate_sandbox.py` §_hide) |
| config change required | **yes** — every T1 role must be `danger-full-access`, or two roles panic | no |

### Recommendation

**For this project as it stands — no root, docker available, no GPU in containers, ~30-minute
sessions, tens of campaigns — I would ship Mechanism A now, and migrate to C when the mode-config
decision is made.**

1. **A closes the measured leak with zero new failure modes.** The facts the review named —
   `references/targets.json`, the held-out graphs, the commitments, `~/gptapi.md` — all live under
   `/home`, which A replaces with an empty tmpfs. It needs no image, no CLI rebuild, no toolchain
   reproduction, no container lifecycle, and it adds no latency.
2. **C is the structurally stronger guarantee, and that is not a small thing.** Its filesystem is
   default-deny: "the answer store is absent" stops being a statement about a list of hidden roots
   and becomes a statement about what was mounted. If the project's answer, R/OPT/U and key stores
   ever move outside `/home` — or if a future reviewer wants a bound that does not depend on
   remembering them — C is the mechanism that gives it.
3. **But C cannot be adopted today without a config change that is the user's to make.** Under C the
   CLI's `read-only`/`workspace-write` sandbox panics, so T1's two `read-only` roles cannot run.
   Relaxing the container to `CAP_SYS_ADMIN + seccomp=unconfined` to recover them is a bad trade
   (it hands the agent near-root in the container, which is what the container was protecting), so
   the honest fix is `danger-full-access` for all three roles *with the container as the boundary* —
   which is also the intellectually consistent position, since the leak proved the CLI's own
   `workspace-write` was never a read jail. Making that change simultaneously adopts C's strongest
   argument.
4. **If C is adopted, adopt the C2 shape** (`--network none` + bind-mounted unix socket): strictly
   stronger closure than C1, identical cost, and reusing `a0.a1.topology.UnixRelay` rather than a new
   component.
5. **If both are wanted, they compose.** A could be run *inside* the container (it needs `unshare`,
   which `cap_drop ALL` denies — so no, that specific composition fails; what composes is C's
   container plus the *candidate* lane's `candidate_sandbox.py` on the host, which is already the
   project's shape). *This item is inference from the measured capability error in §5.3, not a
   measurement.*

---

## 7. Proposed diffs — reported, not applied

1. **`a0/a1/kapso_t1/config/mode.maxcut.yaml`, `feedback_generator` and `evaluation_maintainer`:
   `sandbox: "read-only"` → `"danger-full-access"`.** Required only if Mechanism C is adopted; the
   reason is §5.3. Not applied: the mode config is frozen and any contract revision is the user's
   pending decision.
2. **Optional harness seam**: `run.sh`'s phases are the prototype of a `session_container` driver —
   `up` (once per campaign), `docker exec` (once per CLI invocation), `down`. Not implemented as
   library code here, because nothing in the contract names it yet.

---

## 8. What I could not verify, and the residuals

* **A ~30-minute session was not run.** The longest thing I ran is a few seconds per call. Container
  lifetime, idleness, the `CODEX_HOME` sqlite files' growth and any long-run drift are *inferred*
  from codex's behaviour on the host, not measured here.
* **`codex exec resume` was not tested inside the container.** The session directory survives across
  `docker exec` calls, so it should work; `a0/notes/exit-closed/codex-0.155.1/REPORT.md` §5.4 already
  records that even on the host the prior-turn replay was not verified.
* **The TUI (`codex` interactive) was not tested** — only `codex exec`. A PTY-driven lane would need
  `docker exec -it`, which I did not exercise.
* **`/proc/self/mountinfo` reveals the bind-mount source path strings** (§4.2). Cosmetic; the
  mitigation (baking the CLI and probe into the image) costs the byte-identity property that made
  the bind mount attractive.
* **The metering container is a trusted component and a new dual-homed object.** I probed its
  refusals from inside the lane (§5.4), but its own correctness rests on `a0/meter/`'s evidence.
* **The container is not a VM.** It shares the kernel; a kernel exploit escapes both C and A. What C
  establishes specifically is that *no file outside the mount list exists in the view* — a stronger
  and simpler property than A's, but not a stronger one against a kernel bug.
* **`--cap-drop ALL` was chosen and kept.** With it, `danger-full-access` worked; the CLI's own
  sandbox did not (§5.3). I did not test whether some subset of capabilities gives the CLI's sandbox
  without `--privileged` beyond the ladder in `evidence/28_bwrap.txt`.
* **`/tmp/a0ec` remains on the host** after teardown (the run directory). It contains the probe
  output, the session `CODEX_HOME` and the ledger; it holds no key material (the key was only ever
  in `DS_KEY` for the duration of one `docker exec`). `run.sh down` removes the containers and
  networks, not the run directory, on purpose — the ledger is evidence.

---

## 9. Rerun it

```bash
cd /home/ebt/rsi-dev
DS_KEY=$(awk -F: '/^deepseek:/{sub(/^deepseek:[ ]*/,""); print; exit}' ~/gptapi.md) \
  a0/a1/epistemic-container/run.sh all          # ~2 634 CEq, ≈0.3 US cents
a0/a1/epistemic-container/run.sh down           # and: ./probe_bwrap.sh for the no-spend finding
```

`run.sh all` = `env up probe call tool verify`. It pulls nothing (every image is already local), it
creates only `a0ec-*` containers and networks, and `verify` re-checks that the pre-existing
containers are byte-identical to their before-fingerprint. `probe_bwrap.sh` needs no key and makes
no model call, so the §5.3 finding can be re-established for free.
