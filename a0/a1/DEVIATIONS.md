# `a0/a1/DEVIATIONS.md` — every place this workstream interpreted or departed

Two of these are departures from another worker's component and one is a hole in
its own deliverable; all three are load-bearing for what the evidence above may be
used to claim. Nothing here is silent.

---

## D-A1-1 — T1's `EID*` document is authored **here**, not by the maxcut worker

**What.** `a0/tasks/maxcut/` ships a frozen evaluator (`e_star.py`,
`e_star_child.py`), a frozen suite with a manifest sha256 (`47324fcc…`) and a
frozen candidate set, but **no `EID*` document** (`ls` of that directory: no
`*.EID*.json`, no contract spec). `INTERFACE.md` §2/§5 make the evaluator's
identity a first-class object (`evaluator_source_sha256` on every Outcome; §11
says T1 "只需新增自己的 `EvaluatorSource` 记录"), and principle (i) requires it to
be frozen and recomputable — so *some* document has to exist.

**What was done.** `a0/a1/t1_eid.py` supplies a **spec**
(`a0/a1/T1.contract.json`) and has the contract owner's own
`a0/contract/evalcontract.py` build the five components and the combined
`EID*` (`a0/a1/T1-EID.json`). `EID*` = `cddfa64ead571bbb09daa458c6b514377fba32e62612f5c2e17a6b49b7a78ab1`.
`python3 a0/a1/t1_eid.py check` rebuilds everything from the repository and
cross-checks the `EvaluatorSource` records against what `E*` itself hashes
(`e_star.py digest`), so the two ways of naming the evaluator cannot drift.

**Why this is a deviation.** The document's *home* is arguably
`a0/tasks/maxcut/`; putting it there would write into another worker's directory.
The file declares `"produced_by": "a0/a1/t1_eid.py"` and this entry records the
choice. If the maxcut owner authors one, this should be replaced by theirs and the
`eid_star` value re-frozen — nothing else in `a0/a1/` needs to change, because the
path is a parameter (`--eid`, `A1Campaign.eid_path`).

**Not claimed:** that this is the *only* reasonable T1 identity. It is a
recomputable one, built from the frozen material, with the recipe published.

---

## D-A1-2 — the KAPSO arm still runs the **plumbing** task, not T1

**What.** `INTERFACE.md`'s CID rule ("if an object can change `P(Y|r)` it must be
inside `CID` or `AID_r`") makes `TaskID` a `CID` component: two arms measured on
different tasks cannot contribute to the same `Δ`. KAPSO's adapter
(`a0/runtimes/kapso/a0_adapter/`) is wired end to end for
`a0/tasks/circle-packing`: its `EidStar`, its registered evaluation tree
(`registered/kapso_eval.py`), its problem handler and its goal all describe
circle-packing. Retargeting it to T1 means a new registered evaluator tree, a new
`EidStar` binding and a new problem/goal — a workstream of its own.

**What was done instead.** The KAPSO wiring was implemented *task-agnostically*
and verified in two places:

* `probes/wiring_kapso.py` (model-free, 7/7): the injection, the class-triple
  derivation, the ordering rule and the attribution caveat;
* `probes/live_probe.py --arm kapso` (10/10): a real campaign with a real metered
  model turn, the same ordering test, and the meter evidence.

For the live arm the harness was pointed at the **plumbing** evaluator
(`--evaluator circle-packing`), which is the task KAPSO is actually wired to.

**Consequence, stated plainly.** The A1 skeleton's `CID` names `TaskID =
T1-maxcut`; the KAPSO arm cannot be placed in it until the retarget is done. So
the skeleton's dry-run is a proof of the *machinery*, not a licence to run the 8
campaigns with two arms. What the KAPSO work *does* establish is the thing that
was open: that an externally authored score can be landed after the session and
cannot be overridden by the session, with the class triple derived from the
runtime. All of that is task-independent.

**What would close it.** A `T1.contract.json`-equivalent spec for KAPSO's
registered tree, `common.EidStar` accepting a max-cut EID document, and a
`KapsoRuntime` mode whose candidate artifacts are T1 candidate directories.

---

## D-A1-3 — `a0/meter` drops every request body; a declared repair hop compensates

**The defect (reproduced, and it is not ours to fix).**
`a0/meter/meter_proxy.py` builds the upstream request with
`putrequest` / `putheader` / `endheaders(body)` (`:283-291`) after stripping
`Content-Length` as a hop-by-hop header (`HOP_BY_HOP`, `:103`). Python's
`http.client.endheaders(message_body)` does **not** re-add `Content-Length`, so
the upstream receives the body bytes with **no framing header at all**. Captured
verbatim by a raw TCP tap behind the proxy (`/tmp/a1/dbg/tap.bin` during the probe):

```
POST /v1/chat/completions HTTP/1.1
User-Agent: curl/8.22.0
Authorization: Bearer …
Content-Type: application/json
Host: 127.0.0.1:8898
Accept-Encoding: identity
<blank line>
{"model":"m1","messages":[…],"max_tokens":8}      <- unframed
```

A conforming HTTP/1.1 server reads no body. Every real DeepSeek call therefore
answers `400 Failed to parse the request body as JSON: EOF while parsing a value
at line 1 column 0` and is booked `unmetered` with reason
`unparseable_response_body` — i.e. **no campaign could ever have a real `CEq`,
which is precisely what §8's budget rests on.**

The component's own selftest cannot see this: `fake_upstream.py:239` reads the
body from `content-length`, gets 0 bytes, and the tests assert on the *response*
usage. 55/55 pass with every request body silently discarded.

**What was done, and why not an edit.** `a0/meter/` belongs to another worker and
`INTERFACE.md` forbids silent deviation, so the fix is a **declared compensating
hop** in this directory: `a0/a1/meter_body_repair.py` sits *below* the meter

```
runtime ─plaintext─▶ meter_proxy ─plaintext─▶ repair hop ─TLS─▶ api.deepseek.com
                      (books the row)          (restores framing)
