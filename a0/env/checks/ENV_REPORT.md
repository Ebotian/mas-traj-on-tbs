# ENV_REPORT.md — A0 environment-readiness audit

Auditor: environment-readiness subagent. Audit window: **2026-09-20 15:44–15:56 (+08:00)**.
Host `Nico-arch-home`, Arch Linux, kernel 7.2.4-arch1-2, user `ebt` (uid 1000, member of `docker`).
All results below are **verified by execution** unless a row says otherwise.

Scope note: this audit wrote only inside `/home/ebt/rsi-dev/a0/env/checks/`. The upstream
projects (`/home/ebt/kapso_ck/kapso`, `/tmp/eve`, `/tmp/lor`) were read-only inputs.

---

## 1. Verdict table

| # | Prerequisite | Verdict | One-line basis |
|---|---|---|---|
| 0 | Toolchain versions match protocol §4.0 | **PASS** | all 7 claimed versions reproduced exactly |
| 1a | `codex` CLI installed | **PASS** | `codex --version` → `codex-cli 0.154.0` |
| 1b | `codex` CLI logged in **and usable** | **FAIL** | creds resolve, but its provider endpoint is dead: `codex exec` cannot complete a call |
| 1c | `claude` CLI installed | **PASS** | `claude --version` → `2.1.260 (Claude Code)` |
| 1d | `claude` logged in to Anthropic | **FAIL** | `claude doctor`: "Not signed in to claude.ai", "subscription auth not active" |
| 1e | `claude` can complete a model call | **UNKNOWN** | only a billed call could settle it; deliberately not run (§4) |
| 2a | `uv` can install interpreters 3.11 / 3.12 | **PASS** | `uv python install` → cpython 3.11.15, 3.12.11 |
| 2b | KAPSO dependency resolution (documented path) | **PASS** | `pip install -e .` deps resolve on 3.11, 3.12 **and** 3.14 |
| 2c | KAPSO root `requirements.txt` | **FAIL** | unsatisfiable on both 3.11 and 3.12 (stale aggregate file) |
| 2d | EvE dependency resolution (locked) | **PASS** | 95 locked packages install on 3.11, 3.12, 3.14 |
| 2e | Protocol risk "3.14.7 lacks wheels" | **REFUTED** | every dependency of both projects installed on 3.14.7, 0 source builds |
| 3 | Container infra: fresh Postgres **and** Redis | **PASS** | both started, accepted connections, then removed |
| 4a | `docker --internal` blocks egress, keeps siblings | **PASS** | egress blocked **and** sibling reachable (`local=ok`) |
| 4b | `docker --network none` blocks egress | **PASS** | dns/tcp/https all fail |
| 4c | `unshare -rn` blocks egress (no root) | **PASS** | same command: succeeds on host, `URLError` inside |
| 4d | Firewall control (iptables / nftables) | **BLOCKED** | no root; both tools return "Permission denied" |
| 4e | `unshare -n` without userns | **FAIL** | `unshare failed: Operation not permitted` |
| 5 | Resource headroom for PG + Redis + runtimes | **PASS** | 12 threads, 19 GiB available RAM, 137 GB free disk |
| 6 | Loreley clone pinned at `4c375920` | **BLOCKED** | `a0/env/upstream/` is empty; no clone ever ran |

**Hard blocker that stops A0 as specified:** row **1b**. KAPSO needs `codex` *and* `claude`;
EvE needs `codex`. `codex` cannot currently complete a single model call on this machine.

---

## 2. Scope split — verified by execution vs. reported by others

**Verified by execution in this audit** (every row of the table above, plus everything in
§3–§7). Raw logs are in `logs/`.

**Reported by others, unverified by this audit:**

| Claim | Status |
|---|---|
| KAPSO `/home/ebt/kapso_ck/kapso` == audit snapshot | HEAD `7d99b15` + full SHA confirmed by `git log`; *byte-identity with the snapshot not re-verified* |
| EvE `/tmp/eve` == audit snapshot | HEAD `979065f` confirmed; *byte-identity not re-verified* |
| `/tmp/lor` is not a git checkout | **re-verified** — no `.git`, `_version.py` reads `importlib.metadata`. Protocol claim CONFIRMED |
| `/tmp/eve/eve/` redundant copy is removable | *not inspected by this audit* — no deletion performed |
| Loreley clone is "being fetched into `a0/env/upstream/loreley`" | **FALSE at audit time** — directory empty, no `git clone` process running |
| Redis not running on host | **re-verified** — no listener on 6379, no redis container, `redis-cli` absent |
| `adapdc-catalog-postgres-1` is unrelated and running | **re-verified** — `postgres:16`, Up (healthy), `127.0.0.1:5433->5432`, compose project `adapdc`, network `adapdc_temporal-network` |

