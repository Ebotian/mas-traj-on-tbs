# Deviations from `a0/tasks/maxcut/INTERFACE.md`

Owner: the metering worker (`a0/meter/`). `INTERFACE.md` is the binding authority and is **not**
edited by this directory. This file records (a) where the implementation had to fill a gap the
interface leaves open, and (b) the one place where the interface's own text is not self-consistent.

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

## C. Defect found in `INTERFACE.md` §8 — reported, not silently worked around

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
