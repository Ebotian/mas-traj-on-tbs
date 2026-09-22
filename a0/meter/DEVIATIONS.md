# Deviations from `a0/tasks/maxcut/INTERFACE.md`

Owner: the metering worker (`a0/meter/`). `INTERFACE.md` is the binding authority and is **not**
edited by this directory. This file records (a) where the implementation had to fill a gap the
interface leaves open, (b) the one place where the interface's own text is not self-consistent, and
(c) the defect this directory found in itself and fixed, because a metering component that cannot
frame its own requests has no numbers to report.

## A. Behavioural deviations: none

Every behaviour §8 specifies is implemented as specified:

* the ledger row has exactly the key set, key order and `schema` string of §8 — enforced by
  `Ledger._check_row`, so a row that does not match is never written;
* `CEq = miss + floor(hit*2/100) + 4*completion` in integers only;
* a successful response without usage is `unmetered: true` and `ceq: null`, never an estimate;
* plaintext HTTP is terminated locally and the upstream leg is TLS to the allowlisted host;
* `HTTPS_PROXY`/CONNECT is not a metering path (it is refused outright);
* `meter.mode = plaintext_base_url` and `meter.allowlist = [api.deepseek.com]` are emitted in
  `meter.aid.json`, ready for `AID_r` as §8 requires.

## B. Recorded extensions and gap-fills

These are things §8 does not specify. Each is additive: none changes the meaning of a field §8
does define, and none can make an unmetered call look metered.

1. **Refusals and transport failures also produce ledger rows.**
   §8 says "one row per upstream call"; a policy refusal is not an upstream call.
   *Justification:* requirement 3 of this workstream — "anything else is refused **and recorded**"
   — and the general principle that the ledger should be a complete record of *attempted* calls,
   not only of those that reached the provider. Such rows are `unmetered: true, ceq: null`, so
   they can never contribute to a budget; `endpoint` and `reason` distinguish them.

2. **`usage: null` on unmetered rows.** §8 shows only the metered case. Null is the honest value
   for "not measured" and matches `ceq: null`.