```

It reads the unframed body (a short idle window delimits it — the proxy sends head
and body in one `sendall`), adds `Content-Length`, and forwards over
certificate-verified TLS to `api.deepseek.com` and nothing else. The meter still
sees the client's request and still books the row from the provider's response, so
the accounting authority is unchanged; the repair is recorded in every ledger
adjacent artifact (`meter.aid.json: body_repair`, and the hop's own
`repair.jsonl`), and `CID` carries a `harness.meter_body_repair` factor with the
hop's sha256.

Proof it works: `evidence/live_simpleloop.json` records one row with
`ceq = 3600` and one repair record
`{client_framing: "unframed_repaired", request_body_bytes: 2697, status: 200}`.

**Remove this hop** when `meter_proxy.py` re-adds the header (one line:
`conn.putheader("Content-Length", str(len(body)))`). At that point delete
`meter_body_repair.py`, `MeterBodyRepairHop`, the `use_body_repair` flag, the
`meter.aid.json` fragment and the `CID` factor — and re-freeze `CID`, because
`meter.upstream_base` moves back to `api.deepseek.com`.

**Not claimed:** that the hop is a *good* design. It is a declared workaround for
a defect in a component whose owner should fix it; it adds one process inside the
metre's trust boundary and it sees the credential that the meter already sees.

---

## D-A1-4 — `a0/a1/` follows the SimpleLoop adapter's convention for `--evaluator`

`evidence/*.json` names the evaluator per arm (`maxcut` for SimpleLoop,
`circle-packing` for KAPSO, per D-A1-2). The ABI, the token, the ledger and the
fail-closed ordering are identical for both; only the argv and the score field
differ (`EVALUATORS` in `eval_service.py`). This is an extension of §5, which
defines the Outcome for T1 only, and it exists so the KAPSO ordering test could be
run against a real runtime rather than a mock (D-A1-2).

---

## D-A1-5 — two small extensions inside the SimpleLoop adapter

Both are inside the wire-up, both are visible in the traces, neither changes a
selection rule:

1. `traces.failure_stage_for` maps **exit code 4 to `timeout`**. T1's `E*` gives a
   timeout its own exit code (`e_star.py:99`); the plumbing evaluator reports it as
   exit 3 with `failure.kind = runtime_budget_exceeded`. Same trace stage, one more
   reachable code. The frozen plumbing table is untouched.
2. `policy.scalar_of` reads a field from `outcome.fields` when the Outcome has
   one and from the Outcome's top level otherwise, and preserves the integer type
   of T1's `cut_edges` so the argmax is exact integer comparison rather than an
   IEEE-754 equality that merely happens to be exact. `load_policy` accepts
   `outcome.<name>` as well as `outcome.fields.<name>` for the same reason.

---

## Not a deviation, but worth recording

* **`deepseek-flash` answers inside `reasoning_content`** on the DeepSeek chat
  face, leaving `content` empty (measured: `content: ""`, `finish_reason: length`,
  the text in `reasoning_content`). The model lane reads both and records which one
  carried the answer (`solvers.py`, `ModelSolver._chat`). A lane that read only
  `content` would look like a model that never answers.
* **`--meter-token=<value>` is passed with `=`** in the probes: a
  `secrets.token_urlsafe` token may begin with `-`, which argparse would then read
  as another option (measured: `error: argument --meter-token: expected one
  argument`).
* **The live SimpleLoop arm's model proposal is degenerate** (`ds_i001` scores
  `cut_edges = 0`, i.e. a trivial assignment). The probe measures the wiring, not
  the model's search skill; the harness's number for that candidate still enters
  the selection (`132 > 0`, the baseline stays champion).
