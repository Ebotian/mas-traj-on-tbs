# Rootless closure under a REMOTE model — a docker allowlist-proxy topology

Owner: `a0/notes/exit-closed/proxy-closure/**`. All measurements 2026-09-21 (CST, UTC+8).
Everything below is **verified by running it** on this host unless the line says *read from source*
or *inferred*. Raw transcripts: `evidence/01..05*.log`.

## 0. Verdict

**Confirmed.** A rootless topology does close client egress while the model stays remote:
`docker network create --internal` removes the default route entirely, and a single **dual-homed
allowlist proxy** is the one peer on that network with an uplink. A client on the internal network
fails every direct connection (`Network is unreachable`) and succeeds against
`api.deepseek.com` through the proxy **by container name**; the identical client on the default
bridge reaches the internet directly. `claude` 2.1.260, `opencode` v2.0.11 and `kilo` 7.7.5 all
complete real model turns under this topology, and all three report back the expected text.

One-line verdict: **the model being remote does not block closure — it changes the shape from
"no uplink" to "one allowlisted uplink", and that shape is verified end-to-end for all three CLIs.**

## 1. What was built

All names are `a0pc-*`. Nothing pre-existing is touched (`adapdc-catalog-postgres-1` was up before
and after, verified in `evidence` teardown run).

| Element | Value |
|---|---|
| Network `a0pc-internal` | `docker network create --internal --subnet 172.31.77.0/24` |
| Proxy `a0pc-proxy` | `python:3.12-slim` (already local, nothing pulled) + `proxy/allowlist_proxy.py` mounted read-only. Attached to **`bridge`** at 172.17.0.2 and to **`a0pc-internal`** at a pinned 172.31.77.10 |
| Proxy port | one plaintext listener, `8787` |
| Allowlist | CONNECT hosts `api.deepseek.com`, `openrouter.ai` (env `PROXY_ALLOW`); origin-form paths `/v1/messages`, `/v1/chat/completions`, `/v1/models` |
| Client `a0pc-cli` | on `a0pc-internal` only; the three CLIs bind-mounted read-only from the host |
| Services `a0pc-pg`, `a0pc-redis` | `postgres:16`, `redis:8`, on `a0pc-internal` only (requirement 4) |

Bring up / tear down:

```bash
a0/notes/exit-closed/proxy-closure/setup.sh            # network + proxy + client container
WITH_SERVICES=1 a0/notes/exit-closed/proxy-closure/setup.sh   # + postgres + redis
a0/notes/exit-closed/proxy-closure/teardown.sh         # removes every a0pc-* container/network
```

`setup.sh` is idempotent (re-ran mid-session and re-verified the barrier held). **No package was
installed and no image was pulled** — `python:3.12-slim`, `postgres:16` and `redis:8` were already
in the local image store.

### What the proxy is

`proxy/allowlist_proxy.py`, ~330 lines, Python stdlib only. Two request shapes on one port:

* **forward-proxy `CONNECT host:port`** — what `HTTPS_PROXY=` produces. Hostname matched against the
  allowlist; on a match the TLS stream is tunnelled end to end. **No MITM, no injected CA**: the
  client validates the real `api.deepseek.com` certificate (verified: `TLSv1.3`,
  `peer=((('commonName','api.deepseek.com'),),)`).
* **origin-form plaintext routing** — what a `base_url` pointing at the proxy produces. The path
  selects the upstream shape, so *one* listener serves both protocols without the client knowing
  either upstream URL:
  * `/v1/messages*` → `https://api.deepseek.com/anthropic/v1/messages*`
  * `/v1/chat/completions`, `/v1/models` → `https://api.deepseek.com/...`

Every decision is logged (`event=connect … decision=ALLOW|DENY`, `event=req … status=…`), which is
what `evidence/05_cli_window_proxy_log.txt` and `evidence/06_probe_window_proxy_log.txt` record.

### Credentials

The proxy is a **pass-through** — it needs no key at all, so no credential is stored anywhere in
the topology. Clients receive the key via `docker exec -e DEEPSEEK_API_KEY` with *no value*, so
docker copies it from the calling shell's environment: **it never enters argv, a config file, or any
container's persisted config**. Client-side configs reference it as `{env:DEEPSEEK_API_KEY}`. The
key was never printed and never written to disk.

