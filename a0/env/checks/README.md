# a0/env/checks — how to rerun every check

Environment-readiness audit for the A0 measurement study. Findings live in
[`ENV_REPORT.md`](ENV_REPORT.md); machine-readable verdicts, docker commands and port
inventory live in [`env_status.json`](env_status.json).

Everything here writes **only** inside this directory. Raw evidence for the audit run is in
`logs/`.

## Contents

| File | Purpose |
|---|---|
| `ENV_REPORT.md` | full report: verdicts, commands, observed output, implications |
| `env_status.json` | same verdicts machine-readable + reusable `docker run` commands + ports to avoid |
| `probe_egress.sh` | reusable closure probe — proves egress is or is not blocked for **any** runtime |
| `run_dep_matrix.sh` | reruns the KAPSO/EvE dependency-resolution matrix |
| `logs/` | raw output of every command cited in the report |
| `kapso/`, `eve/` | extracted dependency lists (`core-reqs.txt`, `locked-reqs.txt`) |

---

## 1. Provenance / toolchain

```bash
codex --version; claude --version; uv --version; node --version
python3 --version; typst --version; docker version --format '{{.Server.Version}}'
```

## 2. CLI login state (the section that matters most)

No credential file is read by any of these — each CLI resolves its own credentials internally and
prints a redacted answer.

```bash
# codex: credential state
codex login status                       # -> "Logged in using an API key - ***"
codex doctor --summary --no-color        # auth/network/sandbox check rows
codex doctor --json                      # redacted machine-readable report

# codex: the one that actually determines usability (a FAILING call bills nothing)
timeout 90 codex exec --sandbox read-only --skip-git-repo-check 'Reply with exactly: OK'
#   expected healthy: prints OK
#   measured 2026-09-20: "ERROR: Reconnecting... 1/5..4/5" then exit 124 (provider down)

# claude: credential state vs. real login (they disagree; read both)
claude auth status                       # -> {"loggedIn": true, "authMethod": "oauth_token"}
claude doctor                            # -> "Not signed in to claude.ai" (custom base URL)

# claude: NOT run by the audit, because it is a billed model call.
# This is the smallest command that settles claude's usability:
cd /tmp && timeout 120 claude -p 'Reply with exactly: OK'
```

If `codex exec` hangs and retries, check whether its provider exists:

```bash
grep -E 'base_url|model_provider|^model' ~/.codex/config.toml   # -> http://127.0.0.1:15722/v1
ss -ltn | grep 15722                                            # -> no listener => relay not running
```

## 3. Interpreter pinning and dependency resolution

```bash
uv python install 3.11 3.12
uv python list | grep -E '3\.11|3\.12'
./run_dep_matrix.sh            # writes logs/dep_matrix.log; ~2 min; creates and uses throwaway venvs
```

`run_dep_matrix.sh` unsets `http_proxy`/`https_proxy` (the host proxy breaks some indexes) and
points `UV_CACHE_DIR` inside this directory. Re-run only the pieces you need:

```bash
# KAPSO core deps (the documented `pip install -e .` path)
uv venv --python 3.12 /tmp/v312 && \
  uv pip install --python /tmp/v312 -r kapso/core-reqs.txt

# EvE locked set — note UV_PROJECT_ENVIRONMENT so /tmp/eve is never modified
cd /tmp/eve && uv export --frozen --no-emit-project --format requirements-txt -o /tmp/eve-reqs.txt
uv venv --python 3.12 /tmp/v312e && uv pip install --python /tmp/v312e -r /tmp/eve-reqs.txt
```

Expected today: both PASS on 3.11/3.12/3.14; KAPSO's `requirements.txt` FAILS on both 3.11 and
3.12 (stale aggregate — use `pip install -e .` instead).

## 4. Container infrastructure for Loreley

Ports 5432/6379 are free; 5433 belongs to the pre-existing `adapdc-catalog-postgres-1` — **never**
touch, stop or reuse that container.

```bash
# start (verified working)
docker run -d --name a0-loreley-redis -p 127.0.0.1:6379:6379 redis:8 redis-server --appendonly yes
docker run -d --name a0-loreley-postgres \
  -e POSTGRES_USER=loreley -e POSTGRES_PASSWORD=loreley -e POSTGRES_DB=loreley \
  -p 127.0.0.1:5432:5432 postgres:18

# verify — redis-cli is NOT installed on the host, so exec inside the container
for i in $(seq 1 40); do docker exec a0-loreley-postgres pg_isready -U loreley -d loreley && break; sleep 1; done
docker exec a0-loreley-redis redis-cli ping
docker exec a0-loreley-postgres psql -U loreley -d loreley -c 'select version();'
psql "postgresql://loreley:loreley@localhost:5432/loreley" -c 'select current_user, current_database();'

# tear down
docker rm -f a0-loreley-redis a0-loreley-postgres
```

For the variant that also satisfies the §4.3 closure requirement, see
`env_status.json → containers.verified_docker_run_commands.variant_B_closed_network_recommended`.

## 5. Egress / closure probe

```bash
./probe_egress.sh list        # mechanisms and what each one is expected to do
./probe_egress.sh self-test   # positive AND negative controls for every mechanism
./probe_egress.sh check --mechanism docker-internal
./probe_egress.sh check --mechanism unshare-rn --cmd '<the exact command your runtime runs>'
```

Mechanisms: `host` and `docker-bridge` (positive controls, egress must be OPEN), `docker-internal`,
`docker-none`, `unshare-rn` (barriers, egress must be BLOCKED).

`self-test` exits non-zero on any mismatch and prints `SELF-TEST: PASS|FAIL`. It also starts a
sibling redis on the internal network and requires the barrier to leave that channel **reachable**
(`local=ok`) — otherwise a barrier that simply broke networking would look like a pass.

Exit codes: `0` observed matches expectation, `1` mismatch, `2` usage/environment error.
Add `--json FILE` to append machine-readable results, `--timeout N` to change the per-check cap.

Two sharp edges, both measured: `unshare -rn` and `docker --internal` also cut the process off
from **host-localhost** services, because a new network namespace has its own loopback. Wrap only
the candidate-execution channel, and put anything a containerized runtime needs (Postgres, Redis,
model relay) on the **same internal network as a sibling**.

## 6. Resources

```bash
nproc; lscpu | grep 'Model name'; free -h; df -h /; uptime
docker info --format '{{.DockerRootDir}}'
```

## 7. Leave the machine as you found it

```bash
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'   # expect only the pre-existing adapdc containers
docker network ls                                                    # expect no a0-* networks
ss -ltn                                                              # expect 5433/7890/7891/1053/9093/44169/39349
du -sh .                                                             # this directory stays small (logs only)
```

The audit deleted its throwaway venvs (157M+49M+449M+203M) and uv cache, removed every container
and the internal network it created, and left only the `postgres:18` / `redis:8` / `alpine:3.21`
images (needed by the Loreley adapter and by `probe_egress.sh`).
