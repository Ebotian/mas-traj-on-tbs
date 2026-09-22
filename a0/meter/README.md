# `a0/meter/` — the plaintext metering proxy and its usage ledger

Owner of this directory: the metering worker. It implements `a0/tasks/maxcut/INTERFACE.md` §8 and
nothing else. It **never** modifies `INTERFACE.md`; where the interface leaves something open, the
decision is recorded in `DEVIATIONS.md` in this directory.

The component exists to make one sentence true: *"this campaign's `CEq` is a number the runtime
could not have lied about."* It is the enforcement point for constraint (iv) of the project's
first principles, and the visibility point for constraint (v).

---

## 1. What it is

```
 runtime (claude / opencode / kilo / any HTTP client)
   │  plaintext HTTP/1.1,   base_url = http://127.0.0.1:<campaign port>
   ▼
 a0/meter/meter_proxy.py            <- terminates HTTP here, reads the token fields
   │  one ledger row per upstream call, fsync'd before the response is released
   │  HTTPS, certificate-verified
   ▼
 https://api.deepseek.com           <- the only destination the proxy can reach
```

* **In:** plaintext HTTP. This is not a convenience — it is the precondition for metering.
  Under `HTTPS_PROXY`/CONNECT the proxy sees ciphertext and can read neither tokens nor cache
  hits (`a0/A1-CONTRACT-AUDIT.md` §B2 is the audit that established this). CONNECT is therefore
  **refused with 405**, never tunnelled.
* **Out:** TLS with certificate verification against the system trust store (or `--upstream-ca`).
* **Destination:** `--upstream-base`, which must be on `--allowlist`. A client's `Host` header
  and any absolute-URI request target are *checked* against the allowlist and then discarded;
  the upstream host is never taken from client bytes. The proxy is not an open relay, and the
  failure mode of a misconfigured client is a 403, not a silent forward.

### 1.1 The outbound request is framed by the proxy, not by the client

`http.client.endheaders(message_body)` writes the request head and then the body; it adds **no**
framing header. Every framing header on the upstream leg is therefore stated by `forward()`, from
the bytes it is about to write:

| client sent | proxy sends upstream |
|---|---|
| `Content-Length: N` + body | `Content-Length: <len(body)>` — re-derived, never the client's number |
| `Transfer-Encoding: chunked` + chunks | `Transfer-Encoding: chunked`, re-encoded by `http.client` from the decoded body |
| both (a smuggling shape) | chunked, per RFC 9112 §6.1; the client's `Content-Length` is dropped |
| no body, no framing header | no framing header (a `GET /v1/models`, unchanged) |
| a body with **no** framing header | refused: `400 request_body_unframed`, recorded, never forwarded |

This is a correctness fix for a defect that made the budget unmeasurable: `Content-Length` used
to sit in `HOP_BY_HOP`, so it was stripped, `endheaders` did not re-add it, and the upstream
received a body with no framing header at all. A conforming server reads no body, so every real
call answered `400 … EOF while parsing a value at line 1 column 0` and was booked `unmetered` —
which means §8's `CEq` could never have carried a real number.

**Evidence, on the wire.** `raw_tap.py --proof` runs the proxy against a raw socket that records
the exact bytes it receives and answers an unframed body the way DeepSeek does. Before/after
captures live in `evidence/framing_before.txt` and `evidence/framing_after.txt`; the pre-fix
capture shows the 98-byte body arriving under a head with no `Content-Length` and no
`Transfer-Encoding`, answered `400`, booked `unmetered`. The after capture shows
`Content-Length: 98` (and, for the chunked client, `Transfer-Encoding: chunked` with the same
decoded body) and two metered rows. `evidence/selftest_on_prefix_proxy.txt` is the same selftest
run against the pre-fix revision: **36/65**, exit 1, versus 65/65 for this one.

**Why the selftest missed it for 55/55.** `fake_upstream.py` read the body length from
`content-length`, got zero bytes, and answered from its scenario default; every check asserted on
the *response*. The mock has been made wire-shaped: it frames its own reads (`Content-Length` or
chunked), records the framing headers, the body byte count and the body's sha256, requires a
credential, and answers a body it could not read or parse with `400`. Section S18 of the selftest
now reads that log back, and S19 proves an undelimitable body never reaches the upstream.
`tests/test_meter_framing.py` pins the same property at unit level (17 tests).

## 2. The ledger row

Exactly the key set and order of `INTERFACE.md` §8 — verified by `verify_ledger.py`, which
rejects any extra or missing key:

```json
{"schema":"a0.meter.call/v1","campaign_id":"C_0001","arm_id":"A_base",
 "ts":"2026-09-22T15:04:11.077027+08:00","provider":"deepseek",
 "endpoint":"https://api.deepseek.com/v1/chat/completions","model_requested":"deepseek-flash",
 "model_reported":"deepseek-flash","provider_request_id":"...","stream":false,
 "usage":{"prompt_cache_hit_tokens":1280,"prompt_cache_miss_tokens":10240,"completion_tokens":312},
 "ceq":11513,"unmetered":false,"reason":null}
```

### The arithmetic, frozen

```
ceq = prompt_cache_miss_tokens + floor(prompt_cache_hit_tokens * 2 / 100) + 4 * completion_tokens
```

Integer arithmetic only: `(hit * 2) // 100`. No float ever touches a score. `ceq(...)` rejects
negative or non-integer inputs rather than crediting them.

Worked: `miss=10240, hit=1280, completion=312` → `10240 + 25 + 1248 = 11513`.
Worked: `miss=184, hit=2048, completion=55` → `184 + 40 + 220 = 444`.

### The three provider faces, one triple

| face | `prompt_cache_hit_tokens` | `prompt_cache_miss_tokens` | `completion_tokens` |
|---|---|---|---|
| OpenAI chat completions (DeepSeek native) | `prompt_cache_hit_tokens` | `prompt_cache_miss_tokens` | `completion_tokens` |
| OpenAI Responses / generic OpenAI | `input_tokens_details.cached_tokens` | `input_tokens - cached` | `output_tokens` |
| Anthropic Messages | `cache_read_input_tokens` | `input_tokens + cache_creation_input_tokens` | `output_tokens` |

Anthropic's `input_tokens` is the **uncached** input, so everything not served from cache — fresh
input plus cache writes — is charged at the miss rate. Cache reads are the only thing DeepSeek
discounts and the only thing that becomes `hit`. On the `/v1/messages` route, an omitted
`cache_read_input_tokens` is read as 0, because that is the Anthropic wire format's documented
encoding of "no cache read"; off that route, a missing cache split is a gap, not a zero.

### `unmetered` rows

`usage: null`, `ceq: null`, and a `reason` naming the gap. Never an estimate, never a zero:
a zero would be indistinguishable from "this call was free", which is the silent accounting hole
this component exists to close. Reasons this implementation emits:

| reason | meaning |
|---|---|
| `no_usage_field_in_response` | 2xx response with no `usage` object |
| `upstream_http_<code>_no_usage` | non-2xx response; error bodies do not carry usage |
| `empty_response_body` | 2xx with an empty body |
| `usage_present_without_cache_split` | prompt total reported, cache split not (`--on-missing-cache-split unmetered`) |
| `stream_truncated_before_usage[:<err>]` | the stream ended (or errored) before any *final* usage event |
| `stream_ended_without_usage` | the stream terminated normally but never reported final usage |
| `stream_usage_incomplete` | a final usage event appeared, but the triple could not be completed |
| `content_encoding_<enc>_not_parseable` | provider compressed the body despite `Accept-Encoding: identity` |
| `unparseable_response_body` | 2xx body that is not JSON |
| `inconsistent_usage_negative_field` | a negative token figure (rejected, not credited) |
| `upstream_unreachable:<ErrClass>` | the upstream call was attempted and failed |
| `non_allowlisted_host:<host>` / `host_header_not_allowlisted:<h>` / `path_not_routed:<p>` | destination policy refusal, recorded, nothing forwarded |
| `connect_not_supported` | a CONNECT tunnel was attempted (§8 forbids metering by tunnel) |
| `attribution_token_mismatch` | request arrived on campaign C's port without C's token |
| `request_body_unframed` | body bytes with neither `Content-Length` nor chunked framing: extent undefined, so refused rather than guessed (recorded, nothing forwarded) |
| `request_body_truncated` | declared length or chunked terminator never arrived |
| `request_body_length_unparsable` / `request_body_too_large` | `Content-Length` that is not a non-negative integer / exceeds the 64 MiB cap |

## 3. Attribution — how a row knows which campaign it belongs to

**Mechanism: one listening port per campaign; `(campaign_id, arm_id)` is fixed when the socket is
bound.** The registry (`campaigns.json`, schema `a0.meter.registry/v1`) lists one entry per
campaign with its port.

Why this and not a path prefix or a header:

* A path prefix and a header are **client-supplied data**. A runtime that drops or forges the
  field mis-attributes its own spend, and the ledger — whose only job is to be trusted about
  spend — would inherit that lie. A port is not data: it is where the bytes physically arrived.