## 2. Requirement 1 — name resolution inside `--internal`

**Answer: container names resolve; external names do not.** Docker's embedded DNS still works on an
`--internal` network, which is why the client can and should address the proxy **by name**.

```
resolv.conf nameserver                      -> 127.0.0.11  (docker embedded DNS)
container name  a0pc-proxy                  -> 172.31.77.10
external name   api.deepseek.com            -> gaierror: [Errno -3] Temporary failure in name resolution
external name   example.com                 -> gaierror: [Errno -3] Temporary failure in name resolution
```

`evidence/02_closure_probe.log` §P1. This confirms and explains the earlier `gaierror` finding: the
embedded resolver still resolves network-scoped container names/aliases; only *forwarding* to the
host's upstream resolvers fails, because that forwarding runs inside the container's own namespace,
which has no route. The proxy container — which does have uplink — resolves external names normally
via `/etc/resolv.conf` on the bridge side.

A stable IP is also available (`--ip 172.31.77.10` on connect) and is what the delivered topology
pins, but **name is the better contract**: it survives a proxy restart onto a different address and
it is what all three CLIs accept natively in their `base_url`.

## 3. Requirement 2 — the two controls, executed

Canonical lines from the sibling probe, `a0/env/checks/probe_egress.sh`, pointed at this network
(`INTERNAL_NET=a0pc-internal`) — `evidence/01_controls_probe_egress.log`:

```
EVIDENCE mechanism=docker-internal mode=canary rc=0 dns=fail tcp=fail tcpvia=none https=fail egress=BLOCKED
VERDICT  docker-internal: CONFIRMED (expected egress_blocked, observed egress_BLOCKED)

EVIDENCE mechanism=docker-bridge   mode=canary rc=0 dns=ok tcp=ok tcpvia=example.com:443 https=ok egress=OPEN
VERDICT  docker-bridge:   CONFIRMED (expected egress_open,    observed egress_OPEN)
```

Sharper, IP-literal controls so DNS cannot mask the result (`evidence/02_closure_probe.log`):

| Control | Observed |
|---|---|
| **Negative** — internal client → internet, direct | `123.148.116.184:443`, `1.1.1.1:443`, `8.8.8.8:53`, `140.82.121.4:443` → all `[Errno 101] Network is unreachable` |
| **Positive** — same client → model through the proxy | `GET http://a0pc-proxy:8787/v1/models` → `HTTP 200`, `models: ['deepseek-flash','deepseek-v4-pro']` |
| **Selectivity** — same image on the bridge, direct | `https://example.com` → `HTTP 200` (and `1.1.1.1:443` times out, the known host filter recorded in `probe_egress.sh`) |

Extra properties measured, because "blocked" alone is not a closure claim:

* **Lateral moves are impossible.** The client's only route is `172.31.77.0/24`; the proxy's
  *bridge-side* IP `172.17.0.2:8787` and the bridge gateway `172.17.0.1:443` both return
  `Network is unreachable`. A scan of the whole subnet × ports {8787,443,6379,5432,80,22} from the
  client returns exactly the intended peers: `172.31.77.10:8787` (proxy), `172.31.77.3:5432`
  (postgres), `172.31.77.4:6379` (redis).
* **The proxy is not an open relay.** `http://a0pc-proxy:8787/https://example.com` → `HTTP 403`.
* **The allowlist really constrains the model provider.** `claude` left on its default provider with
  only `HTTPS_PROXY` set fails with
  `API Error: 403 a0pc-proxy: destination not on allowlist` — not a network error, an explicit
  policy refusal.
