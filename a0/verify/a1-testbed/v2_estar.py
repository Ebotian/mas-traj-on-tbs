#!/usr/bin/env python3
"""Adversarial re-derivation of the E* claims (assignment item 2).

Everything here runs the real CLI as a subprocess and reads the artifacts it
writes.  Nothing imports E* and trusts an internal function; the unit of
evidence is the command + its stdout/stderr + the JSON on disk.

Claims attacked:
  C2.1 six required properties: cwd/PATH independence, determinism, failure
       semantics (cut_edges null, never 0), network independence, no
       credential/proxy leakage into the child, exact rational aggregation
  C2.2 the interpreter-prefix launch makes the executable bit irrelevant
       (byte-identical candidates, different modes)
  C2.3 test_candidate_staging.py actually fails against the pre-fix E*
  C2.4 rows of conformance.expected.json reproduce by hand
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
MX = REPO / "a0/tasks/maxcut"
E_STAR = MX / "e_star.py"
PY = "/usr/bin/python3.14"
GRAPH = MX / "suite/dev/G_dev_0001.json"
CAND_OK = MX / "candidates/c01_ok_high_pc"
WORK = pathlib.Path(tempfile.mkdtemp(prefix="a1testbed-e-star-"))

results: list[tuple[str, str, str]] = []


def record(claim: str, verdict: str, detail: str) -> None:
    results.append((claim, verdict, detail))
    print(f"  [{verdict}] {claim}: {detail}", flush=True)


def run(cmd, cwd=None, env=None, timeout=600):
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    return proc


def evaluate(candidate, graph, out, *, cwd=None, env=None, extra=(), state_dir=None, timeout=200):
    cmd = [PY, str(E_STAR), "evaluate", "--candidate", str(candidate), "--graph", str(graph),
           "--seed", "1337", "--timeout", "30", "--out", str(out)]
    if state_dir:
        cmd += ["--state-dir", str(state_dir)]
    cmd += list(extra)
    proc = run(cmd, cwd=cwd, env=env, timeout=timeout)
    doc = json.loads(pathlib.Path(out).read_text()) if pathlib.Path(out).is_file() else None
    return proc, doc


def outcome_core(doc):
    """The canonical bytes, minus the fields that legitimately differ per process."""
    trimmed = {k: v for k, v in doc.items() if k not in ("canonical_digest",)}
    trimmed.pop("interpreter", None)  # sys.executable/version, a declared environment field
    return json.dumps(trimmed, sort_keys=True)


# --------------------------------------------------------------------------- #
# C2.1
# --------------------------------------------------------------------------- #

def c_cwd_path_independence():
    base = WORK / "cwd"
    outs = {}
    for tag, cwd in (("root", "/"), ("tmp", "/tmp"), ("repo", str(REPO))):
        out = base / f"{tag}.json"
        proc, doc = evaluate(CAND_OK, GRAPH, out, cwd=cwd)
        if proc.returncode != 0 or doc is None:
            record("C2.1 cwd independence", "REJECTED", f"cwd={cwd} rc={proc.returncode} {proc.stderr[-200:]}")
            return
        outs[tag] = doc
    same = len({outcome_core(d) for d in outs.values()}) == 1
    record("C2.1 cwd independence",
           "ACCEPTED" if same else "REJECTED",
           f"3 cwds (/, /tmp, repo root) -> cut_edges "
           f"{[outs[t]['cut_edges'] for t in ('root', 'tmp', 'repo')]}, "
           f"equal canonical bytes {same}")

    # PATH: the harness's own interpreter is absolute, so an empty/absurd PATH must not matter
    envs = {
        "normal": None,
        "empty-path": {**os.environ, "PATH": ""},
        "no-path": {k: v for k, v in os.environ.items() if k != "PATH"},
        "absurd-path": {**os.environ, "PATH": "/nonexistent-bin"},
    }
    seen = {}
    for tag, env in envs.items():
        out = base / f"path-{tag}.json"
        proc, doc = evaluate(CAND_OK, GRAPH, out, env=env)
        if doc is None:
            record("C2.1 PATH independence", "REJECTED", f"{tag}: rc={proc.returncode}")
            return
        seen[tag] = doc
    same = len({outcome_core(d) for d in seen.values()}) == 1
    record("C2.1 PATH independence",
           "ACCEPTED" if same else "REJECTED",
           f"PATH normal/empty/absent/absurd -> cut_edges {[seen[t]['cut_edges'] for t in envs]}, "
           f"equal canonical bytes {same}")


def c_determinism():
    a = WORK / "det-a.json"
    b = WORK / "det-b.json"
    _, da = evaluate(CAND_OK, GRAPH, a)
    _, db = evaluate(CAND_OK, GRAPH, b)
    ok = (da["status"] == "ok" and da["canonical_digest"] == db["canonical_digest"]
          and da["determinism"]["identical"] is True
          and da["determinism"]["canonical_sha256"][0] == da["determinism"]["canonical_sha256"][1])
    record("C2.1 determinism across two E* processes", "ACCEPTED" if ok else "REJECTED",
           f"canonical_digest {da['canonical_digest'][:16]}=={db['canonical_digest'][:16]}, "
           f"runs-2-identical={da['determinism']['identical']}")


def c_failure_semantics():
    rows = json.loads((MX / "conformance.expected.json").read_text())["rows"]
    net_rows = set(json.loads((MX / "conformance.expected.json").read_text())["net_isolate_rows"])
    bad = []
    checked = 0
    for row in rows:
        if row["status"] == "ok":
            continue
        cand = MX / "candidates" / row["candidate_id"]
        if row["candidate_id"] == "c17_error_input_tampered":
            continue  # needs its own graph-mutating setup; reproduced separately below
        out = WORK / f"fail-{row['candidate_id']}.json"
        # the frozen table's own record of which rows need the closed topology
        extra = ("--net-isolate",) if row["candidate_id"] in net_rows else ()
        proc, doc = evaluate(cand, GRAPH, out, extra=extra)
        checked += 1
        if doc is None:
            bad.append(f"{row['candidate_id']}: no outcome (rc={proc.returncode})")
            continue
        if doc["cut_edges"] is not None or doc["cut_fraction"] is not None:
            bad.append(f"{row['candidate_id']}: cut_edges={doc['cut_edges']!r} (must be null)")
        if doc["status"] != row["status"]:
            bad.append(f"{row['candidate_id']}: status {doc['status']} != expected {row['status']}")
        if (doc["failure"] or {}).get("kind") != row["failure_kind"]:
            bad.append(f"{row['candidate_id']}: failure.kind {(doc['failure'] or {}).get('kind')!r} "
                       f"!= expected {row['failure_kind']!r}")
    record("C2.1 failure semantics: cut_edges null (never 0) for every non-ok row",
           "ACCEPTED" if not bad else "REJECTED",
           f"{checked} non-ok C*(T1) candidates run (c15 with the frozen table's own --net-isolate); "
           f"problems={bad if bad else 'none'}")
    # and the same candidate WITHOUT the flag, to show what the default invocation does
    out_open = WORK / "fail-c15-open.json"
    _, doc_open = evaluate(MX / "candidates/c15_error_network_attempt", GRAPH, out_open)
    print(f"    c15_error_network_attempt without --net-isolate: status={doc_open['status']} "
          f"cut_edges={doc_open['cut_edges']} failure={(doc_open['failure'] or {}).get('kind')}")

    # the tamper row, set up here: rewrite the graph after the candidate read it
    tamper_cand = WORK / "tamper_cand"
    tamper_cand.mkdir(exist_ok=True)
    (tamper_cand / "solution.py").write_text(
        "import argparse,json,pathlib\n"
        "p=argparse.ArgumentParser();p.add_argument('--graph');p.add_argument('--out');p.add_argument('--seed',type=int)\n"
        "a=p.parse_args()\n"
        "doc=json.load(open(a.graph))\n"
        "# rewrite the graph's own edge list to a single edge (tamper), then write a valid partition\n"
        "E=pathlib.Path(a.graph);E.write_text(json.dumps({'schema':doc['schema'],'graph_id':doc['graph_id'],"
        "'family':doc['family'],'n':doc['n'],'edges':[[0,1]],'generator':doc['generator'],'notes':''},"
        "sort_keys=True,separators=(',',':'))+'\\n')\n"
        "open(a.out,'w').write(json.dumps({'schema':'a0.maxcut.partition/v1','graph_id':doc['graph_id'],"
        "'assignment':[i%2 for i in range(doc['n'])]},sort_keys=True,separators=(',',':'))+'\\n')\n"
    )
    victim = WORK / "tamper_graph.json"
    shutil.copy(GRAPH, victim)
    out = WORK / "tamper.json"
    proc, doc = evaluate(tamper_cand, victim, out)
    record("C2.1 input tampering is reported, not scored",
           "ACCEPTED" if doc and doc["status"] == "error" and doc["cut_edges"] is None
           else "REJECTED",
           f"status={doc and doc['status']} failure={doc and (doc['failure'] or {}).get('kind')} "
           f"cut_edges={doc and doc['cut_edges']}")


def c_network_and_env():
    # (a) the child's environment, dumped by the candidate itself
    env_cand = WORK / "env_cand"
    env_cand.mkdir(exist_ok=True)
    (env_cand / "solution.py").write_text(
        "import argparse,json,os,pathlib\n"
        "p=argparse.ArgumentParser();p.add_argument('--graph');p.add_argument('--out');p.add_argument('--seed',type=int)\n"
        "a=p.parse_args()\n"
        "pathlib.Path('env_dump.json').write_text(json.dumps(dict(os.environ),sort_keys=True))\n"
        "doc=json.load(open(a.graph))\n"
        "open(a.out,'w').write(json.dumps({'schema':'a0.maxcut.partition/v1','graph_id':doc['graph_id'],"
        "'assignment':[i%2 for i in range(doc['n'])]},sort_keys=True,separators=(',',':'))+'\\n')\n"
    )
    state = WORK / "state-env"
    out = WORK / "env.json"
    proc, doc = evaluate(env_cand, GRAPH, out, state_dir=state)
    dumps = sorted(state.glob("invocations/*/*/run*/scratch/env_dump.json"))
    if not dumps:
        record("C2.1 no credential/proxy leakage into the child", "UNPROVEN", "no env dump found")
    else:
        child_env = json.loads(dumps[0].read_text())
        host_names = set(os.environ)
        leaked = sorted(n for n in child_env if n not in {"PATH", "PYTHONDONTWRITEBYTECODE", "HOME", "LANG"})
        suspicious = sorted(n for n in child_env
                            if any(t in n.upper() for t in ("PROXY", "KEY", "TOKEN", "SECRET", "PASSWORD")))
        host_only = sorted(host_names - set(child_env) - {"PATH", "HOME", "LANG"})
        record("C2.1 no credential/proxy leakage into the child",
               "ACCEPTED" if not leaked and not suspicious else "REJECTED",
               f"child env keys={sorted(child_env)}; extra={leaked}; suspicious={suspicious}; "
               f"host vars not inherited={len(host_only)}/{len(host_names)}")

    # (b) network independence and what "no network" actually means here
    net_cand = WORK / "net_cand"
    net_cand.mkdir(exist_ok=True)
    (net_cand / "solution.py").write_text(
        "import argparse,json,socket,sys\n"
        "p=argparse.ArgumentParser();p.add_argument('--graph');p.add_argument('--out');p.add_argument('--seed',type=int)\n"
        "a=p.parse_args()\n"
        "try:\n"
        "    s=socket.create_connection(('1.1.1.1',443),timeout=3);s.close()\n"
        "except Exception as exc:\n"
        "    print('no network:',exc,file=sys.stderr);sys.exit(40)\n"
        "doc=json.load(open(a.graph));open(a.out,'w').write(json.dumps({'schema':'a0.maxcut.partition/v1',"
        "'graph_id':doc['graph_id'],'assignment':[i%2 for i in range(doc['n'])]},sort_keys=True,separators=(',',':')))\n"
    )
    out = WORK / "net-open.json"
    _, doc_open = evaluate(net_cand, GRAPH, out)
    out_i = WORK / "net-iso.json"
    _, doc_iso = evaluate(net_cand, GRAPH, out_i, extra=("--net-isolate",))
    # honest candidate, with and without the namespace
    out_a = WORK / "honest-open.json"
    out_b = WORK / "honest-iso.json"
    _, doc_a = evaluate(CAND_OK, GRAPH, out_a)
    _, doc_b = evaluate(CAND_OK, GRAPH, out_b, extra=("--net-isolate",))
    same = doc_a["canonical_digest"] == doc_b["canonical_digest"]
    record("C2.1 network independence (an honest candidate's number does not move with the topology)",
           "ACCEPTED" if same else "REJECTED",
           f"honest candidate cut_edges open={doc_a['cut_edges']} netns={doc_b['cut_edges']}, "
           f"canonical_digest equal={same}")
    record("C2.1 a candidate that insists on the network is refused in both topologies",
           "ACCEPTED" if doc_open["status"] == "error" and doc_iso["status"] == "error" else "REJECTED",
           f"1.1.1.1:443 open-topology -> status={doc_open['status']} "
           f"failure={(doc_open['failure'] or {}).get('kind')} (exit "
           f"{doc_open['interpreted']['exit_code']}); --net-isolate -> status={doc_iso['status']} "
           f"failure={(doc_iso['failure'] or {}).get('kind')}")

    # (c) the one that matters for the budget: can a child reach the bare model API?
    api_cand = WORK / "api_cand"
    api_cand.mkdir(exist_ok=True)
    (api_cand / "solution.py").write_text(
        "import argparse,json,socket,sys\n"
        "p=argparse.ArgumentParser();p.add_argument('--graph');p.add_argument('--out');p.add_argument('--seed',type=int)\n"
        "a=p.parse_args()\n"
        "result={}\n"
        "for host in ('api.deepseek.com','127.0.0.1'):\n"
        "    for port in ((443,) if host!='127.0.0.1' else (7890,8080,8081,8082)):\n"
        "        try:\n"
        "            s=socket.create_connection((host,port),timeout=2);s.close();result[f'{host}:{port}']='open'\n"
        "        except Exception as exc: result[f'{host}:{port}']=type(exc).__name__\n"
        "open('/tmp/a1testbed-egress.json','w').write(json.dumps(result,sort_keys=True))\n"
        "doc=json.load(open(a.graph));open(a.out,'w').write(json.dumps({'schema':'a0.maxcut.partition/v1',"
        "'graph_id':doc['graph_id'],'assignment':[i%2 for i in range(doc['n'])]},sort_keys=True,separators=(',',':')))\n"
    )
    pathlib.Path("/tmp/a1testbed-egress.json").unlink(missing_ok=True)
    _, doc_api = evaluate(api_cand, GRAPH, WORK / "api-open.json")
    open_report = json.loads(pathlib.Path("/tmp/a1testbed-egress.json").read_text())
    pathlib.Path("/tmp/a1testbed-egress.json").unlink()
    _, doc_api_iso = evaluate(api_cand, GRAPH, WORK / "api-iso.json", extra=("--net-isolate",))
    iso_report = json.loads(pathlib.Path("/tmp/a1testbed-egress.json").read_text())
    print(f"    child egress (open topology): {open_report}")
    print(f"    child egress (--net-isolate): {iso_report}")
    reachable = [k for k, v in open_report.items() if v == "open"]
    record("C2.1 the child has no route to the model API in the OPEN topology",
           "ACCEPTED" if not reachable else "REJECTED",
           f"from inside the candidate process (env has no proxy): reachable={reachable or 'none'}; "
           f"--net-isolate reachable={[k for k, v in iso_report.items() if v == 'open'] or 'none'}")


def c_exact_aggregation():
    out = WORK / "agg-dev.json"
    cmd = [PY, str(E_STAR), "aggregate", "--candidate", str(CAND_OK), "--graph-set", "dev",
           "--out", str(out), "--seed", "1337", "--timeout", "30", "--state-dir", str(WORK / "state-agg")]
    proc = run(cmd, timeout=1200)
    if not out.is_file():
        record("C2.1 exact rational aggregation", "REJECTED", f"no aggregate (rc={proc.returncode}) {proc.stderr[-300:]}")
        return
    agg = json.loads(out.read_text())
    # independent route: evaluate every dev graph myself, then aggregate with Fraction
    suite = MX / "suite/dev"
    weighted_num = weighted_den = 0
    sum_of_rates = Fraction(0)
    counts = {"ok": 0, "invalid": 0, "error": 0, "timeout": 0}
    per_fam: dict[str, list[tuple[int, int]]] = {}
    for path in sorted(suite.glob("*.json")):
        o = WORK / f"agg-{path.stem}.json"
        proc, doc = evaluate(CAND_OK, path, o)
        counts[doc["status"]] += 1
        if doc["status"] == "ok":
            weighted_num += doc["cut_edges"]
            weighted_den += doc["edges_total"]
            sum_of_rates += Fraction(doc["cut_edges"], doc["edges_total"])
            per_fam.setdefault(doc["graph_family"], []).append((doc["cut_edges"], doc["edges_total"]))
    weighted = Fraction(weighted_num, weighted_den)
    theirs = Fraction(agg["score_exact"]["numerator"], agg["score_exact"]["denominator"])
    fam_ok = all(Fraction(agg["per_family_exact"][f]["numerator"], agg["per_family_exact"][f]["denominator"])
                 == Fraction(sum(c for c, _ in v), sum(e for _, e in v))
                 for f, v in per_fam.items())
    reduced = theirs.numerator is not None and Fraction(theirs) == theirs and \
        __import__("math").gcd(theirs.numerator, theirs.denominator) == 1
    record("C2.1 exact rational aggregation of 24 dev Outcomes (Σcut/Σ|E|, the implemented rule)",
           "ACCEPTED" if weighted == theirs and counts == agg["counts"] and fam_ok and reduced else "REJECTED",
           f"mine={weighted.numerator}/{weighted.denominator} theirs={theirs.numerator}/{theirs.denominator} "
           f"counts mine={counts} theirs={agg['counts']} per_family_exact match={fam_ok} reduced={reduced}")
    # §5's literal text reads as the accumulation of the per-graph rates; the code
    # docstring declares the other reading.  With |E| varying 192..713 on dev the
    # two are not equal, so record which one every consumer gets.
    literal = sum_of_rates
    record("C2.1 §5's literal reading (accumulate cut_i/|E_i|) gives a different number",
           "PARTIALLY ACCEPTED" if literal != theirs else "ACCEPTED",
           f"literal Σ(cut_i/|E_i|)={literal.numerator}/{literal.denominator} ({float(literal):.6f}) vs "
           f"implemented Σcut/Σ|E|={theirs.numerator}/{theirs.denominator} ({float(theirs):.6f}); "
           f"no consumer of score_exact exists in a0/a1 or gates/ (grep), so the divergence is inert")


# --------------------------------------------------------------------------- #
# C2.2 -- mode irrelevance
# --------------------------------------------------------------------------- #

def c_mode_irrelevance():
    src = (MX / "candidates/c18_ok_inflation_attempt/solution.py")
    body = src.read_bytes()
    variants = {}
    for tag, mode in (("0755", 0o755), ("0644", 0o644), ("0600", 0o600), ("0400", 0o400)):
        d = WORK / f"mode-{tag}"
        d.mkdir(exist_ok=True)
        f = d / "solution.py"
        f.write_bytes(body)
        os.chmod(f, mode)
        # same declared identity in every variant, so candidate_id cannot be the
        # thing that differs: only the mode bit is allowed to vary
        (d / "candidate.json").write_text(json.dumps({"candidate_id": "mode-probe", "entry": "solution.py"}))
        out = WORK / f"mode-{tag}.json"
        proc, doc = evaluate(d, GRAPH, out)
        variants[tag] = (mode, doc, proc.returncode)
    print("    mode variants:", {t: (oct(m), d and d["status"], d and d["cut_edges"], d and d["candidate_source_sha256"][:12])
                                 for t, (m, d, _) in variants.items()})
    digests = {d["candidate_source_sha256"] for _, d, _ in variants.values() if d}
    cores = {outcome_core(d) for _, d, _ in variants.values() if d}
    ok = (len(digests) == 1 and len(cores) == 1
          and all(d["status"] == "ok" for _, d, _ in variants.values()))
    record("C2.2 the launch does not depend on the entry's mode bit (byte-identical, 0755/0644/0600/0400)",
           "ACCEPTED" if ok else "REJECTED",
           f"identical candidate_source_sha256={len(digests) == 1}, identical canonical outcome="
           f"{len(cores) == 1}, all ok={all(d['status'] == 'ok' for _, d, _ in variants.values())}")

    # the complementary half: a bogus shebang must not change the launch either
    d = WORK / "bogus-shebang"
    d.mkdir(exist_ok=True)
    f = d / "solution.py"
    f.write_bytes(b"#!/bin/false -not-an-interpreter\n" + body[body.index(b"\n") + 1:])
    out = WORK / "bogus.json"
    proc, doc = evaluate(d, GRAPH, out)
    record("C2.2 the '#!/...' line is not consulted (no execve)",
           "ACCEPTED" if doc and doc["status"] == "ok" and doc["cut_edges"] == variants["0644"][1]["cut_edges"]
           else "REJECTED",
           f"entry first line '#!/bin/false …' -> status={doc and doc['status']} cut_edges={doc and doc['cut_edges']}")

    # the declared opt-in must still be honoured exactly once
    d2 = WORK / "declared-exec"
    d2.mkdir(exist_ok=True)
    sh = d2 / "solution.sh"
    sh.write_text("#!/bin/sh\nexec %s %s/solution.py \"$@\"\n" % (PY, d2))
    (d2 / "solution.py").write_text(body.decode())
    (d2 / "candidate.json").write_text(json.dumps({"candidate_id": "declared-exec", "entry": "solution.sh",
                                                   "exec": []}))
    os.chmod(sh, 0o755)
    out = WORK / "declared.json"
    proc, doc = evaluate(d2, GRAPH, out)
    record("C2.2 `exec: []` is honoured for a genuinely self-executing entry",
           "ACCEPTED" if doc and doc["status"] == "ok" else "REJECTED",
           f"shell entry with exec:[] -> status={doc and doc['status']} cut_edges={doc and doc['cut_edges']} "
           f"argv0-mode={'shell' if doc and doc['status'] == 'ok' else 'n/a'}")
    # ... and a declared-exec entry that is NOT executable must be a precise error
    os.chmod(sh, 0o644)
    out = WORK / "declared-noexec.json"
    proc, doc = evaluate(d2, GRAPH, out)
    record("C2.2 a declared direct execution with a non-executable entry errors precisely",
           "ACCEPTED" if doc is None and proc.returncode == 3 and "executable" in proc.stderr
           else "REJECTED",
           f"rc={proc.returncode} stderr={proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else ''}")


# --------------------------------------------------------------------------- #
# C2.3 -- the regression test against the pre-fix bytes
# --------------------------------------------------------------------------- #

def c_prefix_regression():
    prefix = WORK / "pre-fix"
    prefix.mkdir(exist_ok=True)
    for name in ("e_star.py", "e_star_child.py"):
        blob = subprocess.run(["git", "-C", str(REPO), "show", f"11f55bf0:a0/tasks/maxcut/{name}"],
                              capture_output=True)
        if blob.returncode != 0:
            record("C2.3 staging regression fails on the pre-fix E*", "UNPROVEN",
                   f"git show failed for {name}")
            return
        (prefix / name).write_bytes(blob.stdout)
    pre_digest = hashlib.sha256((prefix / "e_star.py").read_bytes()).hexdigest()
    test = MX / "test_candidate_staging.py"

    post = run([PY, str(test), "--json"], timeout=900)
    pre = run([PY, str(test), "--e-star", str(prefix / "e_star.py"), "--json"], timeout=900)
    print(f"    pre-fix e_star.py sha256={pre_digest[:16]}  (test: rc pre={pre.returncode} post={post.returncode})")
    print("    pre-fix stdout tail:", (pre.stdout or "").strip()[-400:])
    record("C2.3 test_candidate_staging.py passes on the working tree",
           "ACCEPTED" if post.returncode == 0 else "REJECTED", f"rc={post.returncode}")
    record("C2.3 test_candidate_staging.py fails on the pre-fix E* (git 11f55bf0)",
           "ACCEPTED" if pre.returncode != 0 else "REJECTED",
           f"rc={pre.returncode}; failure line: "
           f"{(pre.stdout or '').strip().splitlines()[-1] if (pre.stdout or '').strip() else pre.stderr.strip()[-200:]}")

    # and the same test through the conformance entry point that claims to carry it
    conf = run([PY, str(MX / "conformance.py"), "--check"], timeout=2400)
    tail = (conf.stdout or "").strip().splitlines()
    record("C2.3 conformance.py --check is green (21 rows + 14 checks incl. 5 staging cases)",
           "ACCEPTED" if conf.returncode == 0 else "REJECTED",
           f"rc={conf.returncode}; {tail[-1] if tail else conf.stderr[-200:]}")


# --------------------------------------------------------------------------- #
# C2.4 -- hand-reproduction of conformance rows
# --------------------------------------------------------------------------- #

def c_hand_rows():
    rows = {r["candidate_id"]: r for r in json.loads((MX / "conformance.expected.json").read_text())["rows"]}
    verdicts = []
    for cid in ("c01_ok_high_pc", "c13_error_non_deterministic", "c19_timeout_process_group"):
        row = rows[cid]
        out = WORK / f"hand-{cid}.json"
        proc, doc = evaluate(MX / "candidates" / cid, GRAPH, out)
        match = (doc is not None and doc["status"] == row["status"]
                 and doc["cut_edges"] == row["cut_edges"]
                 and (doc["failure"] or {}).get("kind") == row["failure_kind"]
                 and proc.returncode == row["evaluator_exit_code"]
                 and doc["candidate_source_sha256"] == row["candidate_source_sha256"])
        verdicts.append((cid, match, doc["status"] if doc else None, proc.returncode))
        print(f"    {cid}: expected status={row['status']} cut={row['cut_edges']} kind={row['failure_kind']} "
              f"rc={row['evaluator_exit_code']} | mine status={doc and doc['status']} "
              f"cut={doc and doc['cut_edges']} kind={doc and (doc['failure'] or {}).get('kind')} rc={proc.returncode}")
    record("C2.4 conformance rows reproduce by hand (ok / non-deterministic / timeout)",
           "ACCEPTED" if all(m for _, m, _, _ in verdicts) else "REJECTED",
           "; ".join(f"{cid}:{'match' if m else 'MISMATCH'}" for cid, m, _, _ in verdicts))


if __name__ == "__main__":
    print(f"work dir: {WORK}")
    for fn in (c_cwd_path_independence, c_determinism, c_failure_semantics, c_network_and_env,
               c_exact_aggregation, c_mode_irrelevance, c_prefix_regression, c_hand_rows):
        print(f"\n== {fn.__name__} ==", flush=True)
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            record(fn.__name__, "UNPROVEN", f"probe raised {type(exc).__name__}: {exc}")
    print("\n== summary ==")
    for claim, verdict, detail in results:
        print(f"{verdict:18s} {claim}")