* Attribution is decided **before any request exists**, so it cannot be influenced by request
  content, ordering, or concurrency.
* It survives concurrent calls by construction: each listener tags every row it writes with its
  own captured identity, and concurrent calls on one port are handled by one thread each with no
  shared mutable state. Concurrent calls on *different* ports cannot interact at all except
  through the ledger, whose appends are serialised by `flock` + `fsync`.

An optional per-campaign `token` adds an independent second check: when declared, requests on that
port must carry `X-A0-Meter-Token`. A mismatch is a 403 **recorded against that port's campaign**,
so the worst a cross-port request can achieve is a refusal booked against itself — it can never
make another campaign's spend appear to be its own.

### Exact CLI configuration a runtime needs

Give each campaign its own port. `--registry` is the preferred form; the single-campaign flags
exist for quick one-off use.

```bash
python3 a0/meter/meter_proxy.py \
  --registry  a0/meter/campaigns.json \
  --ledger    /var/lib/a0/C_0001/ledger.jsonl \
  --events    /var/lib/a0/C_0001/events.jsonl \   # diagnostic sidecar, never authoritative
  --aid-out   /var/lib/a0/C_0001/meter.aid.json \ # the AID_r fragment (§11 of AID_r)
  --allowlist api.deepseek.com                    # default; the ONLY reachable destination
  # --upstream-base https://api.deepseek.com      # default
```

Single campaign, no registry:

```bash
python3 a0/meter/meter_proxy.py --campaign-id C_0001 --arm-id A_base --port 8801 \
  --token "$(head -c 24 /dev/urandom | base64)" --ledger ./ledger.jsonl \
  --allowlist api.deepseek.com
```

Then point the runtime at **its own** port:

| runtime | protocol face | configuration |
|---|---|---|
| `claude` (Claude Code) | Anthropic Messages | `ANTHROPIC_BASE_URL=http://127.0.0.1:8801` — the CLI appends `/v1/messages`, which the proxy rewrites to `/anthropic/v1/messages`. `ANTHROPIC_AUTH_TOKEN=<deepseek key>`. Custom header, if the campaign has a token: `ANTHROPIC_CUSTOM_HEADERS="X-A0-Meter-Token: <token>"` |
| `opencode` | OpenAI Chat Completions | provider `options.baseURL = "http://127.0.0.1:8801/v1"`, `apiKey = <deepseek key>`, `options.headers = {"X-A0-Meter-Token": "<token>"}` |
| `kilo` | OpenAI Chat Completions | `KILO_CONFIG_CONTENT` with the same `baseURL`/`apiKey`/headers |
| any OpenAI-compatible client | Chat Completions | `base_url = "http://127.0.0.1:8801/v1"` |
| any OpenAI-compatible client | Responses API | `base_url = "http://127.0.0.1:8801/v1"` with path `/responses` |
| codex | Responses API | `base_url = "http://127.0.0.1:8801/v1"` (this proxy routes `/v1/responses`) |

**Do not set `HTTPS_PROXY` to this proxy.** CONNECT is refused by design; `HTTPS_PROXY` may be
set to the closure proxy for defence-in-depth (see
`a0/notes/exit-closed/proxy-closure/REPORT.md` §4), but the metered path is the plaintext
`base_url`. A runtime that has no configurable base URL cannot be metered by this component, and
that is a hard blocker for the campaign, not a workaround.

`meter.aid.json` is written at startup and is the fragment that belongs in `AID_r`:
`meter.mode = "plaintext_base_url"`, `meter.allowlist = ["api.deepseek.com"]`, the ledger path,
the row schema, and the verbatim formula. (The copy committed under `evidence/aid.json` is the
selftest's, so its `upstream_base` and `allowlist` point at the local fake upstream; a production
run with no `--upstream-base`/`--allowlist` flags declares `api.deepseek.com` and nothing else.)

## 4. Fail-closed

Three places, each with the failure it removes:

1. **Startup.** `--upstream-base`'s host must be on `--allowlist`, and the ledger must be
   writable, or the process exits non-zero. A proxy that can reach an unlisted upstream, or that
   cannot book what it spends, is not a metering boundary.
2. **Per call, before spending.** `Ledger.preflight()` opens the ledger for append. If that
   fails the call is refused with **500** and *the upstream is never contacted*. Proved: S10 in
   the selftest shows `upstream log lines 18 -> 18` across the refused call.