* **Real denials from real CLIs** (`evidence/05_cli_window_proxy_log.txt` — the preserved
  `docker logs` window covering the CLI runs). Every one of these would have been an open channel
  without the proxy; the counts are for that window only (`docker logs` is per container instance
  and resets when `setup.sh` re-runs):

  | Denied host | Requested by | count in window |
  |---|---|---|
  | `api.kilo.ai:443` | kilo (account/telemetry) | 2 |
  | `us.i.posthog.com:443` | kilo + opencode (analytics) | 2 |
  | `api.anthropic.com:443` | claude, left on its default provider | 2 |
  | `models.opencode.ai:443` | opencode (model registry) | 1 |
  | `models.dev:443` | opencode (model registry) | 1 |

  In the same window, `api.deepseek.com:443` was **allowed 4 times** and three upstream model
  responses returned 200 (`/v1/messages?beta=true`, `/v1/chat/completions` ×2). The wider session
  also recorded denials for `example.com:443`, `1.1.1.1:443` and `api.openai.com:443` (the probe
  controls), and `event=deny … path=/api/hello` (Claude Code's own reachability probe).

## 4. Requirement 3 — how to point the CLIs at the proxy

### The measurement

Each of the three CLIs was run **inside `a0pc-internal`** under both strategies and asked for a
fixed reply. All six succeeded (`evidence/03_cli_routes.log`), with the model actually served:

| CLI | Protocol | Route (a) plaintext `base_url` | Route (b) `HTTPS_PROXY` | served model |
|---|---|---|---|---|
| `claude` 2.1.260 | Anthropic Messages | `result: "PROXY-OK"` | `result: "HTTPS-PROXY-OK"` | `deepseek-flash` (as requested) |
| `opencode` v2.0.11 | OpenAI Chat Completions | `"PROXY-OK"` | `"HTTPS-PROXY-OK"` | via `a0pc/deepseek-flash` |
| `kilo` 7.7.5 | OpenAI Chat Completions | `"KILO-PROXY-OK"` | `"KILO-HTTPS-PROXY-OK"` | via `a0pc/deepseek-flash` |

Both strategies *work* for all three. They are not equally robust:

### Recommendation — use (a), plaintext `base_url` to the proxy, as the primary control

| | (a) `base_url` → `http://a0pc-proxy:8787` | (b) `HTTPS_PROXY=http://a0pc-proxy:8787` |
|---|---|---|
| Where the policy lives | **explicit config the runtime must set** — an unreachable proxy is a config error you see immediately | ambient environment; a missing/typo'd var silently means *no* proxy |
| Failure mode | loud: connection refused | silent egress attempt, or a 403 that looks like an auth error |
| Works for all three | yes — all three have a documented base-URL/`provider.options.baseURL` seam | yes **on these versions**, but only because their HTTP stacks happen to honour the env var |
| Credential handling | proxy can hold/replace the key, client can send a dummy — the candidate never needs the real key | client must hold the real key and speaks TLS itself |
| TLS / MITM | none needed | none needed (CONNECT hostname allowlist, real cert) |
| Attribution | per-CLI config, visible in the runtime's own config surface | process-global, easy to leak into unrelated tools |

Route (b) is still required as a **defence in depth** for the parts of a CLI that do not go through
its configured base URL — for example Claude Code's own `HEAD /api/hello` reachability probe, which
the proxy denied (`event=deny … path=/api/hello reason=no_route`) and which the CLI tolerated. Set
both, but make (a) the thing you verify.

### The proxy must forward two upstream shapes — and does, on one listener

Claude Code speaks **Anthropic Messages** (`POST /v1/messages`); opencode and kilo speak **OpenAI
Chat Completions** (`POST /v1/chat/completions`). Both are served by the same port: the path picks
the upstream, and `/v1/messages` is rewritten to DeepSeek's Anthropic-compatible prefix
`/anthropic` (`evidence/02_closure_probe.log` §P7 — observed `served_model=deepseek-v4-pro` on both
shapes). Two listeners are unnecessary. **No MITM is needed**: the HTTPS side is a plain CONNECT
tunnel allowlisted by hostname, and the plaintext side terminates at the proxy, which holds the
upstream CA-trusting connection.

### Per-CLI wiring details that cost time and are worth recording

1. **`ANTHROPIC_BASE_URL=http://a0pc-proxy:8787`** — Claude Code appends `/v1/messages`, and the
   proxy maps that to `/anthropic/v1/messages`. Auth via `ANTHROPIC_AUTH_TOKEN`. Claude Code prints
   `[claude-code:unrecognized_model] {"model":"deepseek-flash"}` but proceeds.
2. **`opencode` needs `OPENCODE_CONFIG=<path to a file>`, not `OPENCODE_CONFIG_CONTENT`.** With the
   content env var set, the provider is silently not registered and the run dies with
   `Model unavailable: a0pc/deepseek-flash`. With a file path, `opencode debug config` shows the
   provider loaded (`package: aisdk:@ai-sdk/openai-compatible`).
3. **`opencode` v2 runs a background service; `docker exec -e` does not reach it.** Without
   `--standalone` the provider call came back **HTTP 401** even though the env var was set for the
   exec, because the provider request is issued by the already-running server process. `--standalone`
   makes the server inherit this process's environment and it works. Anyone closing an opencode lane
   must account for this or they will chase a phantom auth bug.
4. **`{env:VAR}` substitution in the config did not resolve** on opencode v2.0.11: a control probe
   with `{env:A0PC_TEST_VAR}` and `A0PC_TEST_VAR=xyzzy-visible` still produced `"apiKey": ""`. It
   *did* resolve under `kilo` 7.7.5 (`KILO_CONFIG_CONTENT`). Treat `{env:…}` as version-dependent and
   verify per version.
5. **`kilo` bundles `@ai-sdk/openai-compatible`** (571 string references); `opencode` references it
   too. Neither needed to fetch a provider package over the network — the closure-critical question
   the Loreley report flagged as *inference* (§6.2 of `a0/notes/exit-closed/loreley/REPORT.md`) is
   now **measured**: the custom provider resolves with egress restricted.
6. **Both CLIs degrade gracefully when their registry/telemetry hosts are denied** —
   `models.dev`, `models.opencode.ai`, `api.kilo.ai`, `us.i.posthog.com` were all refused and the
   model turns still completed. `opencode models` simply listed only the built-in `opencode/*`
   models plus the configured one.

### Cost, as the tools themselves printed it

| Run | input | output | tool-reported cost |
|---|---|---|---|
| `claude` route (a), `deepseek-v4-pro` | 17 297 | 25 | `total_cost_usd: 0.08711` |
| `claude` route (b), `deepseek-v4-pro` | 17 299 | 8 | `total_cost_usd: 0.086695` |
| `claude` route (a), `deepseek-flash` | 17 233 | 5 | `total_cost_usd: 0.08629` |
| `claude` route (b), `deepseek-flash` | 17 235 | 8 | `total_cost_usd: 0.086375` |
| `kilo` route (a) | 11 929 | 9 | `cost: 0` |
| `kilo` route (b) | 284 in + 11 648 cached | 12 | `cost: 0` |
| `opencode` (both routes) | 5 977 in, 384 cached | 5 (+14 reasoning) | session `cost: 0.0` |

**Session total ≈ US$0.35, and about US$0.35 of that is Claude Code's `total_cost_usd`.** Two
caveats on those numbers, both material:

* Claude Code's figure is computed from **its own Anthropic pricing table for a model it does not
  recognise** — it reports `"costBasis":"unknown"`, `"provider":"firstParty"`,
  `"canonicalModel":"deepseek-flash"`. It is *not* the DeepSeek bill; treat it as an upper-bound
  estimate. The real spend is lower.
* `kilo` and `opencode` report **0 / unpriced** for a custom provider, exactly the `pricing.py`
  behaviour the Loreley report predicted (`a0/notes/exit-closed/loreley/REPORT.md` §3 item 4):
  unknown model ⇒ `unpriced`, cost `None`. A study tracing cost on this route must supply a pricing
  table or accept `unpriced`.
* Claude Code's ~17.2 k input tokens per trivial turn is its system prompt, and it matches the
  protocol's own 18–20 k figure — worth budgeting for.

## 5. Requirement 4 — the Loreley shape: worker + Postgres + Redis

**Answer: Postgres and Redis can simply join the internal network and be addressed by container
name. They do not need to sit with the worker, and doing so does not weaken the closure claim —
provided they are attached to the internal network *only*.** Measured in
`evidence/04_loreley_services.log`:

1. **By name, from the internal side:** `a0pc-pg:5432 → CONNECTED (dns 172.31.77.3)`,
   `a0pc-redis:6379 → CONNECTED (dns 172.31.77.4)`. Docker's embedded DNS resolves them with no
   extra config.
2. **The closure claim is unchanged:** with both services up, the worker/client's direct egress is
   still `[Errno 101] Network is unreachable` on every target.
3. **Dual-homing a service does *not* leak an uplink.** Attaching `a0pc-pg` and `a0pc-redis` to the
   default bridge as well (which is exactly what the existing `a0-loreley-postgres` /
   `a0-loreley-redis` containers do — they sit on both `a0-loreley-internal` *and* `a0-loreley-net`)
   left the internal client at `[Errno 101] Network is unreachable`, and even the bridge-side IP of
   the redis container remained unreachable. Services do not forward IP traffic.
4. **But a service's own reachability follows its interfaces:** the redis container could not reach
   the model endpoint while internal-only, and *could* once dual-homed onto the bridge. So a
   dual-homed service is itself an unclosed context — it just isn't the *worker's* context.

Three consequences for Loreley, and the reason the answer is not a flat "yes":

* **The "exactly one reachable peer" phrasing must be restated.** With services up, the internal
  subnet scan returns three peers, not one. The accurate claim is: *one peer has an uplink, and that
  peer enforces a hostname allowlist.* The postgres and redis containers have no uplink of their own.
* **The worker's placement is what decides the claim, not the services'.** Loreley's worker currently
  runs on the host and reaches its containers through published `127.0.0.1:5432` / `:6379` ports
  (`docker inspect` on the existing containers confirms both are published on `127.0.0.1`). A host
  process has the host's egress, so a host-side worker's *own* channel is open regardless of what the
  containers do, and the existing `a0-loreley-internal` network buys nothing for it. To close the
  worker's channel the worker must move **inside** the internal network — and then it can no longer
  use `127.0.0.1` published ports; it must address `a0pc-pg` / `a0pc-redis` by name, which item 1
  shows works.
* **The network layer is one-way.** The host can reach *into* the internal network
  (`host -> 172.31.77.3:5432 CONNECTED`, because dockerd owns the bridge). That is not an egress
  hole, but it does mean the barrier is "no traffic out", not "no traffic in", and any orchestrator
  on the host can bypass the proxy by dialling a container IP directly. That is a *tooling* trust
  boundary, not a candidate-code one, and should be stated as such.
* **Attack surface, not egress, is the residual risk of co-locating Redis.** A candidate that can
  reach an unauthenticated `redis:8` gains file-write primitives inside the *redis* container
  (`CONFIG SET dir` + `SAVE`), not in the worker. It does not yield egress. But it enlarges what a
  hostile candidate can touch, and it is the one part of this topology where "the closure claim
  holds" is true for network reasons while "the candidate is contained" is not automatically true.
  Redis with `requirepass` + `rename-command` hardening, or a Unix-socket-only bind, would remove it.

## 6. What breaks per runtime

| Runtime | Breakage under this topology | Status |
|---|---|---|
| **claude** 2.1.260 | none functionally; emits `[claude-code:unrecognized_model]`; its `HEAD /api/hello` preflight is denied (harmless); `total_cost_usd` is a wrong-pricing estimate | works |
| **opencode** v2.0.11 | **`OPENCODE_CONFIG_CONTENT` is not honoured** (needs a file path); **a background service breaks env propagation — needs `--standalone`**; `{env:…}` substitution unresolved; `models.dev`/`models.opencode.ai` denied so the model registry is reduced to built-in + configured entries | works with the above |
| **kilo** 7.7.5 | none functional; `api.kilo.ai` + `us.i.posthog.com` denied (account/telemetry) — tolerated; `{env:…}` in `KILO_CONFIG_CONTENT` works; cost reports `0` | works |
| **codex** | retired; `wire_api="chat"` removed in 0.154.0 and nothing here serves the Responses API. This proxy would need a `/v1/responses` route to reintroduce it | out of scope |
| **Loreley worker + pg + redis** | worker must move inside the internal network and lose `127.0.0.1` published ports; re-address services by container name (verified working). Postgres/Redis need no change beyond network attachment | works with re-placement |
| **GPU workloads** | none needed here — the model is remote. Noted because this host currently exposes no GPU inside containers | n/a |

## 7. Residual gaps — what this probe does *not* prove

1. **The proxy is not network-enforced.** It sits on `bridge` with unrestricted egress; the
   allowlist is ~330 lines of software, not a kernel or firewall rule. Everything the proxy does
   not implement is permitted to it. The candidate is closed; the *proxy* is a trusted component
   whose correctness is the whole claim. A shorter/audited proxy, or a `--internal`-plus-NAT rule
   set in the egress namespace, would be a stronger foundation.
2. **The barrier is one-way and host-permeable.** The host can dial any container IP on
   `a0pc-internal` directly (`evidence/04` §2). Candidate code runs in a container so it cannot, but
   any host-side component bypasses the proxy entirely. This is not a defence against a compromised
   host or against host-side orchestrator code.
3. **"Closed" is proven for the egress paths probed, not for all egress paths.** The negative
   controls cover DNS, raw TCP to IP literals, and HTTPS. They do not cover e.g. non-IP link layers,
   IPv6 (the internal network is IPv4-only here — worth confirming if it matters), ICMP tunnelling,
   or a side-channel through a service peer that itself has a second interface.
4. **No tool-use / agentic round was run.** Every CLI call here is a single text turn. Tool calls
   (Bash, file edits) were not exercised inside the container, so "the candidate's tool loop is
   confined" is inherited from the network barrier, not separately measured. The Anthropic-shape
   probe in `evidence/02` §P7 confirms `stop_reason`-level tool plumbing is reachable through the
   proxy, but not a full agent loop.
5. **`{env:…}` behaviour is version-specific and was measured on one version each.** A CLI upgrade
   can change it silently; item 4 in §4 is a snapshot, not a contract.
6. **Cost figures are not DeepSeek's.** See §4 — Claude Code's `total_cost_usd` uses Anthropic
   pricing against an unrecognised model, kilo/opencode report `unpriced`. The honest statement is
   "≈US$0.35 of *tool-reported* cost, real spend lower and unmeasured".
7. **Nothing about the *quality* of DeepSeek behind these CLIs was assessed** — this lane answers
   topology and closure, not whether the replacement model is adequate for A1.
8. **Redis/Postgres reached by a candidate are not hardened.** Unauthenticated `redis:8` on the same
   L2 is a file-write primitive inside the redis container. See §5.

## 8. Evidence index

| Artefact | Contents |
|---|---|
| `setup.sh` | idempotent bring-up of network + proxy + client container (+ `WITH_SERVICES=1` for pg/redis) |
| `teardown.sh` | removes every `a0pc-*` container and network; verifies `adapdc-catalog-postgres-1` untouched |
| `proxy/allowlist_proxy.py` | the stdlib proxy (CONNECT allowlist + dual-shape plaintext routing), all decisions logged |
| `probe_closure.sh` | P1–P7: name resolution, both controls, selectivity, peer scan, allowlist enforcement, dual-shape upstream |
| `probe_loreley_services.sh` | requirement-4 experiment (name routing, one-way barrier, dual-homing, service-side uplink) |
| `run_cli_through_proxy.sh` | the runnable, re-executable per-CLI answer for requirement 3 |
| `evidence/01_controls_probe_egress.log` | canonical `probe_egress.sh` controls on this network |
| `evidence/02_closure_probe.log` | P1–P7 full transcript |
| `evidence/03_cli_routes.log` | all six CLI×route runs + the allowlist negative control |
| `evidence/04_loreley_services.log` | requirement-4 transcript |
| `evidence/05_cli_window_proxy_log.txt` | proxy decisions during the CLI runs (verbatim `docker logs` window) |
| `evidence/06_probe_window_proxy_log.txt` | proxy decisions during the probe-window container instance |

Note: `docker logs a0pc-proxy` is per **container instance**. `setup.sh` recreates the proxy, so the
live log restarts empty; the two files above are the preserved windows and are what the counts in
§3 refer to.

### Reproduce

```bash
cd a0/notes/exit-closed/proxy-closure
./setup.sh && WITH_SERVICES=1 ./setup.sh
./probe_closure.sh                                    # no key needed except P3/P7
./probe_loreley_services.sh
DEEPSEEK_API_KEY=$(sed -n 's/^deepseek://p' ~/gptapi.md|head -1); export DEEPSEEK_API_KEY
./run_cli_through_proxy.sh                            # spends ~US$0.17 (4 claude turns)
unset DEEPSEEK_API_KEY
./teardown.sh
```

### Live state at hand-off

`a0pc-internal` (internal), `a0pc-proxy` (bridge + a0pc-internal), `a0pc-cli`, `a0pc-pg`,
`a0pc-redis` are left **running** so the probes can be re-run immediately; `teardown.sh` removes
them all and touches nothing else. `adapdc-catalog-postgres-1` was up before and after and was never
referenced.
