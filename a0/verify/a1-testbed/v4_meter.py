#!/usr/bin/env python3
"""Adversarial re-derivation of the meter claims (assignment item 4).

  1. the ledger arithmetic, re-derived from each row's own usage
  2. the framing fix, on the wire, before and after (raw tap, pre-fix proxy from git)
  3. the fail-closed claims: unframed body refused, ledger unwritable -> call refused,
     CONNECT never tunnelled, non-allowlisted destination refused

No model call is made and no real provider is contacted: the upstream legs here are
local sockets.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import socket
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[3]
METER = REPO / "a0/meter"
HERE = pathlib.Path(__file__).resolve().parent
TAPDIR = HERE / "tap"
PREFIX_PROXY = pathlib.Path("/tmp/prefix-meter/a0/meter/meter_proxy.py")
PY = sys.executable

problems: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
    if not cond:
        problems.append(msg)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_port(port: int, timeout: float = 10.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.4).close()
            return True
        except OSError:
            time.sleep(0.05)
    return False


def send(port: int, raw: bytes, timeout: float = 10.0) -> bytes:
    s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    s.sendall(raw)
    out = b""
    s.settimeout(timeout)
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            out += chunk
    except socket.timeout:
        pass
    s.close()
    return out


def start_proxy(*, ledger: pathlib.Path, upstream: str, port: int, token: str = "tok-probe",
                allowlist: str = "127.0.0.1,api.deepseek.com", extra=()):
    cmd = [PY, str(METER / "meter_proxy.py"), "--campaign-id", "C_probe", "--arm-id", "A_probe",
           "--port", str(port), "--ledger", str(ledger), "--upstream-base", upstream,
           "--allowlist", allowlist, "--no-fsync", "--token", token, *extra]
    log = open(f"/tmp/meter-probe-{port}.log", "wb")
    return subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=str(METER)), log


def probe_body(port: int, token: str, path: str = "/v1/chat/completions",
               host: str = "127.0.0.1", framing: str = "cl", body: bytes = b'{"model":"deepseek-flash"}') -> bytes:
    if framing == "cl":
        head = b"Content-Length: %d\r\n" % len(body)
    elif framing == "chunked":
        head = b"Transfer-Encoding: chunked\r\n"
        body = b"%x\r\n" % len(body) + body + b"\r\n0\r\n\r\n"
    else:
        head = b""
    raw = (b"POST " + path.encode() + b" HTTP/1.1\r\nHost: " + host.encode() + b":%d\r\n" % port
           + b"Content-Type: application/json\r\nAuthorization: Bearer not-a-real-key\r\n"
           + b"X-A0-Meter-Token: " + token.encode() + b"\r\n" + head + b"\r\n" + body)
    return send(port, raw)


def main() -> int:
    print("== 1. ledger arithmetic re-derived from each row's own usage ==")
    for name in ("ledger.jsonl", "live_ledger.jsonl"):
        path = METER / "evidence" / name
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        bad = []
        metered = unmetered = total = 0
        for i, row in enumerate(rows):
            if row["unmetered"]:
                unmetered += 1
                if row["ceq"] is not None or row["usage"] is not None or not row["reason"]:
                    bad.append((i, "unmetered row not null/with-reason"))
                continue
            u = row["usage"]
            expect = u["prompt_cache_miss_tokens"] + (u["prompt_cache_hit_tokens"] * 2) // 100 + 4 * u["completion_tokens"]
            if expect != row["ceq"]:
                bad.append((i, row["ceq"], expect))
            metered += 1
            total += row["ceq"]
        tool = subprocess.run([PY, str(METER / "verify_ledger.py"), str(path)],
                              capture_output=True, text=True)
        tool_total = int(tool.stdout.split("ceq_total=")[1].split()[0]) if "ceq_total=" in tool.stdout else -1
        check(not bad and tool.returncode == 0 and tool_total == total,
              f"{name}: {len(rows)} rows, {metered} metered / {unmetered} unmetered, my ceq_total={total}, "
              f"verify_ledger.py ceq_total={tool_total}, rc={tool.returncode}, mismatches={bad}")
    # the interface's own worked example, from INTERFACE.md §8's corrected paragraph
    from fractions import Fraction
    check(0 + (0 * 2) // 100 + 4 * 312 == 1248, "INTERFACE.md §8's own example arithmetic (4*312=1248)")
    print(f"    formula: ceq = miss + floor(hit*2/100) + 4*completion; "
          f"no float anywhere: Fraction(187090) == {Fraction(187090)}")

    print("\n== 2. framing on the wire: my own raw-tap captures, after and before ==")
    for label, want_framed in (("mine_after", True), ("mine_before", False)):
        js = json.loads((TAPDIR / f"framing_{label}.json").read_text())
        verdicts = js["verdicts"]
        rows = js["ledger_rows"]
        framed = [v for v in verdicts if v.get("framing_header_present")]
        metered = [r for r in rows if not r.get("unmetered")]
        print(f"    {label}: {len(verdicts)} client shapes, {len(framed)} reached the upstream framed, "
              f"ledger rows metered={len(metered)}, ok={js['ok']}")
        for v in verdicts:
            print(f"      {v['shape'][:28]:28s} reached={v['reached_upstream']} framing={v['framing']!r} "
                  f"header_present={v['framing_header_present']} length_matches={v['declared_length_matches_body']} "
                  f"body_identical={v['body_identical_to_client']} status={v['upstream_status']!r}")
        if want_framed:
            check(all(v["framing_header_present"] and v["declared_length_matches_body"]
                      and v["body_identical_to_client"] for v in verdicts[:2]),
                  f"{label}: both body-bearing shapes arrive framed, with a length that matches the body "
                  f"and bytes identical to the client's")
            check(verdicts[0]["framing"] == "content-length" and verdicts[1]["framing"] == "chunked",
                  f"{label}: shape A framed by Content-Length, shape B by Transfer-Encoding: chunked")
            check(not verdicts[2]["reached_upstream"],
                  f"{label}: the client's illegal unframed body never reaches the upstream "
                  f"(the proxy answers it {verdicts[2]['upstream_status']} itself)")
            check(len(metered) == 2 and all(r["ceq"] == 4128 for r in metered),
                  f"{label}: exactly 2 metered rows, each ceq=4128 (usage was readable upstream)")
        else:
            check(not any(v["framing_header_present"] for v in verdicts),
                  f"{label}: NO request carries a framing header (the pre-fix defect)")
            check(all(v["upstream_status"] == "HTTP/1.1 400 Bad Request" for v in verdicts),
                  f"{label}: every shape answered 400 by the wire-shaped upstream")
            check(len(metered) == 0 and all(r["unmetered"] for r in rows),
                  f"{label}: every row unmetered (usage unreadable upstream)")

    print("\n== 3a. an unframed body is refused and never forwarded ==")
    port = free_port()
    ledger = pathlib.Path("/tmp/meter-probe-unframed.jsonl")
    ledger.unlink(missing_ok=True)
    # upstream points at a closed port on purpose: if the proxy contacted it, we would see 502
    dead = free_port()
    proc, log = start_proxy(ledger=ledger, upstream=f"https://127.0.0.1:{dead}", port=port)
    try:
        if not wait_port(port):
            check(False, "proxy did not start for the unframed probe")
        else:
            resp = probe_body(port, "tok-probe", framing="none")
            rows = [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
            check(b"400" in resp.split(b"\r\n")[0] and b"Meter Token" not in resp,
                  f"unframed body -> {resp.split(b'\r\n')[0].decode()}")
            check(any(r["unmetered"] and r["reason"] == "request_body_unframed" for r in rows),
                  f"booked as unmetered with reason request_body_unframed ({[r['reason'] for r in rows]})")
    finally:
        proc.kill()
        log.close()

    print("\n== 3b. ledger unwritable -> the call is refused (not booked unmetered) ==")
    ro_dir = pathlib.Path("/tmp/meter-probe-ro")
    ro_dir.mkdir(exist_ok=True)
    os.chmod(ro_dir, 0o700)
    port = free_port()
    ledger = ro_dir / "ledger.jsonl"
    ledger.unlink(missing_ok=True)
    proc, log = start_proxy(ledger=ledger, upstream=f"https://127.0.0.1:{free_port()}", port=port)
    ok_start = wait_port(port)
    # the ledger *file* becomes unwritable after startup; a directory-only check would be
    # passed by O_WRONLY on an existing file, so the file itself is what must be changed
    os.chmod(ledger, 0o400)
    try:
        if not ok_start:
            check(False, "proxy did not start for the unwritable-ledger probe")
        else:
            resp = probe_body(port, "tok-probe")
            log.flush()
            text = pathlib.Path(f"/tmp/meter-probe-{port}.log").read_text(errors="replace")
            check(resp.startswith(b"HTTP/1.1 500"), f"call answered {resp.split(b'\r\n')[0].decode()}")
            check(b"ledger not writable; call refused" in resp,
                  "the refusal says the call was refused rather than unmetered")
            check("LEDGER PREFLIGHT FAILED, refusing call before contacting upstream" in text,
                  "the proxy log shows the refusal happened before the upstream leg")
    finally:
        os.chmod(ro_dir, 0o700)
        if ledger.exists():
            os.chmod(ledger, 0o600)
        proc.kill()
        log.close()
    # and a fresh proxy whose ledger cannot be created must not start at all
    port2 = free_port()
    os.chmod(ro_dir, 0o500)
    proc2, log2 = start_proxy(ledger=ro_dir / "ledger2.jsonl", upstream=f"https://127.0.0.1:{free_port()}",
                              port=port2)
    started = wait_port(port2, timeout=3)
    proc2.poll()
    try:
        check(not started and proc2.returncode is not None,
              f"a proxy whose ledger cannot be created does not start (rc={proc2.returncode})")
    finally:
        os.chmod(ro_dir, 0o700)
        if proc2.poll() is None:
            proc2.kill()
        log2.close()

    print("\n== 3c. CONNECT is never tunnelled, and the destination is allowlisted ==")
    port = free_port()
    ledger = pathlib.Path("/tmp/meter-probe-connect.jsonl")
    ledger.unlink(missing_ok=True)
    proc, log = start_proxy(ledger=ledger, upstream=f"https://127.0.0.1:{free_port()}", port=port)
    try:
        if not wait_port(port):
            check(False, "proxy did not start for the CONNECT probe")
        else:
            resp = send(port, b"CONNECT api.deepseek.com:443 HTTP/1.1\r\nHost: api.deepseek.com:443\r\n\r\n")
            rows = [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
            check(resp.startswith(b"HTTP/1.1 405"), f"CONNECT -> {resp.split(b'\r\n')[0].decode()}")
            check(any(r["unmetered"] and r["reason"] == "connect_not_supported" for r in rows),
                  "the tunnelling attempt is recorded as unmetered/connect_not_supported")
            resp = probe_body(port, "tok-probe", host="example.com")
            rows = [json.loads(line) for line in ledger.read_text().splitlines()]
            check(resp.startswith(b"HTTP/1.1 403"), f"Host: example.com -> {resp.split(b'\r\n')[0].decode()}")
            check(any(r["reason"] and (r["reason"].startswith("non_allowlisted_host")
                                      or r["reason"].startswith("host_header_not_allowlisted"))
                      for r in rows),
                  "a non-allowlisted destination is refused, not silently forwarded")
    finally:
        proc.kill()
        log.close()
    print("\n== 3d. the meter's own selftest: before and after ==")
    after = (HERE / "out_selftest_after.txt")
    before = (HERE / "out_selftest_before.txt")
    committed_after = METER / "evidence/report.txt"
    committed_before = METER / "evidence/selftest_on_prefix_proxy.txt"
    mine_after = re.search(r"(\d+)/(\d+) checks passed", after.read_text())
    mine_before = re.search(r"(\d+)/(\d+) checks passed", before.read_text())
    their_after = re.search(r"(\d+)/(\d+) checks passed", committed_after.read_text())
    their_before = re.search(r"(\d+)/(\d+) checks passed", committed_before.read_text())
    print(f"    post-fix proxy: mine {mine_after.group(0)}, committed {their_after.group(0)}")
    print(f"    pre-fix proxy:  mine {mine_before.group(0)}, committed {their_before.group(0)}")
    check(mine_after.group(0) == "65/65 checks passed" == their_after.group(0),
          "the current proxy passes 65/65 in my run and in the committed report")
    mine_fail = {l.split(" --")[0].strip() for l in before.read_text().splitlines() if l.startswith("  FAIL")}
    their_fail = {l.split(" --")[0].strip() for l in committed_before.read_text().splitlines() if l.startswith("  FAIL")}
    print(f"    pre-fix failures: mine {len(mine_fail)}, committed {len(their_fail)}; "
          f"only in the committed run: {sorted(their_fail - mine_fail)}")
    framing_rows = sorted(f for f in mine_fail if "S18" in f or "S19" in f)
    check(len(framing_rows) >= 5 and len(mine_fail) >= 20,
          f"the pre-fix proxy fails the framing checks specifically ({framing_rows}) and {len(mine_fail)} "
          f"of the 65 checks in all")
    check(their_fail - mine_fail == {"FAIL S16 the refusal names the offending host"},
          "the committed 36/65 differs from my 37/65 by exactly one row (S16), whose committed failure is "
          "a ModuleNotFoundError from copying only meter_proxy.py without meter_core.py")
    print("    (no provider was contacted anywhere above; all upstream legs are local or dead ports)")

    print(f"\nPROBLEMS: {len(problems)}")
    for p in problems:
        print("  -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