---

## 3. Check 1 — CLI login state

### 3.1 `codex` — FAIL (installed and credentialed, but unusable)

Evidence chain, least-invasive first:

```console
$ codex --version
codex-cli 0.154.0

$ codex login status
Logged in using an API key - ***          # exit 0

$ codex doctor --json        # redacted report; excerpt
/checks/auth.credentials/status  = 'ok'
/checks/auth.credentials/summary = 'auth is configured'
/checks/auth.credentials/details/stored auth mode = 'api_key'
/checks/network.provider_reachability/status = 'warning'
/checks/network.provider_reachability/details/custom API inference URL
    = 'http://127.0.0.1:15722/v1/<redacted> reachable (HTTP 502)'
```

`~/.codex/config.toml` (read with secret-shaped values filtered; no credential file opened):

```toml
model_provider = custom
model = gpt-5.6-sol
[model_providers.custom]
name = zjapi
wire_api = responses
requires_openai_auth = true
base_url = http://127.0.0.1:15722/v1
```

So `codex` is pointed at a **local relay on port 15722**. That port has no listener:

```console
$ ss -ltn | grep 15722
(no output)

$ curl -s -o /dev/null -w '%{http_code}' --noproxy '*' http://127.0.0.1:15722/v1/models
000                       # connection refused
$ curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:15722/v1/models
502                       # the host's mihomo proxy answering for a dead upstream
```

Final end-to-end attempt (a *failing* call, so nothing was billed):

```console
$ timeout 90 codex exec --sandbox read-only --skip-git-repo-check 'Reply with exactly: OK'
OpenAI Codex v0.154.0
model: gpt-5.6-sol
provider: custom
sandbox: read-only
ERROR: Reconnecting... 1/5
ERROR: Reconnecting... 2/5
ERROR: Reconnecting... 3/5
ERROR: Reconnecting... 4/5
exit 124                                  # timed out, no completion
```

**Verdict:** credentials are configured and the CLI considers itself logged in, but the
configured provider endpoint does not exist. A bare "auth is configured" would have been a
false green here. **`codex` is not usable**, and this is not a permissions problem that a
re-login fixes — it is a missing local relay.

**Implication:** EvE requires `codex` → EvE is blocked. KAPSO requires `codex` *and* `claude`;
its codex lane is blocked. This is the single most important finding in this report.

### 3.2 `claude` — installed, credential artifact present, Anthropic login FAIL, call UNKNOWN

```console
$ claude --version
2.1.260 (Claude Code)

$ claude auth status
{
  "loggedIn": true,
  "authMethod": "oauth_token",
  "apiProvider": "firstParty",
  ...
}
```

That alone would be a false green. `claude doctor` contradicts it:

```console
$ claude doctor
Config install method: unknown
Managed settings (remote): not fetched — not available with a custom ANTHROPIC_BASE_URL
...
- Not connected to the Anthropic API (api.anthropic.com)
- Not signed in to claude.ai
- claude.ai subscription auth not active
- Sign-in is missing the user:profile scope
```

`~/.claude/settings.json` (secret-shaped values redacted) explains the split:

```json
env.ANTHROPIC_BASE_URL        = https://api.deepseek.com/anthropic
env.ANTHROPIC_AUTH_TOKEN      = <redacted len=35>
env.ANTHROPIC_MODEL           = deepseek-v4.1-flash-expires-on-0910
env.ANTHROPIC_SMALL_FAST_MODEL = deepseek-v4.1-flash-expires-on-0910
model                         = deepseek-v4.1-flash-expires-on-0910
```

The backend endpoint itself is alive:

```console
$ curl -s -o /dev/null -w '%{http_code}' -X POST \
    https://api.deepseek.com/anthropic/v1/messages -H 'content-type: application/json' -d '{}'
401                       # reachable, auth enforced
```

**Verdict:** `claude` is installed and carries a bearer token for a **third-party relay**
(DeepSeek), not an Anthropic login. It is **not logged in to Anthropic**. Whether the lane can
actually produce completions is **UNKNOWN**.

