#!/usr/bin/env python3
"""Real calls through the metering proxy, to prove the meter bills a live provider.

Everything else in this directory runs against a local mock. This is the one check that spends
money -- a few tokens per model call -- and it exists because a mock can only ever prove that the
meter agrees with the mock. What it establishes, from artifacts it keeps:

* the proxy's own outbound request is accepted by `api.deepseek.com` (HTTP 200, not the
  `400 ... EOF while parsing a value` that an unframed body draws);
* the ledger row for each model call is **metered**: a real `ceq` and the provider's `usage`
  triple, not `unmetered`/`null`;
* `verify_ledger.py` re-derives every row's `ceq` from its own `usage` and agrees.

Three shapes, because they exercise three different framing decisions on the upstream leg:

| shape | what it proves |
|---|---|
| `GET /v1/models` | the no-body, no-framing-header path still works (and is booked `unmetered`, because a catalogue response reports no usage -- the designed behaviour, not a defect) |
| `POST /v1/chat/completions`, `Content-Length` | the ordinary path, and `usage` parsing on a real response |
| `POST ...`, `Transfer-Encoding: chunked` (`--chunked`) | the re-encoded chunked path: a provider that rejected it would make the chunked branch a liability, so it is worth the extra few tokens to know |

The API key is read from `$DEEPSEEK_API_KEY` by the caller, in the same command, and is never
printed, never written to an artifact, and never put in an argv. The script checks the artifacts
for it afterwards and fails if it finds it.

    export DEEPSEEK_API_KEY=$(awk -F: '/^deepseek:/{sub(/^deepseek:[ ]*/,""); print; exit}' ~/gptapi.md)
    python3 live_check.py --out evidence/live --chunked

The key reaches the proxy only inside an `Authorization: Bearer` header, and the ledger does not
record headers. Set `--model` to anything else and it is a different (bigger) bill.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY = os.path.join(HERE, "meter_proxy.py")
VERIFY = os.path.join(HERE, "verify_ledger.py")
UPSTREAM = "https://api.deepseek.com"


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


def call_content_length(port: int, key: str, token: str, path: str, payload: bytes,
                        timeout: float) -> tuple[int | None, str, bytes, float]:
    started = time.time()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
        conn.request("POST", path, body=payload,
                     headers={"Content-Type": "application/json",
                              "Authorization": "Bearer " + key,
                              "X-A0-Meter-Token": token})
        response = conn.getresponse()
        status, reason, body = response.status, response.reason, response.read()
        conn.close()
    except (OSError, http.client.HTTPException) as exc:
        status, reason, body = None, "%s: %s" % (type(exc).__name__, exc), b""
    return status, reason, body, time.time() - started


def call_chunked(port: int, key: str, token: str, path: str, payload: bytes,
                 timeout: float) -> tuple[int | None, str, bytes, float]:
    """The same request with `Transfer-Encoding: chunked`, so the proxy must re-encode it."""
    half = len(payload) // 2
    wire = (b"POST " + path.encode() + b" HTTP/1.1\r\n"
            + ("Host: 127.0.0.1:%d\r\n" % port).encode()
            + b"Content-Type: application/json\r\n"
            + b"Authorization: Bearer " + key.encode() + b"\r\n"
            + b"X-A0-Meter-Token: " + token.encode() + b"\r\n"
            + b"Transfer-Encoding: chunked\r\n\r\n"
            + b"%x\r\n" % half + payload[:half] + b"\r\n"
            + b"%x\r\n" % (len(payload) - half) + payload[half:] + b"\r\n"
            + b"0\r\n\r\n")
    started = time.time()
    try:
        sock = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        sock.settimeout(timeout)
        sock.sendall(wire)
        raw = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            raw += chunk
        sock.close()
    except OSError as exc:
        return None, "%s: %s" % (type(exc).__name__, exc), b"", time.time() - started
    head, _, body = raw.partition(b"\r\n\r\n")
    first = head.split(b"\r\n")[0].decode("iso-8859-1")
    status = int(first.split()[1]) if len(first.split()) > 1 else None
    return status, first, body, time.time() - started


def call_models(port: int, key: str, token: str, timeout: float) -> tuple[int | None, str, bytes, float]:
    started = time.time()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
        conn.request("GET", "/v1/models",
                     headers={"Authorization": "Bearer " + key, "X-A0-Meter-Token": token})
        response = conn.getresponse()
        status, reason, body = response.status, response.reason, response.read()
        conn.close()
    except (OSError, http.client.HTTPException) as exc:
        status, reason, body = None, "%s: %s" % (type(exc).__name__, exc), b""
    return status, reason, body, time.time() - started


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="live calls through the meter (spend: cents)")
    parser.add_argument("--out", default=os.path.join(HERE, "evidence", "live"))
    parser.add_argument("--model", default="deepseek-flash")
    parser.add_argument("--max-tokens", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--chunked", action="store_true",
                        help="also send the same call with Transfer-Encoding: chunked (one more call)")
    args = parser.parse_args(argv)

    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("DEEPSEEK_API_KEY is not set; export it from ~/gptapi.md in this command")

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    ledger = os.path.join(out, "live_ledger.jsonl")
    events = os.path.join(out, "live_events.jsonl")
    console = os.path.join(out, "live_proxy_diag.txt")
    for path in (ledger, events, console):
        if os.path.exists(path):
            os.remove(path)

    port = free_port()
    cmd = [sys.executable, PROXY, "--campaign-id", "live_check", "--arm-id", "A_live",
           "--port", str(port), "--ledger", ledger, "--events", events,
           "--upstream-base", UPSTREAM, "--allowlist", "api.deepseek.com",
           "--token", "tok-live"]
    handle = open(console, "ab")
    proxy = subprocess.Popen(cmd, stdout=handle, stderr=subprocess.STDOUT, cwd=HERE)
    if not wait_for_port(port):
        handle.close()
        proxy.kill()
        print("proxy failed to start; diagnostics:")
        print(open(console, encoding="utf-8").read())
        return 1

    token = "tok-live"
    payload = json.dumps({"model": args.model, "max_tokens": args.max_tokens,
                          "messages": [{"role": "user", "content": "Reply with the single word: ok"}]}
                         ).encode()

    observations = []
    observations.append(("GET /v1/models (no body, no framing header)", "unmetered-ok",
                         call_models(port, key, token, args.timeout)))
    observations.append(("POST /v1/chat/completions (Content-Length)",
                         "must be metered",
                         call_content_length(port, key, token, "/v1/chat/completions", payload,
                                             args.timeout)))
    if args.chunked:
        observations.append(("POST /v1/chat/completions (Transfer-Encoding: chunked)",
                             "must be metered",
                             call_chunked(port, key, token, "/v1/chat/completions", payload,
                                          args.timeout)))

    time.sleep(0.3)
    proxy.terminate()
    try:
        proxy.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proxy.kill()
    handle.close()

    rows = []
    if os.path.exists(ledger):
        with open(ledger, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
    verify = subprocess.run([sys.executable, VERIFY, ledger, "--json"],
                            capture_output=True, text=True, cwd=HERE)

    lines = ["a0/meter live check -- calls to %s through the metering proxy" % UPSTREAM,
             "model=%s max_tokens=%d  key: read from $DEEPSEEK_API_KEY, never printed or stored"
             % (args.model, args.max_tokens),
             ""]
    for name, requirement, (status, reason, body, elapsed) in observations:
        lines.append("%s  [%s]" % (name, requirement))
        lines.append("  client saw: HTTP %s %s in %.2fs" % (status, reason, elapsed))
        lines.append("  response body (first 200 bytes): %s"
                     % body[:200].decode("utf-8", "replace"))
        lines.append("")
    lines.append("ledger rows: %d" % len(rows))
    for row in rows:
        lines.append("  " + json.dumps(row))
    lines.append("")
    lines.append("verify_ledger.py exit=%d" % verify.returncode)
    lines.append(verify.stdout.strip())
    if verify.returncode != 0:
        lines.append(verify.stderr.strip())

    model_rows = [r for r in rows if r["endpoint"].endswith("/v1/chat/completions")]
    metered = [r for r in model_rows if r["unmetered"] is False and isinstance(r["ceq"], int)]
    expected_calls = 2 + (1 if args.chunked else 0)
    ok = (all(status == 200 for _, _, (status, _, _, _) in observations)
          and len(metered) == expected_calls - 1      # every model call metered
          and verify.returncode == 0)
    lines.append("")
    lines.append("VERDICT: %s"
                 % ("%d live model call(s) metered with a real ceq, ledger re-derives"
                    % len(metered) if ok else "NOT ALL LIVE CALLS WERE METERED -- see above"))

    # The key must not have leaked into any artifact this script produced.
    leaked = []
    for path in (ledger, events, console):
        if os.path.exists(path) and key.encode() in open(path, "rb").read():
            leaked.append(os.path.basename(path))
    lines.append("key absent from every artifact: %s" % (not leaked))
    if leaked:
        lines.append("  KEY FOUND IN: %s" % leaked)
        ok = False

    text = "\n".join(lines) + "\n"
    with open(os.path.join(out, "live_check.txt"), "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