3. **`reason: null` is required on metered rows.** §8's example shows it. A consequence: an
   annotation about a metered call (e.g. "the tail of this stream was truncated but usage had
   already arrived") is *not* put in the row — it goes to the diagnostic sidecar
   (`--events`). Enforced by `verify_row`.

4. **CONNECT is answered `405`.** §8 says `HTTPS_PROXY`/CONNECT is not the metering authority;
   refusing rather than tunnelling is the fail-closed reading. The alternative — tunnelling and
   booking an unmetered row — would leave a channel whose usage is permanently invisible.

5. **An optional `X-A0-Meter-Token` header per campaign.** Not in §8. It is an *additional*
   refusal trigger; attribution itself is the port. A wrong token causes a refusal recorded
   against the port's own campaign and never a re-attribution.

6. **`--upstream-base` is configurable** (default `https://api.deepseek.com`, the allowlisted
   host). The default is what production runs; the flag exists so the selftest can point the
   proxy at a local fake upstream and prove the mechanism without spending money. The weakening
   this could introduce is closed by a startup check: the process refuses to start unless
   `--upstream-base`'s host is in `--allowlist`, and the allowlist is what `meter.aid.json`
   declares. `--upstream-insecure` exists for the same testing reason and logs a loud warning
   when used; the selftest does **not** use it (it verifies a real throwaway CA).

7. **`stream` is true when the request asked for streaming or the response is `text/event-stream`.**
   §8 does not define the field's derivation. Documented so two readers cannot disagree.

8. **Per-campaign ports are a harness allocation.** The registry loader rejects duplicate ports
   within one registry, but A1 must ensure a campaign's port is free when it starts the proxy.

9. **Outbound framing is re-derived from the body actually held.** §8 says nothing about the
   request the proxy builds; it only fixes the *response-side* accounting. Decision: the client's
   framing *headers* are never forwarded, and the framing *mechanism* is preserved — a chunked
   client request is re-encoded as chunked, everything else with a body is sent with
   `Content-Length: <len(body)>`. When a client sends both `Content-Length` and
   `Transfer-Encoding: chunked` (a request-smuggling shape), chunked wins and the client's length
   is dropped, per RFC 9112 §6.1. The alternative — always sending `Content-Length` — would also
   be conforming, but it would make the chunked path untested and would silently rewrite a client's
   transfer choice. Nothing about the *numbers* is inherited from the client.

10. **A body whose extent cannot be established is refused, not guessed at.** Not specified by §8,
    which assumes well-formed clients. Decision: `request_body_unframed` (bytes with neither
    `Content-Length` nor `Transfer-Encoding: chunked`), `request_body_truncated` (declared length
    or chunked terminator never arrived), `request_body_length_unparsable`, `request_body_too_large`
    → `400`, and the refusal is booked as an unmetered row like every other refusal (B1). The
    alternative — forwarding whatever arrived, with a length the proxy invents — is a fabricated
    body, and a fabricated body is a mis-metered one. The refusal is loud (`proxy.console.txt`,
    `events.jsonl`, a ledger row), which is what makes it safe: no legitimate path here sends an
    undelimited body, and if one ever does it will be seen immediately rather than counted wrongly.

11. **`read_request_body` returns `(body, framing)`.** An internal signature change, not visible in
    the ledger, the AID fragment, or the row schema. `forward(..., client_framing)` takes the same
    value. Nothing outside `meter_proxy.py` calls either function (checked: only `serve_conn` →
    `handle_request` does).

## C. Defect found and fixed in this directory: the upstream leg carried no framing

**The defect.** `Content-Length` sat in `HOP_BY_HOP`, so `forward()` stripped it, and
`http.client.endheaders(body)` writes the head and then the body without adding one. The upstream
therefore received:

```
POST /v1/chat/completions HTTP/1.1
Content-Type: application/json
Authorization: Bearer …
Host: 127.0.0.1:36975
Accept-Encoding: identity
<blank line>
{"model": "deepseek-flash", ...}          <- 98 bytes, unframed
```

A conforming server reads no body, so `api.deepseek.com` answered
`400 Failed to parse the request body as JSON: EOF while parsing a value at line 1 column 0`, every
real call was booked `unmetered`, and §8's `CEq` could not have carried a real number for any
campaign. Reproduced on the wire, before the fix: `evidence/framing_before.txt` (proxy sha256
`48c7129b…`), three client shapes — `Content-Length`, chunked, unframed — all arriving with
`framing=none`, and all three answered `400` by a tap that frames its reads like a real server.

**Why the component's own 55/55 was blind to it.** `fake_upstream.py` read its body length from
`content-length`, got zero bytes, and answered from the scenario's defaults; the tests asserted on
responses. In the committed pre-fix evidence, all 20 recorded upstream requests have
`"model": null, "stream": null` — the upstream never saw a body byte, and no check looked.

**The fix.** (i) `Content-Length` is no longer treated as hop-by-hop; framing headers are stripped
from the client's list and re-stated by `forward()` from `len(body)`. (ii) A chunked client body is
re-encoded with `encode_chunked=True`. (iii) The chunked read no longer ends when the buffer merely
*ends with* `0\r\n\r\n` — a chunk's data can end that way, and the truncated body would then have
been framed as if it were whole; `chunked_body_complete` walks the sizes. (iv) An undelimitable body
is refused (B10).

**Evidence.**
* `evidence/framing_after.txt` / `.json` — the same three shapes after the fix: `Content-Length: 98`
  for shape A, `Transfer-Encoding: chunked` with the identical decoded body for shape B, both
  `200` and both metered; shape C refused locally with reason `request_body_unframed` and nothing
  reaching the upstream. Proxy sha256 `0aa928be…`, recorded in the capture itself.
* `evidence/selftest_on_prefix_proxy.txt` — the new selftest run against the pre-fix revision:
  **36/65, exit 1**, the request-side checks failing as they must.
* `evidence/live_check.txt` + `evidence/live_ledger.jsonl` — real calls to
  `https://api.deepseek.com` through this proxy (no repair hop, no test double): the no-body
  `GET /v1/models` path (200, booked `unmetered` because a catalogue reports no usage — by design),
  a `Content-Length`-framed chat call and a chunked-framed chat call, both `HTTP 200`,
  `ceq: 53 = 37 + 0 + 4×4`, `unmetered: false`; `verify_ledger.py` re-derives all three rows
  (exit 0). The chunked call also answers the question the fix had to guess at: the provider
  accepts a re-encoded chunked request body, so preserving the client's framing choice is safe.
* `python3 -m pytest tests -q` → 65 passed, including the 17 framing tests in
  `tests/test_meter_framing.py`.

**Audit: which other checks were mock-shaped rather than wire-shaped.** The same class of defect —
the mock's shape differing from a real provider's — was looked for across the component:

*Fixed:*
1. The mock framed its reads from `content-length` alone, so a chunked or unframed request silently
   became an empty body *and was still answered `200`*. It now frames per RFC 9112 (`Content-Length`
   or chunked), and answers a body it could not read, could not parse, or was sent no credential
   for exactly as the real endpoint does (`400` with DeepSeek's wording; `401`).
2. It recorded almost nothing about the request, so no request-side assertion was possible: under
   the defect its log said `"model": null, "stream": null` for all 20 requests and nothing looked.
   It now records `framing`, `content_length_header`, `transfer_encoding_header`, `declared_length`,
   `chunked_complete`, `framing_error`, `body_bytes`, `body_sha256`, `body_json_ok`.
3. It served any caller. The real endpoint requires a key; a keyless request is now `401`. The
   selftest's streaming raw-socket client was itself sending no credential (it was the only client
   that did not), and was fixed; S18f audits that every forwarded request carried one.
4. Every check in the suite asserted on *responses*, or on the proxy's own self-report. S18a–g now
   assert on the upstream's record of what it received (framing header present, declared length
   equal to bytes received, body sha256 equal to the client's, body parseable) over the whole run,
   and S19 proves an undelimitable body never reaches the upstream at all.
5. `chunked_body_complete` replaces an `endswith(b"0\r\n\r\n")` heuristic that a chunk's *data*
   could satisfy. The corpus test in `tests/test_meter_framing.py` pins it.

*Flagged, deliberately not changed:*
6. The mock picks its answer from `X-Fake-Scenario` and never validates request *semantics* — an
   unknown model name, a malformed `messages` array, an unsupported parameter. A real provider
   `400`s those. Left alone because the meter must not depend on request semantics at all, and
   S18c already asserts that the model the upstream parsed is the model the client sent; a
   semantic validator inside the mock would give a meter that mangles the model field somewhere to
   hide behind a scenario `200`.
7. The mock always answers `Connection: close`, so client keep-alive reuse is never exercised; the
   proxy declares `Connection: close` to its client and opens a fresh upstream connection per call,
   so no conforming client can reuse the proxy's socket, and the ledger has one row per call either
   way. Untested rather than wrong — but it means the ledger has never been exercised by a client
   that pipelines two requests on one connection, which the conformance gate might want to know.
   (Because the proxy closes each client connection after one request, such a client would have its
   second request fail, not be silently unlogged.)
8. The mock never compresses a response, so the `content_encoding_<enc>_not_parseable` path is
   exercised only by construction. Separately, the upstream leg pays a fresh TCP+TLS handshake per
   call: `forward()` builds a new connection and does not reuse it. That costs wall-clock, not
   `CEq`, so it belongs to §9's calibration of `q_r` rather than to the budget, and it is raised
   here rather than fixed because connection reuse would add a failure mode to the leg whose
   correctness is the whole point.
9. **Not a mock issue, but the same "shape of a real peer" class: the proxy never answers
   `Expect: 100-continue`.** It terminates HTTP, so a client that offers `Expect: 100-continue`
   and waits for the interim response before sending its body gets no interim response — it waits
   for the client's own timeout (curl: 1 s, then it sends anyway) before the proxy ever sees the
   body. No client in this project's wiring sends it (the OpenAI/httpx clients used by both arms do
   not; curl only adds it above ~1 KB of body), so nothing is broken today. Flagged, not fixed:
   answering it means an interim write on the client socket before the routing decisions are
   finished, which is a change to the request path this fix did not need.