Two risk signals worth flagging to the adapter authors: the configured model id is
`deepseek-v4.1-flash-expires-on-0910`, an expiry-labelled model **10 days past its label date**;
and `user:profile` scope is reported missing.

**Smallest safe confirming command** (deliberately not run — it would be a billed model call):

```bash
cd /tmp && timeout 120 claude -p 'Reply with exactly: OK'    # expect: OK
```

If that returns `OK`, mark 1e PASS; if it returns a 4xx/model-not-found, the model id has
expired and `~/.claude/settings.json` needs a new `ANTHROPIC_MODEL`.

### 3.3 Method note — what was and was not touched

`codex login status`, `codex doctor`, `claude auth status`, `claude doctor` all resolve
credentials *internally*; none of them print a secret. **No credential file was opened, printed,
copied or transmitted** — `~/.codex/auth.json` and the `ANTHROPIC_AUTH_TOKEN` value were never
read. The token lengths above come from the redaction filter, not from the values.

---

## 4. Check 2 — Interpreter pinning and dependency resolution

### 4.1 Interpreters

```console
$ uv --version
uv 0.12.13 (0ebbd9274 2026-09-10 x86_64-unknown-linux-gnu)

$ uv python install 3.11 3.12
Installed 2 versions in 35ms
 + cpython-3.11.15-linux-x86_64-gnu (python3.11)
 + cpython-3.12.11-linux-x86_64-gnu (python3.12)
```

The host has **no** system `python3.11` / `python3.12`; only `python3.14` (`/usr/bin/python3.14`,
which `python3` points at). `uv` supplies 3.11/3.12 on demand — no root needed in practice,
since the interpreters land in `~/.local/share/uv/python/`.

### 4.2 Result matrix (real installs, not just resolution)

| Case | Python | Result | Source builds |
|---|---|---|---|
| KAPSO `pyproject.toml` core deps | 3.11.15 | **PASS** (RC=0) | `antlr4-python3-runtime==4.9.3` (pure-Python sdist) |
| KAPSO `pyproject.toml` core deps | 3.12.11 | **PASS** (RC=0) | none |
| KAPSO `pyproject.toml` core deps | 3.14.7 | **PASS** (RC=0) | none |
| KAPSO `requirements.txt` | 3.11.15 | **FAIL** (RC=1) unsatisfiable | — |
| KAPSO `requirements.txt` | 3.12.11 | **FAIL** (RC=1) unsatisfiable | — |
| EvE `uv.lock` set (95 pkgs) | 3.11.15 | **PASS** (RC=0) | `antlr4-python3-runtime==4.9.3` (pure-Python sdist) |
| EvE `uv.lock` set (95 pkgs) | 3.12.11 | **PASS** (RC=0) | none |
| EvE `uv.lock` set | 3.14.7 | **PASS** (RC=0, dry-run) | none |

**Nothing is missing and nothing falls back to a real compile.** The only sdist build in the
entire matrix is `antlr4-python3-runtime==4.9.3`, a pure-Python package that simply has no wheel
on PyPI; no C/C++ toolchain is exercised.

### 4.3 KAPSO — the documented path passes, `requirements.txt` does not

```console
$ uv pip install --python <venv311> -r requirements.txt
      Because the current Python version (3.11.15) does not satisfy Python>=3.12 and
      openhands>=1.3.0 depends on Python>=3.12,<3.13, we can conclude that
      openhands>=1.3.0 cannot be used.
      ... you require openhands>=0.10.0, we can conclude that your requirements
      are unsatisfiable.
# RC=1
```

```console
$ uv pip install --python <venv312> -r requirements.txt
      ... because you require litellm==1.75.0, we can conclude that your
      requirements, aider-chat>=0.35.0, openhands>=1.0.0 are incompatible.
# RC=1
```

`requirements.txt` is a stale aggregate: it pins `litellm==1.75.0` while also pulling
`aider-chat>=0.35.0` (which excludes that litellm) and `openhands>=0.10.0` (which needs
Python ≥3.12). The repo's own `pyproject.toml` comments already say exactly this — the aider and
openhands adapters were moved to optional extras. KAPSO's README documents `pip install -e .`
(README.md:135), which resolves cleanly. **Not a blocker; do not build from
`requirements.txt`.**

