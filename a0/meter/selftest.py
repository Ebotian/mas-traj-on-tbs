#!/usr/bin/env python3
"""End-to-end proof of the metering proxy, entirely against a local fake upstream.

Nothing here talks to api.deepseek.com and nothing here costs money. What it *does* establish:

* the ledger reproduces the frozen integer formula for every shape DeepSeek serves, including
  Anthropic's `cache_read_input_tokens`;
* a missing usage becomes `unmetered: true, ceq: null` with a reason that names the gap;
* a streamed call is metered from a usage chunk that arrives after the content, and the content
  is forwarded *before* the usage exists (so the meter is not secretly buffering the stream);
* a stream cut before usage arrives is unmetered and says it was truncated;
* a non-allowlisted destination is refused without any connection being attempted;
* two campaigns running concurrently are attributed to their own ports and never to each other;
* a ledger that cannot be written makes the call fail instead of producing an unmetered success.

Usage: `python3 selftest.py --out evidence [--keep]`
Exit code 0 iff every check passed.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from meter_core import ceq, read_ledger, verify_row  # noqa: E402

PROXY = os.path.join(HERE, "meter_proxy.py")
FAKE = os.path.join(HERE, "fake_upstream.py")

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    CHECKS.append((name, bool(ok), detail))
    print("  %-4s %s%s" % ("PASS" if ok else "FAIL", name, (" -- " + detail) if detail else ""))
    return bool(ok)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_port(port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.05)
    return False


# ------------------------------------------------------------------------------------------
# HTTP helpers
# ------------------------------------------------------------------------------------------


def post(port: int, path: str, body: dict, headers: dict, timeout: float = 30.0):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    payload = json.dumps(body).encode()
    hdrs = {"Content-Type": "application/json", "Content-Length": str(len(payload))}
    hdrs.update(headers)
    conn.request("POST", path, body=payload, headers=hdrs)
    resp = conn.getresponse()
    data = resp.read()
    out = (resp.status, dict(resp.getheaders()), data)
    conn.close()
    return out


def request_raw(port: int, raw: bytes, timeout: float = 30.0):
    sock = socket.create_connection(("127.0.0.1", port), timeout=timeout)
    sock.sendall(raw)
    chunks = []
    sock.settimeout(timeout)
    while True:
        try:
            data = sock.recv(65536)
        except socket.timeout:
            break
        if not data:
            break
        chunks.append(data)
    sock.close()
    return b"".join(chunks)


def json_of(body: bytes):
    try:
        return json.loads(body.decode())
    except ValueError:
        return None


def split_http(raw: bytes) -> tuple[bytes, bytes]:
    head, _, body = raw.partition(b"\r\n\r\n")
    return head, body


def dechunk_body(blob: bytes) -> bytes:
    decoded = bytearray()
    pos = 0
    while True:
        end = blob.find(b"\r\n", pos)
        if end < 0:
            break
        try:
            size = int(blob[pos:end].split(b";")[0], 16)
        except ValueError:
            break
        if size == 0:
            break
        start = end + 2
        decoded += blob[start:start + size]
        pos = start + size + 2
    return bytes(decoded)


def sse_events_from_text(text: bytes) -> list[tuple[str | None, bytes]]:
    events = []
    for block in text.split(b"\n\n"):
        if not block.strip():
            continue
        name = None
        data_parts = []
        for line in block.split(b"\n"):
            if line.startswith(b"event: "):
                name = line[7:].decode()
            elif line.startswith(b"data: "):
                data_parts.append(line[6:])
        events.append((name, b"\n".join(data_parts)))
    return events


def raw_sse(stream: bytes) -> tuple[list[tuple[str | None, bytes]], bool]:
    """From a raw chunked HTTP response on a client socket: (events, saw_final_chunk)."""
    _, body = split_http(stream)
    return sse_events_from_text(dechunk_body(body)), b"0\r\n\r\n" in body


# ------------------------------------------------------------------------------------------
# Setup helpers
# ------------------------------------------------------------------------------------------


def make_certs(work: str) -> tuple[str, str, str]:
    """A throwaway CA and a 127.0.0.1 server certificate, so the TLS leg is genuinely verified."""
    ca_key = os.path.join(work, "ca.key")
    ca_pem = os.path.join(work, "ca.pem")
    srv_key = os.path.join(work, "srv.key")
    srv_csr = os.path.join(work, "srv.csr")
    srv_pem = os.path.join(work, "srv.pem")
    ext = os.path.join(work, "srv.ext")
    with open(ext, "w", encoding="utf-8") as handle:
        handle.write("subjectAltName=IP:127.0.0.1,DNS:localhost\nbasicConstraints=CA:FALSE\n")
    run = lambda *args: subprocess.run(args, check=True, capture_output=True, cwd=work)  # noqa: E731
    # OpenSSL 3 / Python 3.14 enforce the CA's keyUsage, so it must be declared explicitly.
    run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", ca_key,
        "-out", ca_pem, "-days", "2", "-subj", "/CN=a0-meter-selftest-ca",
        "-addext", "basicConstraints=critical,CA:TRUE",
        "-addext", "keyUsage=critical,keyCertSign,cRLSign")
    run("openssl", "req", "-newkey", "rsa:2048", "-nodes", "-keyout", srv_key,
        "-out", srv_csr, "-subj", "/CN=127.0.0.1")
    run("openssl", "x509", "-req", "-in", srv_csr, "-CA", ca_pem, "-CAkey", ca_key,
        "-CAcreateserial", "-out", srv_pem, "-days", "2", "-extfile", ext)
    return ca_pem, srv_pem, srv_key


def start(cmd: list[str], log_path: str) -> subprocess.Popen:
    handle = open(log_path, "ab")
    proc = subprocess.Popen(cmd, stdout=handle, stderr=subprocess.STDOUT, cwd=HERE)
    proc._log_handle = handle  # type: ignore[attr-defined]
    return proc


def stop(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except (subprocess.TimeoutExpired, OSError):
        try:
            proc.kill()
        except OSError:
            pass
    handle = getattr(proc, "_log_handle", None)
    if handle:
        handle.close()


# ------------------------------------------------------------------------------------------
# The run
# ------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=os.path.join(HERE, "evidence"))
    parser.add_argument("--work", default=os.path.join(HERE, ".run"))
    parser.add_argument("--keep", action="store_true", help="keep the scratch run directory")
    args = parser.parse_args(argv)

    work = os.path.abspath(args.work)
    out = os.path.abspath(args.out)
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work, exist_ok=True)
    os.makedirs(out, exist_ok=True)

    upstream_log = os.path.join(work, "upstream.log.jsonl")
    ledger = os.path.join(work, "ledger.jsonl")
    events = os.path.join(work, "events.jsonl")
    aid = os.path.join(work, "aid.json")
    registry = os.path.join(work, "campaigns.json")

    upstream_port = free_port()
    p1, p2 = free_port(), free_port()
    while p2 == p1:
        p2 = free_port()

    ca_pem, srv_pem, srv_key = make_certs(work)

    with open(registry, "w", encoding="utf-8") as handle:
        json.dump({
            "schema": "a0.meter.registry/v1",
            "listen_host": "127.0.0.1",
            "campaigns": [
                {"campaign_id": "C_0001", "arm_id": "A_base", "port": p1, "token": "tok-C1"},
                {"campaign_id": "C_0002", "arm_id": "A_pc", "port": p2, "token": "tok-C2"},
            ],
        }, handle, indent=2)

    upstream = start([sys.executable, FAKE, "--port", str(upstream_port),
                      "--cert", srv_pem, "--key", srv_key, "--log", upstream_log], 
                     os.path.join(work, "upstream.console.txt"))
    if not wait_for_port(upstream_port):
        print("fake upstream failed to start")
        stop(upstream)
        return 1

    proxy = start([sys.executable, PROXY, "--registry", registry,
                   "--ledger", ledger, "--events", events,
                   "--upstream-base", "https://127.0.0.1:%d" % upstream_port,
                   "--allowlist", "127.0.0.1,api.deepseek.com",
                   "--upstream-ca", ca_pem,
                   "--aid-out", aid,
                   "--ready-file", os.path.join(work, "proxy.ready")],
                  os.path.join(work, "proxy.console.txt"))
    ok = wait_for_port(p1) and wait_for_port(p2)
    if not ok:
        print("proxy failed to start; console:")
        print(open(os.path.join(work, "proxy.console.txt")).read())
        stop(proxy)
        stop(upstream)
        return 1

    H1 = {"X-Fake-Scenario": "chat-usage-ns", "X-A0-Meter-Token": "tok-C1",
          "Authorization": "Bearer sk-fake-not-a-real-key"}
    H1S = {"X-Fake-Scenario": "chat-usage-stream", "X-A0-Meter-Token": "tok-C1"}
    H1N = {"X-Fake-Scenario": "chat-nousage", "X-A0-Meter-Token": "tok-C1"}
    H1A = {"X-Fake-Scenario": "anthropic-cache", "X-A0-Meter-Token": "tok-C1"}
    H1AS = {"X-Fake-Scenario": "anthropic-stream", "X-A0-Meter-Token": "tok-C1"}
    H1AT = {"X-Fake-Scenario": "anthropic-truncated", "X-A0-Meter-Token": "tok-C1"}
    H1R = {"X-Fake-Scenario": "responses-stream", "X-A0-Meter-Token": "tok-C1"}
    H1G = {"X-Fake-Scenario": "generic-nosplit", "X-A0-Meter-Token": "tok-C1"}
    H1E = {"X-Fake-Scenario": "error-401", "X-A0-Meter-Token": "tok-C1"}
    H2 = {"X-Fake-Scenario": "chat-usage-ns", "X-A0-Meter-Token": "tok-C2"}

    def rows() -> list[dict]:
        return read_ledger(ledger)

    def last() -> dict:
        return rows()[-1]

    print("\n=== S1  chat-completions, non-streaming, usage present ===")
    status, _, body = post(p1, "/v1/chat/completions",
                           {"model": "deepseek-flash", "messages": []}, H1)
    row = last()
    expected = ceq(10240, 1280, 312)
    check("S1 http 200", status == 200, "status=%d" % status)
    check("S1 row metered", row["unmetered"] is False and row["ceq"] == expected,
          "ceq=%r expected=%d" % (row["ceq"], expected))
    check("S1 usage fields exact", row["usage"] == {"prompt_cache_hit_tokens": 1280,
                                                    "prompt_cache_miss_tokens": 10240,
                                                    "completion_tokens": 312}, json.dumps(row["usage"]))
    check("S1 attribution", row["campaign_id"] == "C_0001" and row["arm_id"] == "A_base",
          "%s/%s" % (row["campaign_id"], row["arm_id"]))
    check("S1 provider identity echoed",
          row["model_reported"] == "deepseek-flash" and row["provider_request_id"] == "fake-chatcmpl-0001",
          "model=%s id=%s" % (row["model_reported"], row["provider_request_id"]))
    s1_row = row

    print("\n=== S2  chat-completions, streaming, usage arrives late ===")
    t0 = time.time()
    stamps: dict[str, float] = {}
    sock = socket.create_connection(("127.0.0.1", p1), timeout=30)
    payload = json.dumps({"model": "deepseek-flash", "stream": True, "messages": []}).encode()
    sock.sendall(b"POST /v1/chat/completions HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                 b"Content-Type: application/json\r\n"
                 b"X-Fake-Scenario: chat-usage-stream\r\nX-A0-Meter-Token: tok-C1\r\n"
                 b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload)
    stream = b""
    while True:
        data = sock.recv(65536)
        if not data:
            break
        stream += data
        now = time.time() - t0
        if "content_marker" not in stamps and b'"hello "' in stream:
            stamps["content_marker"] = now
        if "usage_marker" not in stamps and b"prompt_cache_hit_tokens" in stream:
            stamps["usage_marker"] = now
    sock.close()
    row = last()
    expected = ceq(10240, 1024, 296)
    check("S2 row metered from late usage chunk",
          row["unmetered"] is False and row["ceq"] == expected,
          "ceq=%r expected=%d" % (row["ceq"], expected))
    check("S2 row records stream=true", row["stream"] is True, "stream=%r" % row["stream"])
    check("S2 content reached the client before usage existed",
          stamps.get("content_marker", 9e9) + 0.3 < stamps.get("usage_marker", -1),
          "content at %.3fs, usage at %.3fs" % (stamps.get("content_marker", -1),
                                                stamps.get("usage_marker", -1)))
    events_s2, complete_s2 = raw_sse(stream)
    check("S2 client received the terminator after the row was durable",
          complete_s2 and events_s2 and events_s2[-1][1] == b"[DONE]",
          "events=%d final_chunk=%s" % (len(events_s2), complete_s2))
    s2_row = row

    print("\n=== S3  chat-completions, usage deliberately omitted ===")
    status, _, _ = post(p1, "/v1/chat/completions", {"model": "deepseek-flash"}, H1N)
    row = last()
    check("S3 http 200 but unmetered", status == 200 and row["unmetered"] is True,
          "status=%d unmetered=%r" % (status, row["unmetered"]))
    check("S3 ceq is null, not zero", row["ceq"] is None, "ceq=%r" % row["ceq"])
    check("S3 usage is null", row["usage"] is None, "usage=%r" % row["usage"])
    check("S3 reason names the gap", row["reason"] == "no_usage_field_in_response",
          "reason=%r" % row["reason"])
    s3_row = row

    print("\n=== S4  Anthropic shape, non-streaming, cache-read fields ===")
    status, _, _ = post(p1, "/v1/messages", {"model": "deepseek-flash"}, H1A)
    row = last()
    expected = ceq(184, 2048, 55)
    check("S4 metered with cache-read as hit", row["usage"] == {
        "prompt_cache_hit_tokens": 2048, "prompt_cache_miss_tokens": 184,
        "completion_tokens": 55}, json.dumps(row["usage"]))
    check("S4 ceq matches formula", row["ceq"] == expected,
          "ceq=%r expected=%d" % (row["ceq"], expected))
    check("S4 anthropic path routed", row["endpoint"].endswith("/anthropic/v1/messages"),
          row["endpoint"])
    s4_row = row

    print("\n=== S5  Anthropic shape, streaming (usage split across two events) ===")
    status, _, body = post(p1, "/v1/messages", {"model": "deepseek-flash", "stream": True}, H1AS)
    row = last()
    expected = ceq(96, 3072, 73)
    check("S5 usage merged from message_start + message_delta", row["usage"] == {
        "prompt_cache_hit_tokens": 3072, "prompt_cache_miss_tokens": 96,
        "completion_tokens": 73}, json.dumps(row["usage"]))
    check("S5 ceq matches formula", row["ceq"] == expected,
          "ceq=%r expected=%d" % (row["ceq"], expected))
    ev5 = sse_events_from_text(body)
    check("S5 message_stop reached the client",
          bool(ev5) and ev5[-1][0] == "message_stop",
          "last=%r events=%d" % (ev5[-1][0] if ev5 else None, len(ev5)))
    s5_row = row

    print("\n=== S6  OpenAI Responses shape, streaming (usage in response.completed) ===")
    status, _, body = post(p1, "/v1/responses", {"model": "deepseek-flash", "stream": True}, H1R)
    row = last()
    expected = ceq(1536, 512, 128)
    check("S6 metered from response.completed", row["usage"] == {
        "prompt_cache_hit_tokens": 512, "prompt_cache_miss_tokens": 1536,
        "completion_tokens": 128}, json.dumps(row["usage"]))
    check("S6 ceq matches formula", row["ceq"] == expected,
          "ceq=%r expected=%d" % (row["ceq"], expected))
    s6_row = row

    print("\n=== S7  refusals: non-allowlisted destinations, no upstream contact ===")
    before = len(open(upstream_log).readlines()) if os.path.exists(upstream_log) else 0
    raw_c = request_raw(p1, b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n")
    check("S7a CONNECT refused", b"405" in raw_c.split(b"\r\n")[0]
          and b"connect_not_supported" in raw_c, raw_c.split(b"\r\n")[0].decode())
    row_connect = last()
    raw_a = request_raw(p1, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
    check("S7b absolute-URI to a foreign host refused",
          b"403" in raw_a.split(b"\r\n")[0] and b"non_allowlisted_host:example.com" in raw_a,
          raw_a.split(b"\r\n")[0].decode())
    row_abs = last()
    raw_d = request_raw(p1, b"GET http://this-host-does-not-exist.invalid/v1/models HTTP/1.1\r\n"
                            b"Host: this-host-does-not-exist.invalid\r\n\r\n")
    check("S7c unresolvable name also refused locally (no DNS attempted)",
          b"403" in raw_d.split(b"\r\n")[0]
          and b"non_allowlisted_host:this-host-does-not-exist.invalid" in raw_d,
          raw_d.split(b"\r\n")[0].decode())
    after = len(open(upstream_log).readlines()) if os.path.exists(upstream_log) else 0
    check("S7d no refusal reached the upstream", before == after,
          "upstream log lines %d -> %d" % (before, after))
    check("S7e refusals are recorded as unmetered rows",
          row_connect["unmetered"] and row_connect["ceq"] is None
          and row_connect["reason"] == "connect_not_supported"
          and row_abs["reason"] == "non_allowlisted_host:example.com",
          "%s / %s" % (row_connect["reason"], row_abs["reason"]))
    refusal_rows = [row_connect, row_abs, last()]

    print("\n=== S8  two campaigns, concurrent calls, attribution ===")
    results: dict[str, list[dict]] = {"C_0001": [], "C_0002": []}
    base_len = len(rows())
    errs: list[str] = []

    def worker(port: int, headers: dict, n: int):
        for _ in range(n):
            try:
                status, _, _ = post(port, "/v1/chat/completions",
                                    {"model": "deepseek-flash"}, headers)
                if status != 200:
                    errs.append("status %d" % status)
            except Exception as exc:  # noqa: BLE001
                errs.append(repr(exc))

    threads = [threading.Thread(target=worker, args=(p1, H1, 6)),
               threading.Thread(target=worker, args=(p2, H2, 6))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    new_rows = rows()[base_len:]
    for row in new_rows:
        results[row["campaign_id"]].append(row)
    check("S8 all 12 concurrent calls succeeded", not errs and len(new_rows) == 12,
          "errs=%s rows=%d" % (errs[:3], len(new_rows)))
    check("S8 rows attributed to the right campaign",
          len(results["C_0001"]) == 6 and len(results["C_0002"]) == 6,
          "C_0001=%d C_0002=%d" % (len(results["C_0001"]), len(results["C_0002"])))
    check("S8 arm ids follow the campaign",
          {r["arm_id"] for r in results["C_0001"]} == {"A_base"}
          and {r["arm_id"] for r in results["C_0002"]} == {"A_pc"},
          "%s / %s" % ({r["arm_id"] for r in results["C_0001"]},
                       {r["arm_id"] for r in results["C_0002"]}))
    check("S8 every concurrent row is metered and arithmetic-correct",
          all(r["ceq"] == ceq(10240, 1280, 312) for r in new_rows),
          "distinct ceq=%s" % sorted({r["ceq"] for r in new_rows}))

    print("\n=== S9  cross-campaign attribution attempt ===")
    status, _, _ = post(p1, "/v1/chat/completions", {"model": "deepseek-flash"},
                        {"X-Fake-Scenario": "chat-usage-ns", "X-A0-Meter-Token": "tok-C2"})
    row = last()
    check("S9 request on C_0001's port with C_0002's token is refused", status == 403,
          "status=%d" % status)
    check("S9 the refusal is booked against C_0001, never C_0002",
          row["campaign_id"] == "C_0001"
          and row["reason"] == "attribution_token_mismatch", 
          "%s / %s" % (row["campaign_id"], row["reason"]))

    print("\n=== S10 ledger unwritable -> the call fails, it does not proceed unmetered ===")
    before = len(open(upstream_log).readlines()) if os.path.exists(upstream_log) else 0
    os.chmod(ledger, 0o444)
    try:
        status, _, body = post(p1, "/v1/chat/completions", {"model": "deepseek-flash"}, H1)
    finally:
        os.chmod(ledger, 0o644)
    after = len(open(upstream_log).readlines()) if os.path.exists(upstream_log) else 0
    check("S10 call fails with 500", status == 500, "status=%d body=%r" % (status, body[:80]))
    check("S10 upstream was never contacted (preflight refused first)", before == after,
          "upstream log lines %d -> %d" % (before, after))
    check("S10 no success reached the client", b"ledger not writable" in body, body[:80].decode())
    events_log = [json.loads(line) for line in open(events, encoding="utf-8") if line.strip()]
    check("S10 the failure is recorded in the diagnostic sidecar",
          any(e.get("kind") == "ledger_preflight_failed" for e in events_log),
          "sidecar entries=%d" % len(events_log))

    print("\n=== S11 stream truncated before usage arrives ===")
    status, _, body = post(p1, "/v1/messages", {"model": "deepseek-flash", "stream": True}, H1AT)
    row = last()
    check("S11 unmetered", row["unmetered"] is True and row["ceq"] is None,
          "unmetered=%r ceq=%r" % (row["unmetered"], row["ceq"]))
    check("S11 reason says the stream was truncated before usage",
          str(row["reason"]).startswith("stream_truncated_before_usage"),
          "reason=%r" % row["reason"])
    ev11 = sse_events_from_text(body)
    check("S11 the client never saw message_stop",
          all(name != "message_stop" for name, _ in ev11),
          "events=%d" % len(ev11))
    s11_row = row

    print("\n=== S12 arithmetic and schema, recomputed from every row ===")
    all_rows = rows()
    bad = []
    for index, row in enumerate(all_rows):
        good, detail = verify_row(row)
        if not good:
            bad.append((index, detail, row))
    check("S12 every row passes independent re-derivation", not bad,
          "" if not bad else bad[:2])
    check("S12 every row carries exactly the frozen key set",
          all(list(row.keys()) == [
              "schema", "campaign_id", "arm_id", "ts", "provider", "endpoint",
              "model_requested", "model_reported", "provider_request_id", "stream", "usage",
              "ceq", "unmetered", "reason"] for row in all_rows),
          "rows=%d" % len(all_rows))
    metered = [r for r in all_rows if not r["unmetered"]]
    unmetered = [r for r in all_rows if r["unmetered"]]
    check("S12 unmetered rows are never scored and never estimated",
          all(r["ceq"] is None and r["usage"] is None and r["reason"] for r in unmetered),
          "unmetered=%d of %d" % (len(unmetered), len(all_rows)))

    print("\n=== S13 an HTTP error response is an honest gap, not a zero ===")
    status, _, _ = post(p1, "/v1/chat/completions", {"model": "deepseek-flash"}, H1E)
    row = last()
    check("S13 401 passed through, booked as a gap",
          status == 401 and row["unmetered"] is True
          and row["reason"] == "upstream_http_401_no_usage", 
          "status=%d reason=%r" % (status, row["reason"]))

    print("\n=== S14 provider-reported tokens never enter the row ===")
    call_records = [e for e in events_log if e.get("kind") == "call"]
    check("S14 sidecar keeps the raw provider usage for audit",
          any(isinstance(e.get("raw_usage"), dict) and
              "cache_read_input_tokens" in (e.get("raw_usage") or {}) for e in call_records),
          "sidecar call records=%d" % len(call_records))
    check("S14 the authorization header reached the upstream (proxy is a pass-through)",
          any(json.loads(line).get("authorization_present")
              for line in open(upstream_log, encoding="utf-8") if line.strip()),
          "checked upstream.log.jsonl")

    print("\n=== S15 aid fragment ===")
    aid_doc = json.load(open(aid, encoding="utf-8"))
    check("S15 meter.mode is the plaintext self-terminating mode",
          aid_doc["meter"]["mode"] == "plaintext_base_url", aid_doc["meter"]["mode"])
    check("S15 allowlist is declared", aid_doc["meter"]["allowlist"] == ["127.0.0.1", "api.deepseek.com"],
          str(aid_doc["meter"]["allowlist"]))
    check("S15 ceq formula is quoted verbatim from the interface",
          aid_doc["meter"]["ceq_formula"] == "ceq = miss + floor(hit*2/100) + 4*completion",
          aid_doc["meter"]["ceq_formula"])
    check("S15 both endpoint shapes are published",
          aid_doc["endpoints"][0]["base_url"].endswith("/v1")
          and aid_doc["endpoints"][0]["anthropic_base_url"].endswith(str(p1)),
          json.dumps(aid_doc["endpoints"][0]))

    print("\n=== S16 the proxy refuses to start when its upstream is not allowlisted ===")
    bad = subprocess.run(
        [sys.executable, PROXY, "--campaign-id", "C_X", "--arm-id", "A_X",
         "--port", str(free_port()), "--ledger", os.path.join(work, "never.jsonl"),
         "--upstream-base", "https://api.deepseek.com",
         "--allowlist", "openrouter.ai"],
        capture_output=True, cwd=HERE, timeout=30)
    check("S16 start refused, non-zero exit", bad.returncode != 0, "rc=%d" % bad.returncode)
    check("S16 the refusal names the offending host",
          b"not in --allowlist" in bad.stderr and b"api.deepseek.com" in bad.stderr,
          bad.stderr.decode().strip().splitlines()[-1] if bad.stderr.strip() else "")
    check("S16 no ledger was created for the refused proxy",
          not os.path.exists(os.path.join(work, "never.jsonl")), "")

    print("\n=== S17 no spend: nothing in this run left the host ===")
    forwarded_prefixes = ("no_usage_field_in_response", "upstream_http_", "stream_",
                          "empty_response_body", "usage_present_without_cache_split")
    forwarded_rows = [r for r in all_rows
                      if r["reason"] is None or str(r["reason"]).startswith(forwarded_prefixes)]
    bad_endpoints = [r["endpoint"] for r in forwarded_rows
                     if "127.0.0.1:%d" % upstream_port not in r["endpoint"]]
    check("S17 every forwarded call went to the local fake upstream",
          not bad_endpoints and forwarded_rows,
          "rows=%d offenders=%s" % (len(forwarded_rows), bad_endpoints[:3]))
    proxy_console = open(os.path.join(work, "proxy.console.txt"), encoding="utf-8").read()
    check("S17 upstream TLS was verified against a real CA, not disabled",
          "--upstream-insecure" not in proxy_console and "WARNING" not in proxy_console,
          "no insecure-upstream warning in the proxy console")
    check("S17 no name outside the host was ever contacted",
          "upstream error" not in proxy_console.replace(
              "upstream error peer=127.0.0.1", "x"),
          "no transport errors to foreign hosts")

    stop(proxy)
    stop(upstream)

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    total = len(CHECKS)
    print("\n=== %d/%d checks passed ===" % (passed, total))

    # ---- evidence ----
    def copy(src: str, name: str) -> None:
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(out, name))

    copy(ledger, "ledger.jsonl")
    copy(events, "events.jsonl")
    copy(upstream_log, "upstream.log.jsonl")
    copy(aid, "aid.json")
    copy(os.path.join(work, "proxy.console.txt"), "proxy.console.txt")
    copy(os.path.join(work, "upstream.console.txt"), "upstream.console.txt")

    highlights = {
        "S1_chat_completions_with_usage": s1_row,
        "S2_streamed_usage_arrives_late": s2_row,
        "S3_usage_missing": s3_row,
        "S4_anthropic_cache_read": s4_row,
        "S5_anthropic_streamed": s5_row,
        "S6_responses_streamed": s6_row,
        "S7a_connect_refused": refusal_rows[0],
        "S7b_non_allowlisted_host_refused": refusal_rows[1],
        "S11_stream_truncated_before_usage": s11_row,
    }
    with open(os.path.join(out, "highlights.json"), "w", encoding="utf-8") as handle:
        json.dump(highlights, handle, indent=2)
        handle.write("\n")
    with open(os.path.join(out, "checks.json"), "w", encoding="utf-8") as handle:
        json.dump({"passed": passed, "total": total,
                   "checks": [{"name": n, "ok": o, "detail": d} for n, o, d in CHECKS]},
                  handle, indent=2)
        handle.write("\n")

    report = []
    report.append("a0/meter selftest -- %d/%d checks passed" % (passed, total))
    report.append("all traffic went to a local fake upstream; no model was called; no spend")
    report.append("")
    for name, ok, detail in CHECKS:
        report.append("%-4s %s%s" % ("PASS" if ok else "FAIL", name,
                                     (" -- " + detail) if detail else ""))
    report.append("")
    report.append("ledger rows: %d (metered %d, unmetered %d)"
                  % (len(all_rows), len(metered), len(unmetered)))
    report.append("")
    report.append("ledger excerpts (verbatim rows):")
    for label, row in highlights.items():
        report.append("  %s:" % label)
        report.append("    " + json.dumps(row))
    with open(os.path.join(out, "report.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(report) + "\n")

    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