10. **Note on the still-installed repair hop** (`a0/a1/meter_body_repair.py`, another workstream's
   file, not touched here). With this fix the meter sends framed requests, and the hop handles
   `Content-Length` framing correctly, so the wiring keeps working. One shape would not: if a
   client sent the meter a chunked body, the meter now forwards it chunked and the hop would
   re-label those chunk-framed bytes with a `Content-Length` — corrupting the body. No client in
   the wiring sends chunked; deleting the hop (recommended, see the consequence below) removes the
   hazard entirely.

**Consequence for `a0/a1/`.** The declared compensating hop `a0/a1/meter_body_repair.py` and the
`CID` factor `harness.meter_body_repair` existed only to restore this framing one hop below the
meter. They can be deleted and `CID` re-frozen without them. This directory does not delete them —
that file belongs to another workstream — and the coordinator has been told.


## D. Defect found in `INTERFACE.md` §8 — reported, not silently worked around

The worked ledger row in §8 is **not arithmetically consistent with the formula stated in the
same section**:

```
usage: {"prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 20153, "completion_tokens": 312}
ceq:   21313

formula: 0 + floor(0*2/100) + 4*312 = 1248
        20153 + 1248                = 21401          <- not 21313
```

`21313` is exactly `20065 + 1248`: the row appears to have been copied from a real call in which
`prompt_cache_miss_tokens` was `20065`, and then the `usage` block and the `ceq` drifted apart.
Alternatively the `ceq` is stale. Either way the two cannot both be right.

**Resolution taken here:** the **formula** is authoritative, because it is the stated definition
and the only thing that can be recomputed from a row's own data. A row copied verbatim out of
§8 will be *rejected* by `verify_ledger.py`, and that is the correct behaviour — a `ceq` that
cannot be re-derived from its own `usage` is precisely the kind of self-reported number this
component exists to eliminate.

This is pinned as an executable test so it cannot be forgotten:
`a0/meter/tests/test_meter_core.py::TestInterfaceExampleRowIsInconsistent` (3 assertions).

**Action requested of the interface owner:** correct the example to either
`prompt_cache_miss_tokens: 20065, ceq: 21313` or `prompt_cache_miss_tokens: 20153, ceq: 21401`.
This directory will not edit `INTERFACE.md`. The same class of defect — two artifacts of the same
fact disagreeing by a small amount — is the "1-ULP disagreement" failure the project has already
paid for once, so it is worth fixing at the source rather than only in the checker.