3. **Per call, before the client sees anything.** The row is appended and `fsync`ed *before* the
   response body is released. Non-streaming: the whole body is withheld and replaced by 500.
   Streaming: the protocol's terminal event (`[DONE]` / `message_stop` / `response.completed`) is
   held back, and on a ledger failure the connection is dropped without it — a client that never
   sees the terminator treats the stream as failed. **An unmetered success is not expressible.**

Content that precedes the hold point is forwarded immediately, so streaming fidelity is preserved
until the last event; the cost of the guarantee is one withheld terminal event, not a buffered
stream. S2 proves the content really is forwarded before the usage chunk exists: in
`evidence/report.txt` the content marker arrives at ~0.04 s and the usage chunk at ~0.41 s, with
the fake upstream sleeping 0.4 s before it emits usage.

## 5. Running it

```bash
cd a0/meter

# Everything behavioural, against a local fake upstream. No model call, no spend.
python3 selftest.py --out evidence          # 65/65 checks; writes evidence/*

# The same thing under pytest (unit + end-to-end + the raw TCP tap proof)
python3 -m pytest tests -q                  # 64 passed

# The wire-level framing proof, on its own (raw socket capture of the upstream leg)
python3 raw_tap.py --proof --out evidence --label after
# ... and the same proof against the pre-fix proxy, which must FAIL:
#   git show HEAD^:a0/meter/meter_proxy.py > /tmp/a0-old/meter_proxy.py
#   python3 raw_tap.py --proof --out /tmp --label before --proxy /tmp/a0-old/meter_proxy.py

# Independently re-derive an existing ledger
python3 verify_ledger.py evidence/ledger.jsonl
python3 verify_ledger.py evidence/ledger.jsonl --json
python3 verify_ledger.py evidence/live_ledger.jsonl        # the one real call

# One trivial REAL call through the proxy (spends a fraction of a cent)
export DEEPSEEK_API_KEY=$(awk -F: '/^deepseek:/{sub(/^deepseek:[ ]*/,""); print; exit}' ~/gptapi.md)
python3 live_check.py --out evidence/live              # GET /v1/models + one model call
python3 live_check.py --out evidence/live --chunked    # plus the chunked-framing path
```

`verify_ledger.py` is deliberately a separate program: a ledger that only its author can check is
not evidence. It recomputes every metered row's `ceq` from that row's own `usage`, asserts the
frozen key set and order, and asserts that unmetered rows carry no score.

`live_check.py` is deliberately a separate program too: it starts a fresh proxy pointed at
`https://api.deepseek.com` (no repair hop, no test double) and asserts from the ledger that each
model call was metered. `evidence/live_ledger.jsonl` is its output — three rows: the free
`GET /v1/models` (a catalogue reports no usage, so it is booked `unmetered` by design), and two
model calls, `Content-Length`-framed and chunked-framed, each `ceq: 53`, `unmetered: false` — and
`verify_ledger.py` re-derives all three.

## 6. What this does not establish

* **Behavioural coverage is still from a mock; only three live paths were proved.** S1–S19 run
  against `fake_upstream.py`, whose token figures are constants chosen by the test. That is the
  point — the meter must reproduce them exactly — but it means the suite proves *the meter*, not
  *DeepSeek's field names*. Three real calls are now proved end-to-end
  (`evidence/live_check.txt`): the no-body `GET /v1/models` path, a `Content-Length`-framed chat
  call, and a chunked-framed chat call, each `ceq: 53`. That closes the framing question for all
  three shapes on the upstream leg, and confirms the provider accepts the re-encoded chunked
  request. Streaming, Anthropic-shaped and Responses-shaped calls, 429s, and cache-hit accounting
  against a real provider are still unverified here.
* **Rate limits, 429s with usage, and provider-side truncation mid-tool-call are untested.** They
  land in the `unmetered` bucket with a reason, which is the designed behaviour, but it is
  unverified behaviour.
* **`credits` / `prompt_cache_write` semantics.** Only `hit`, `miss` and `completion` are
  modelled. If DeepSeek introduces a separately billed category it will appear as an unknown key
  in the sidecar's `raw_usage` and will *not* be charged — a gap, not a silent zero, but a gap.
* **The 0.02 and 4 weights are the interface's, not measured here.** This component implements
  the pricing model it is given.
* **The proxy is a trusted component.** Its correctness is the whole metering claim; there is no
  kernel-level enforcement that it is the only egress (the closure report's residual gap §7.1
  applies unchanged).
* **Port allocation is a harness responsibility.** Two campaigns must not be given the same port;
  the registry loader rejects duplicates within one registry file but cannot see other processes.