### 4.4 EvE — locked set is clean

```console
$ cd /tmp/eve && uv export --frozen --no-emit-project --format requirements-txt -o <checks>/eve/locked-reqs.txt
$ uv pip install --python <venv311> -r <checks>/eve/locked-reqs.txt
Resolved 95 packages in 1.71s
   Building antlr4-python3-runtime==4.9.3
      Built antlr4-python3-runtime==4.9.3
Installed 95 packages in 24ms                                  # RC=0

$ cd /tmp/eve && uv sync --dry-run --frozen --python 3.11
Would use project environment at: .../eve/venv311
Would download 1 package
Would install 1 package
 + eve @ file:///tmp/eve                                      # RC=0
```

Note `uv export`/`uv sync --dry-run` were run with the venv redirected via
`UV_PROJECT_ENVIRONMENT`, so **`/tmp/eve` was not modified** (its `uv.lock` and
`.python-version` are untouched).

### 4.5 The protocol's 3.14 wheel risk does not materialise

Protocol §4.0 warns that python 3.14.7 "may lack prebuilt wheels". Measured: **both projects
resolve and install on 3.14.7 with zero source builds** (KAPSO core deps actually installed,
RC=0; EvE's 95-package locked set dry-ran clean, RC=0). Sample versions resolved on 3.14:
`tiktoken==0.14.0`, `weaviate-client==4.23.1`, `litellm`, `wandb==0.25.1`, `numpy`, `scipy`.

**Implication:** pinning to 3.11/3.12 is a cheap reproducibility precaution, not a hard
necessity. Caveat: EvE's own `.python-version` says `3.13` and its `requires-python` is
`>=3.11,<3.15`; KAPSO targets 3.10–3.12. Prefer **3.12** as the study-wide pin — it is inside
every project's declared range and needed no source build.

---

## 5. Check 3 — Container infrastructure for Loreley

Loreley's own `docker-compose.yml` pins `postgres:18` + `redis:8`, credentials `loreley`/`loreley`,
`POSTGRES_DB=loreley`, host ports `5432` and `6379`, and `env.example` declares:

```
DATABASE_URL=postgresql+psycopg://loreley:loreley@localhost:5432/loreley
TASKS_REDIS_URL=redis://127.0.0.1:6379/0
```

Both host ports were **free** (only `5433` is taken, by the unrelated container). Images
`postgres:18`, `redis:8`, `alpine:3.21` were pulled successfully (daemon egress works without the
host proxy).

### 5.1 Commands that were executed and verified

```bash
# Redis  (verified: redis-cli PING -> PONG; SET/GET round-trip OK; version 8.10.1)
docker run -d --name a0-loreley-redis \
  -p 127.0.0.1:6379:6379 redis:8 redis-server --appendonly yes

# Postgres (verified: 18.6, pg_isready "accepting connections" after 2s,
#           CREATE TABLE / INSERT / SELECT round-trip, host psql connect as loreley)
docker run -d --name a0-loreley-postgres \
  -e POSTGRES_USER=loreley -e POSTGRES_PASSWORD=loreley -e POSTGRES_DB=loreley \
  -p 127.0.0.1:5432:5432 postgres:18
```

Host-side verification of the real connection strings (note `redis-cli` is **not installed on the
host** — confirmed — so container-side `docker exec` was used, plus a raw socket PING from Python):

```console
$ docker exec a0-loreley-redis redis-cli ping
PONG
$ python3 -c "import socket;s=socket.socket();s.settimeout(3);s.connect(('127.0.0.1',6379));s.sendall(b'PING\r\n');print(s.recv(64))"
b'+PONG\r\n'
$ docker exec a0-loreley-postgres psql -U loreley -d loreley -c 'select version();'
 PostgreSQL 18.6 (Debian 18.6-1.pgdg13+2) ...
$ psql "postgresql://loreley:loreley@localhost:5432/loreley" -c 'select current_user, current_database();'
 loreley | loreley
```

### 5.2 Ready-to-use commands for the Loreley adapter

Two variants. **Use variant B if you can** — it is the one that also satisfies §4.3 closure
(see §6), because the internal network blocks external egress while keeping sibling containers
reachable by name (verified: `local=ok`).

**Variant A — published host ports (simplest; matches Loreley's defaults)**

```bash
docker run -d --name loreley-postgres \
  -e POSTGRES_USER=loreley -e POSTGRES_PASSWORD=loreley -e POSTGRES_DB=loreley \
  -p 127.0.0.1:5432:5432 postgres:18
docker run -d --name loreley-redis \
  -p 127.0.0.1:6379:6379 redis:8 redis-server --appendonly yes
# DATABASE_URL=postgresql+psycopg://loreley:loreley@localhost:5432/loreley
# TASKS_REDIS_URL=redis://127.0.0.1:6379/0
```

**Variant B — closed network (no egress, siblings by container name)**

```bash
docker network create --internal a0-egress-internal
docker run -d --name loreley-postgres --network a0-egress-internal \
  -e POSTGRES_USER=loreley -e POSTGRES_PASSWORD=loreley -e POSTGRES_DB=loreley postgres:18
docker run -d --name loreley-redis --network a0-egress-internal \
  redis:8 redis-server --appendonly yes
# then attach the runtime itself to the same network:
#   docker run --network a0-egress-internal ... <loreley-runtime-image>
# DATABASE_URL=postgresql+psycopg://loreley:loreley@loreley-postgres:5432/loreley
# TASKS_REDIS_URL=redis://loreley-redis:6379/0
```

### 5.3 Ports

Occupied at audit time (`ss -ltn`), avoid all of them:

| Port | Bind | Owner |
|---|---|---|
| 5433 | 127.0.0.1 | **`adapdc-catalog-postgres-1`** — pre-existing, do not touch/reuse |
| 7890 | * | mihomo proxy (`http_proxy`/`https_proxy` point here) |
| 7891 | * | mihomo proxy (UDP too) |
| 1053 | * | mihomo DNS (UDP too) |
| 9093 | 127.0.0.1 | unidentified host service |
| 44169 | 127.0.0.1 | unidentified host service |
| 39349 | 127.0.0.1 | VSCode/electron extension host |

Free and recommended: **5432** (Postgres), **6379** (Redis). Also beware: the *stopped* `adapdc`
stack declares `7233` (temporal) and `8080` (temporal UI) and will reclaim them if restarted by
another agent.

### 5.4 Cleanup

`a0-loreley-redis`, `a0-loreley-postgres` and the egress-test sibling were **stopped and
removed**. `a0-egress-internal` was removed too (`probe_egress.sh` recreates it on demand).
Post-cleanup `docker ps -a`, `docker network ls` and `ss -ltn` are byte-identical to the
pre-audit snapshot, and `adapdc-catalog-postgres-1` is still `Up (healthy)` on `5433`.
Images `postgres:18`, `redis:8`, `alpine:3.21` were **left in place** (they are needed by the
Loreley adapter and by `probe_egress.sh`; re-pulling postgres:18 costs ~600 MB).

---

## 6. Check 4 — Network egress and the ability to block it

### 6.1 What is available without root

| Mechanism | Available? | Evidence |
|---|---|---|
| `docker` (user in `docker` group) | yes | `docker version` → server 29.8.0 |
| `docker network create --internal` | **yes** | created and used |
| `unshare -rn` (user+net ns) | **yes** | `unshare -rn true` → exit 0 |
| `unshare -n` (net ns only) | **no** | `unshare: unshare failed: Operation not permitted` |
| `ip link add` (NET_ADMIN) | **no** | `RTNETLINK answers: Operation not permitted` |
| `iptables` | **no** | `Could not fetch rule set generation id: Permission denied (you must be root)` |
| `nft` | **no** | `netlink: Error: cache initialization failed: Operation not permitted` |
| sudo | **no** | `sudo: a password is required` |

So: **no firewall control at all**, and no privileged namespaces. The two working barriers are
both rootless: docker's `--internal`/`--network none`, and `unshare -rn`.

### 6.2 Measured results (`logs/egress_selftest.log`)

`./probe_egress.sh self-test` — every mechanism checked with a negative control (must be
blocked) *and* a positive control (must be reachable), so a mechanism that simply breaks
networking cannot masquerade as a pass:

```console
### mechanism=host   expectation=egress_open
EVIDENCE mechanism=host   rc=0 dns=ok tcp=ok tcpvia=example.com:443 https=ok local=n/a egress=OPEN
VERDICT host: CONFIRMED

### mechanism=docker-bridge expectation=egress_open
EVIDENCE mechanism=docker-bridge rc=0 dns=ok tcp=ok tcpvia=example.com:443 https=ok local=n/a egress=OPEN
VERDICT docker-bridge: CONFIRMED

### mechanism=docker-internal expectation=egress_blocked
EVIDENCE mechanism=docker-internal rc=0 dns=fail tcp=fail tcpvia=none https=fail local=ok egress=BLOCKED
VERDICT docker-internal: CONFIRMED        # local=ok proves the barrier is SELECTIVE

### mechanism=docker-none expectation=egress_blocked
EVIDENCE mechanism=docker-none rc=0 dns=fail tcp=fail tcpvia=none https=fail local=n/a egress=BLOCKED
VERDICT docker-none: CONFIRMED

### mechanism=unshare-rn expectation=egress_blocked
EVIDENCE mechanism=unshare-rn rc=0 dns=fail tcp=fail tcpvia=none https=fail local=n/a egress=BLOCKED
VERDICT unshare-rn: CONFIRMED

SELF-TEST: PASS -- every mechanism behaved as its label claims.
```

`docker-internal` reported **`local=ok`**: a real container on the internal network resolved and
connected to a *sibling* container by name. That is the key property — external egress dies,
intra-study channels survive.

A real connection attempt, not an import or a config read (`logs/egress_cmd_demo.log`): the same
runtime-style command reaches the network on the host and fails inside the barrier.

```console
$ ./probe_egress.sh check --mechanism host --cmd '<runtime urlopen probe>'
RUNTIME EGRESS SUCCEEDED: 200
EVIDENCE ... egress=OPEN    | VERDICT host: CONFIRMED

$ ./probe_egress.sh check --mechanism unshare-rn --cmd '<runtime urlopen probe>'
RUNTIME EGRESS FAILED: URLError
EVIDENCE ... egress=BLOCKED | VERDICT unshare-rn: CONFIRMED
```

### 6.3 Two sharp edges the KAPSO adapter must know about

Both working barriers also cut the process off from **host-localhost services**:

```console
# inside unshare -rn, the host's postgres on 127.0.0.1:5432 is unreachable
$ unshare -rn python3 -c "import socket;s=socket.socket();s.settimeout(4);s.connect(('127.0.0.1',5432))"
BLOCKED: OSError [Errno 101] Network is unreachable
$ PROBE_LOCAL_HOST=127.0.0.1 PROBE_LOCAL_PORT=5432 ./probe_egress.sh check --mechanism unshare-rn
EVIDENCE ... local=fail egress=BLOCKED
```

1. **A new netns has its own loopback.** `unshare -rn` + `ip link set lo up` works (verified), but
   that loopback is *the new namespace's*, not the host's. So wrapping a whole runtime in
   `unshare -rn` also severs any access to services on the host's `127.0.0.1` — including a local
   model relay, KAPSO's `gated_mcp` gate server, or a host Postgres.
2. **`docker --internal` has no route to the host either.** Local services must be *siblings on
   the same internal network* (proven to work), not published host ports.

**Consequence for KAPSO's unclosable Bash-side door (§4.3):** the only viable move without root is
to wrap **the lane's candidate-execution channel** in `unshare -rn` (or run the lane in a
container on `a0-egress-internal`), and leave the orchestrator — the process that talks to the
model endpoint — outside the barrier. That is exactly the right shape anyway, because the
orchestrator legitimately needs model access. Verify with:

```bash
./probe_egress.sh check --mechanism unshare-rn --cmd '<the exact command your lane runs>'
```

**Caveat on the codex CLI's own hard guarantee.** §4.3 relies on "Codex CLI `workspace-write`
defaults to `network_access: false`". That is a *config-level* claim and this audit could not
test it end-to-end, because codex cannot complete any call on this machine (§3.1). It also does
not close a lane that drops to `full-access`, which is precisely KAPSO's documented problem.

### 6.4 Environment quirk that affects every network-touching check

Egress on this host is **not plain**, and this bit me once during the audit:

* `http_proxy`/`https_proxy` are set to `http://127.0.0.1:7890` (mihomo / Clash Meta; PID 608,
  with a `tun0` interface at `10.8.0.106/24` up, though the default route is the wifi NIC).
* The proxy **breaks some hosts**: `curl https://pypi.org/simple/` through the proxy returns
  `000`/timeout, while direct returns `200`.
* Raw TCP connects to *some* public IP literals time out even though the host is online —
  `1.1.1.1:443`, `8.8.8.8:443`, `9.9.9.9:443` all time out, while `1.1.1.1:80`, `8.8.8.8:53` and
  `example.com:443` (by name) connect fine. This is why the probe's canary tries several targets
  and reports which one worked (`tcpvia=`), instead of hanging on one hardcoded IP.
* The canary uses `--noproxy '*'`: a probe must measure the target context's own egress, not a
  relay the host happens to have configured.

**Implication for adapter authors:** if a tool honours `http_proxy`, pypi/npm installs may fail
even though the network is fine — run network-touching installs with the proxy unset. The whole
dependency matrix in §4 was run with `http_proxy`/`https_proxy` unset for this reason.

---

## 7. Check 5 — Resource headroom

```console
$ nproc ; lscpu | grep 'Model name'
12
Model name:  AMD Ryzen 5 9600X 6-Core Processor      # 6 cores / 12 threads

$ free -h
               total        used        free      shared  buff/cache   available
Mem:            30Gi        11Gi       5.2Gi       547Mi        13Gi        19Gi
Swap:          8.0Gi          0B       8.0Gi

$ df -h /
/dev/nvme0n1p3  286G  135G  137G  50% /
$ swapon --show
/dev/nvme0n1p2 partition 8G 0B -1

$ uptime
15:44:16 up 6:38, 1 user, load average: 0.26, 0.28, 0.37
```

**Verdict: PASS.** One Postgres (~150–250 MB) plus one Redis (~10 MB) are negligible.
Disk is the more relevant budget: the throwaway venvs measured 157 MB + 49 MB (KAPSO 3.11/3.12)
and 449 MB + 203 MB (EvE 3.11/3.12) — call it ~0.5–0.9 GB per pinned project environment, plus
~1.3 GB of images already pulled. At 137 GB free there is ample room for many concurrent
runtimes and their venvs.

The real constraint is **CPU (12 threads)** and, for concurrent agent runtimes, network latency
to model endpoints — with all concurrent runtimes blocked on model calls, load stays well below
saturation (0.26 now). One caveat: `/tmp` is a 16 GiB **tmpfs backed by RAM**, so anything large
placed there (venvs, checkouts, the Loreley clone) is drawn from the same 30 GiB pool rather than
from disk. Keep large working sets on `/` where possible.

---

## 8. What the adapters can and cannot count on

**Can count on (verified):**

* Pinned interpreters 3.11.15 and 3.12.11 via `uv`; both projects install cleanly on either, and
  on system 3.14.7 as well. Recommend **3.12**.
* A containerized Postgres 18.6 and Redis 8.10.1 with Loreley's exact credentials — commands in
  §5.2 — on free ports 5432/6379, reachable from the host and from sibling containers.
* A **working, selective egress barrier** (docker `--internal`, `unshare -rn`), with a reusable
  probe script and a self-test that proves the barrier is not merely broken networking.
* Ample disk/RAM/CPU headroom.

**Cannot count on (blocked/failed):**

* **`codex` cannot complete a model call.** Its provider is a local relay on `127.0.0.1:15722`
  that is not running. EvE is blocked by this; KAPSO's codex lane is blocked.
* **`claude` is not logged in to Anthropic.** It carries a DeepSeek relay token and a model id
  whose label says it expired 2026-09-10. Whether it works is UNKNOWN pending the one-line probe
  in §3.2.
* **No firewall control** (no root): closure cannot be done with iptables/nftables, nor by
  blocking at the host level. Only the two rootless barriers exist.
* **Loreley is not checked out at `4c375920`.** `a0/env/upstream/` is empty and no clone process
  was running. The pin is fetchable: `git ls-remote` shows
  `4c3759208e6b908f90716488ac3eec3dceaaf397` as both `HEAD` and `refs/heads/main`, so a plain
  `git clone` lands exactly on the pin. This is outside this audit's write scope
  (`a0/env/checks/**` only), so it was reported, not performed.

**Bottom line for A0:** the infrastructure prerequisites (interpreters, deps, containers, egress
closure, resources) are all satisfied. The blocker is model access: with `codex` dead, only
`SimpleLoop` (which needs no such CLI) is guaranteed runnable today, and §4.1's rule
`|R_1| >= 1` would reduce A0 to the baseline. Restoring the `127.0.0.1:15722` relay and
confirming `claude` are the two highest-value fixes before adapters are written.
