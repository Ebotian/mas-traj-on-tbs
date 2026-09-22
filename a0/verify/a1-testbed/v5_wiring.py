#!/usr/bin/env python3
"""Adversarial re-derivation of the A1 wiring claims (assignment item 5).

From recorded state (a0/a1/evidence/*.json) plus one live harness run of my own
through a0/a1/eval_service.py.  Zero model spend: the live run evaluates a frozen
C*(T1) candidate through E*, which costs nothing.

Claims attacked:
  C5.1 the score of record equals the harness-supplied value, for both arms
  C5.2 a session-printed manifest line cannot override it
  C5.3 no unmetered model call is possible
  C5.4 (falsification) hand the harness a value E* could not produce and see
       whether anything in the pipeline notices
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
A1 = REPO / "a0/a1"
EV = A1 / "evidence"
MX = REPO / "a0/tasks/maxcut"
WORK = pathlib.Path(tempfile.mkdtemp(prefix="a1testbed-wiring-"))
PY = sys.executable

problems: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
    if not cond:
        problems.append(msg)


def load(name: str) -> dict:
    return json.loads((EV / name).read_bytes())


def e_star_value(candidate: pathlib.Path, graph: pathlib.Path) -> int:
    out = WORK / f"es-{candidate.name}.json"
    subprocess.run([PY, str(MX / "e_star.py"), "evaluate", "--candidate", str(candidate),
                    "--graph", str(graph), "--seed", "1337", "--timeout", "10", "--out", str(out)],
                   capture_output=True, check=True)
    return json.loads(out.read_text())["cut_edges"]


def main() -> int:
    graph = MX / "suite/dev/G_dev_0001.json"
    edges_total = len(json.loads(graph.read_bytes())["edges"])

    print("== C5.1a SimpleLoop: the score of record is the harness's, and the harness's is E*'s ==")
    w = load("wiring_simpleloop.json")
    truth = w["truth_vs_handed"]
    check(w["verdict"] == "pass" and all(w["checks"].values()),
          f"recorded verdict={w['verdict']}, {len(w['checks'])}/{len(w['checks'])} checks true")
    # the honest run's numbers, re-derived from E* here
    mine = {"c02_ok_low_baseline": e_star_value(MX / "candidates/c02_ok_low_baseline", graph)}
    check(mine["c02_ok_low_baseline"] == truth["true"]["c02_ok_low_baseline"] == 132,
          f"E* now says c02={mine['c02_ok_low_baseline']} and the record says {truth['true']['c02_ok_low_baseline']}")
    honest = w["runs"]["honest_a"]
    check(honest["champion"] == "proposal_i1" and honest["champion_scalar"] == 207,
          f"honest run champion={honest['champion']} scalar={honest['champion_scalar']} "
          f"(= the true best, {truth['true_best']}={truth['true']['proposal_i1']})")
    check([h["search_signal"] for h in honest["history"]] == list(truth["true"].values())
          or [h["search_signal"] for h in honest["history"]] == [truth["true"][h["candidate_id"]] for h in honest["history"]],
          f"every search_signal in the trace equals the E* value: "
          f"{[(h['candidate_id'], h['search_signal']) for h in honest['history']]}")
    ledger = w["honest_ledger"]
    check(all(r["harness_supplied"] and r["handed_value"] == r["true_value"] and not r["override_applied"]
              for r in ledger),
          f"the honest harness ledger records handed_value == true_value on all {len(ledger)} rows")

    print("\n== C5.1b the override run: the runtime consumes, it does not measure ==")
    check(truth["handed"] == {"c02_ok_low_baseline": 132, "proposal_i1": 1, "proposal_i2": 9999}
          and truth["true"] == {"c02_ok_low_baseline": 132, "proposal_i1": 207, "proposal_i2": 0},
          f"handed {truth['handed']} vs true {truth['true']}")
    check(truth["handed_best"] == "proposal_i2" and truth["true_best"] == "proposal_i1",
          "the override inverts the true ranking and the harness's ranking is the recorded one")
    lying = w["runs"]["lying"]
    check(lying["champion"] == "proposal_i2" and lying["champion_scalar"] == 9999,
          f"override run champion={lying['champion']} scalar={lying['champion_scalar']}")
    check(9999 > edges_total,
          f"the handed 9999 is a number E* could not produce for this graph (|E|={edges_total})")

    print("\n== C5.2 KAPSO: the harness's line lands last and the session cannot override it ==")
    k = load("wiring_kapso.json")
    check(k["verdict"] == "pass" and all(k["checks"].values()),
          f"recorded verdict={k['verdict']}, {len(k['checks'])}/{len(k['checks'])} checks true")
    lk = load("live_kapso.json")
    st = lk["arm_state"]
    check(st["harness_score"] == st["score_of_record"],
          f"score_of_record={st['score_of_record']} == harness_score={st['harness_score']}")
    claimed = st.get("session_claimed_score")
    check(claimed is not None and claimed != st["score_of_record"],
          f"the session claimed {claimed} and the record kept {st['score_of_record']}")
    check(st["last_line_is_the_harness_s"] is True and st["manifest_line_count"] == 3,
          f"{st['manifest_line_count']} manifest lines, the harness's is last")
    attempts = st["evaluation_attempts"]
    check(attempts[0]["evaluator_id"] == st["registered_evaluator_id"],
          "the runtime files the harness's number under the registered evaluator's id "
          "(the attribution caveat, reproduced)")
    check("KAPSO cannot distinguish" in k["attribution_caveat"]
          and "evaluator-realisation evidence" in k["attribution_caveat"],
          "the artifact states that caveat itself")

    print("\n== C5.1c the live runs' scores and CEq, from the recorded ledgers ==")
    for name, arm in (("live_simpleloop.json", "simpleloop"), ("live_kapso.json", "kapso")):
        doc = load(name)
        st = doc["arm_state"]
        rows = doc["meter_ledger_rows"]
        my_total = sum(r["ceq"] for r in rows if not r["unmetered"])
        refigured = []
        for r in rows:
            if r["unmetered"]:
                refigured.append((r["ceq"] is None, r["usage"] is None, bool(r["reason"])))
                continue
            u = r["usage"]
            refigured.append((r["ceq"] == u["prompt_cache_miss_tokens"]
                              + (u["prompt_cache_hit_tokens"] * 2) // 100 + 4 * u["completion_tokens"],))
        print(f"    {arm}: score_of_record={st['score_of_record']} harness_score={st.get('harness_score', st['score_of_record'])} "
              f"CEq(mine)={my_total} CEq(recorded summary)={doc['meter_summary'].get('ceq')} "
              f"rows={len(rows)} verify_ledger_rc={doc['meter_verify_ledger']['returncode']}")
        check(my_total == doc["meter_summary"]["ceq"] and len(rows) == doc["meter_summary"]["rows"],
              f"{arm}: my CEq total {my_total} over {len(rows)} row(s) == the recorded summary "
              f"{doc['meter_summary']['ceq']} over {doc['meter_summary']['rows']} row(s)")
        vl = doc["meter_verify_ledger"]
        vl_doc = json.loads(vl["stdout"]) if vl.get("stdout", "").strip().startswith("{") else {}
        check(vl["returncode"] == 0 and vl_doc.get("failures") == [],
              f"{arm}: the meter's own verify_ledger.py exits 0 with no failures on this ledger "
              f"(ceq_total={vl_doc.get('ceq_total')})")
        probe = doc["topology_probe"]
        literals = {k: v for k, v in probe.items() if not k.startswith("_") and k != "meter_loopback"}
        check(all(v.startswith("BLOCKED") for v in literals.values())
              and probe.get("meter_loopback") == "REACHED"
              and probe.get("_meter_reachable") is True
              and probe.get("_negative_controls_blocked") is True,
              f"{arm}: inside the namespace every direct destination is BLOCKED {literals} and the "
              f"campaign's own meter is REACHED")
        check(all(all(t) for t in refigured), f"{arm}: every row's ceq re-derives from its own usage")
        score_src = st.get("score_source") or "harness"
        check(score_src == "harness" and st["score_of_record"] in
              [e.get("handed_value") for e in doc["harness_ledger_rows"]],
              f"{arm}: score_source={score_src} and the score appears as a harness handed_value")

    print("\n== C5.3 the controls: what 'no unmetered call' is enforced by ==")
    c = load("live_controls.json")
    check(all(c["checks"].values()), f"{len(c['checks'])}/{len(c['checks'])} control checks true: {list(c['checks'])}")
    check(str(c["direct_attempt_inside_namespace"]).startswith("BLOCKED"),
          f"direct egress from inside the namespace: {c['direct_attempt_inside_namespace']}")
    check(c["call_without_the_campaign_token"]["refused"] is True,
          "a call without the campaign token is refused")
    check(c["induced_missing_usage"]["budget_stopped_because"] == "budget_exhausted:unmetered_model_call",
          "an unobservable usage gap stops the campaign instead of being extrapolated")
    skel = load("skeleton_dryrun.json")
    print(f"    skeleton dry-run: verdict={skel.get('verdict')}, "
          f"{sum(1 for v in skel.get('checks', {}).values() if v)}/{len(skel.get('checks', {}))} checks")

    print("\n== C5.4 falsification: an impossible value through the live harness ==")
    root = WORK / "harness"
    root.mkdir(parents=True, exist_ok=True)
    request = {
        "schema": "a0.a1.eval_request/v1",
        "request_id": "probe.i0000.c02_ok_low_baseline",
        "campaign_id": "C_probe", "arm_id": "A_probe",
        "candidate_id": "c02_ok_low_baseline",
        "candidate_path": str(MX / "candidates/c02_ok_low_baseline"),
        "graph_path": str(graph), "seed": 1337, "timeout_s": 10, "iteration": 0,
    }
    req_path = WORK / "request.json"
    req_path.write_text(json.dumps(request))
    base = [PY, str(A1 / "eval_service.py"), "evaluate", "--root", str(root),
            "--campaign-id", "C_probe", "--arm-id", "A_probe", "--harness-run-id", "probe",
            "--nonce", "0123456789abcdef"]
    honest = subprocess.run(base + ["--request", str(req_path)], capture_output=True, text=True)
    hdoc = json.loads(honest.stdout)
    check(hdoc["value"] == 132 and hdoc["true_value"] == 132 and hdoc["override_applied"] is False,
          f"honest service run: value={hdoc['value']} true_value={hdoc['true_value']} "
          f"harness_supplied={hdoc['harness_supplied']}")
    override = WORK / "override.json"
    override.write_text(json.dumps({"c02_ok_low_baseline": 9999}))
    lying = subprocess.run(base + ["--request", str(req_path), "--override", str(override)],
                           capture_output=True, text=True)
    ldoc = json.loads(lying.stdout)
    print(f"    override run: value={ldoc['value']} true_value={ldoc['true_value']} "
          f"override_applied={ldoc['override_applied']} status={ldoc['status']}")
    check(ldoc["value"] == 9999 > edges_total and ldoc["true_value"] == 132,
          "the service publishes an impossible value with the true value beside it (rc="
          f"{lying.returncode})")
    outcome = ldoc["outcome"]
    check(outcome.get("harness_authored") is True and "canonical_digest" not in outcome,
          "the handed Outcome says it is harness-authored and drops E*'s canonical_digest")
    ledger = [json.loads(line) for line in (root / "ledger.jsonl").read_text().splitlines()]
    check(ledger[-1]["handed_value"] == 9999 and ledger[-1]["true_value"] == 132
          and ledger[-1]["override_applied"] is True,
          "the harness ledger keeps both numbers on the same row")

    # Does any frozen validator reject a score the task could not produce?  The
    # trace contract is the one validator that sees the number.
    fixture = REPO / "a0/contract/fixtures/traces/good.jsonl"
    events = [json.loads(line) for line in fixture.read_text().splitlines() if line.strip()]
    control = WORK / "trace_control.jsonl"
    control.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    ctl = subprocess.run([PY, str(REPO / "a0/contract/trace_validate.py"), "validate", "--trace", str(control)],
                         capture_output=True, text=True)
    doctored = []
    for e in events:
        e = json.loads(json.dumps(e))
        if e.get("trace") == "score":
            e["outcome"]["fields"]["coverage"] = 9999.0
            e["search_signal"] = 9999.0
            if isinstance(e.get("fr"), dict) and "scalar" in e["fr"]:
                e["fr"]["scalar"] = 9999.0
        doctored.append(e)
    trace = WORK / "trace_impossible.jsonl"
    trace.write_text("\n".join(json.dumps(e) for e in doctored) + "\n")
    tv = subprocess.run([PY, str(REPO / "a0/contract/trace_validate.py"), "validate", "--trace", str(trace)],
                        capture_output=True, text=True)
    print(f"    fixture good.jsonl: rc={ctl.returncode} (control) | same fixture with every score set to "
          f"9999: rc={tv.returncode} ({(tv.stdout or tv.stderr).strip().splitlines()[-1][:90]})")
    check(ctl.returncode == 0 and tv.returncode == 0,
          "the frozen trace contract validates a real trace carrying an impossible score: it bounds no "
          "task quantity, so 'the number is the harness's' is enforced but 'the number is one E* could "
          "produce' is not")
    # the gate is where the number finally meets |E|; show what it computes, by hand
    b, t = 132, 224
    delta = (9999 - b) / edges_total
    rho = (t - 9999) / (t - b)
    check(delta > 1.0 or rho < 0.0,
          f"gate_config's own definitions applied to the handed value give Δ={delta:.4f} (>1) and "
          f"ρ={rho:.4f} (<0) -- no guard rejects either; the Δ gate would 'pass'")

    print("\n== C5.5 the candidate child the harness spawns is NOT in the closed topology ==")
    argv = json.loads((A1 / "eval_service.py").read_text().split("EVALUATORS = ")[1].split("\n}")[0]
                      .join(["", ""]) + "{}") if False else None  # not parsed here; see grep evidence
    text = (A1 / "eval_service.py").read_text()
    check("--net-isolate" not in text,
          "eval_service.py's frozen maxcut argv never passes --net-isolate to E*")
    egress_cand = pathlib.Path(__file__).resolve().parent / "cand_egress"
    egress_cand.mkdir(exist_ok=True)
    (egress_cand / "solution.py").write_text(
        "import argparse,json,socket\n"
        "p=argparse.ArgumentParser();p.add_argument('--graph');p.add_argument('--out');p.add_argument('--seed',type=int)\n"
        "a=p.parse_args();result={}\n"
        "for host,port in (('api.deepseek.com',443),('1.1.1.1',443)):\n"
        "    try:\n"
        "        s=socket.create_connection((host,port),timeout=3);s.close();result[host]='open'\n"
        "    except Exception as exc: result[host]=type(exc).__name__\n"
        "open('/tmp/a1testbed-wiring-egress.json','w').write(json.dumps(result,sort_keys=True))\n"
        "doc=json.load(open(a.graph));open(a.out,'w').write(json.dumps({'schema':'a0.maxcut.partition/v1',"
        "'graph_id':doc['graph_id'],'assignment':[i%2 for i in range(doc['n'])]},sort_keys=True,separators=(',',':')))\n"
    )
    request2 = dict(request)
    request2["request_id"] = "probe.i0001.cand_egress"
    request2["candidate_id"] = "cand_egress"
    request2["candidate_path"] = str(egress_cand)
    req2 = WORK / "request2.json"
    req2.write_text(json.dumps(request2))
    pathlib.Path("/tmp/a1testbed-wiring-egress.json").unlink(missing_ok=True)
    subprocess.run(base + ["--request", str(req2)], capture_output=True, text=True)
    findings = []
    if pathlib.Path("/tmp/a1testbed-wiring-egress.json").is_file():
        egress = json.loads(pathlib.Path("/tmp/a1testbed-wiring-egress.json").read_text())
        print(f"    egress from a candidate child spawned by the harness service: {egress}")
        key = pathlib.Path.home() / "gptapi.md"
        print(f"    the credential the runtime uses exists as a readable file for that same user: "
              f"{key} exists={key.exists()} (contents NOT read)")
        if egress.get("api.deepseek.com") == "open":
            findings.append(
                "the connected-topology enforcement does not cover the candidate lane: the child E* "
                "spawns (eval_service's frozen maxcut argv has no --net-isolate) reaches "
                "api.deepseek.com:443 directly, and the provider credential is a readable file for the "
                "same user, so a runtime could put model spend inside a candidate the harness evaluates "
                "outside the campaign budget. Claim 8 holds for the arm (inside `unshare -rn`) but not "
                "for the candidates the harness runs on its behalf.")
        check(egress.get("1.1.1.1") != "open",
              "the child cannot reach an arbitrary IP literal (so the egress is not a general hole, "
              "it is the provider's address specifically)")
    else:
        check(False, "no egress report: the candidate child did not run")

    print("\n== C5.6 the one command the A1 report names: does it still pass? ==")
    cid = A1 / "declarations/CID.json"
    cid_before = hashlib.sha256(cid.read_bytes()).hexdigest()
    v = subprocess.run([PY, str(A1 / "verify.py")], capture_output=True, text=True, timeout=1800)
    cid_after = hashlib.sha256(cid.read_bytes()).hexdigest()
    if cid_before != cid_after:
        print(f"    NOTE: a0/a1/verify.py is not read-only: its declarations step rewrote "
              f"{cid.relative_to(REPO)} ({cid_before[:12]} -> {cid_after[:12]}). Restore it with "
              f"`git checkout -- {cid.relative_to(REPO)}` if the tree must stay as found.")
    vdoc = json.loads(v.stdout) if v.stdout.strip().startswith("{") else {}
    print(f"    a0/a1/verify.py rc={v.returncode} verdict={vdoc.get('verdict')} steps={vdoc.get('steps')}")
    check(vdoc.get("verdict") == "fail" or v.returncode == 0,
          f"verify.py's own exit code agrees with its verdict (rc={v.returncode}, verdict={vdoc.get('verdict')})")
    eid = subprocess.run([PY, str(A1 / "t1_eid.py"), "check"], capture_output=True, text=True)
    edoc = json.loads(eid.stdout) if eid.stdout.strip().startswith("{") else {}
    disk = hashlib.sha256((MX / "e_star.py").read_bytes()).hexdigest()
    contract = json.loads((A1 / "T1.contract.json").read_bytes())
    status = json.loads(subprocess.run([PY, str(MX / "e_star.py"), "digest"], capture_output=True,
                                       text=True).stdout or "{}")
    print(f"    EID* on disk {str(edoc.get('on_disk'))[:16]} vs recomputed {str(edoc.get('recomputed'))[:16]} "
          f"({edoc.get('reason')}); e_star.py now {disk[:16]}; "
          f"E*'s own evaluator_source_sha256 now {str(status.get('evaluator_source_sha256'))[:16]}")
    print(f"    A1 evidence recorded against evaluator_source_sha256 "
          f"{sorted({r.get('evaluator_source_sha256', '')[:16] for r in w['honest_ledger']})}")
    check(edoc.get("pass") is not None,
          "t1_eid.py check reports its drift verdict in the expected shape")
    if not edoc.get("pass"):
        findings.append(
            f"the A1 tree is no longer self-consistent after the T1 fix: T1-EID.json holds "
            f"{str(edoc.get('on_disk'))[:16]} while recomputation from the current e_star.py gives "
            f"{str(edoc.get('recomputed'))[:16]}, so a0/a1/verify.py returns rc={v.returncode} with "
            f"steps={vdoc.get('steps')} -- t1-eid, wiring-simpleloop and skeleton-dryrun fail, and the "
            f"SimpleLoop adapter refuses to run with 'contract mismatch: evalcontract.py verify reported "
            f"drift'. The recorded A1 evidence was produced against evaluator_source_sha256 "
            f"{sorted({r.get('evaluator_source_sha256', '')[:16] for r in w['honest_ledger']})} (pre-fix "
            f"E*), so 'verify.py 6/6' describes the tree before 6dd717c2, not the tree that was committed.")

    print(f"\nPROBLEMS (probe failures): {len(problems)}")
    for p in problems:
        print("  -", p)
    print(f"FINDINGS (claims that did not survive): {len(findings)}")
    for f in findings:
        print("  !", f)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
