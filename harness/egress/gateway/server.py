#!/usr/bin/env python3
"""Egress gateway HTTP service (v0: explicit host-side gateway).

Endpoints:
  GET /healthz            -> "ok"
  GET /check?url=<u>      -> JSON decision (diagnostic; always 200)
  GET /fetch?url=<u>      -> 200 bytes when allowed; 403/409 JSON otherwise

Every request is appended to gateway/audit/<date>.jsonl as a policy_decision
record. Content is cached sha256-addressed under gateway/cache/.

Run:  python3 server.py --task tumor-immune-interface --bind 172.17.0.1 --port 8788
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import policy as gateway_policy  # noqa: E402
from surfaces import FetchError  # noqa: E402

CACHE_DIR = HERE / "cache"
AUDIT_DIR = HERE / "audit"
_LOCK = threading.Lock()


def _audit(record):
    AUDIT_DIR.mkdir(exist_ok=True)
    day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    with _LOCK:
        with open(AUDIT_DIR / f"{day}.jsonl", "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _cache_paths(key):
    return CACHE_DIR / f"{key}.bin", CACHE_DIR / f"{key}.json"


class Handler(BaseHTTPRequestHandler):
    server_version = "egress-gateway/0.1"
    registry = None

    def log_message(self, fmt, *args):  # keep stdout clean; audit is the log
        pass

    def _json(self, code, obj, extra_headers=None):
        body = json.dumps(obj, ensure_ascii=False, indent=1).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("X-Gateway-Policy", self.registry.policy_version)
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path)
        q = urllib.parse.parse_qs(u.query)
        target = (q.get("url") or [""])[0]

        if u.path == "/healthz":
            self._json(200, {"status": "ok"})
            return
        if u.path not in ("/check", "/fetch"):
            self._json(404, {"error": "not found"})
            return
        if not target:
            self._json(400, {"error": "missing url parameter"})
            return

        t0 = time.time()
        decision = self.registry.decide(target)
        base = {k: decision[k] for k in
                ("url", "allow", "reason", "form", "t_verified", "dates",
                 "resolved", "policy_version", "cutoff")}

        if u.path == "/check":
            _audit(dict(base, op="check", ts=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        latency_ms=int((time.time() - t0) * 1000)))
            self._json(200, base)
            return

        # /fetch
        if not decision["allow"]:
            _audit(dict(base, op="fetch", outcome="denied",
                        ts=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        latency_ms=int((time.time() - t0) * 1000)))
            self._json(403, {"error": decision["reason"], **base})
            return
        if not decision["fetch"]:
            _audit(dict(base, op="fetch", outcome="check_only",
                        ts=datetime.datetime.now(datetime.timezone.utc).isoformat()))
            self._json(409, {"error": decision["reason"], **base})
            return

        key = hashlib.sha256(decision["fetch"]["url"].encode()).hexdigest()
        binf, metaf = _cache_paths(key)
        cache_hit = binf.exists() and metaf.exists()
        try:
            if cache_hit:
                body = binf.read_bytes()
                meta = json.loads(metaf.read_text())
            else:
                body = self.registry.fetch(decision)
                meta = {"sha256": hashlib.sha256(body).hexdigest(),
                        "bytes": len(body), "fetch_url": decision["fetch"]["url"],
                        "t_verified": decision["t_verified"], "ts":
                        datetime.datetime.now(datetime.timezone.utc).isoformat()}
                CACHE_DIR.mkdir(exist_ok=True)
                binf.write_bytes(body)
                metaf.write_text(json.dumps(meta, ensure_ascii=False))
        except FetchError as e:
            _audit(dict(base, op="fetch", outcome="error", error=e.reason,
                        ts=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        latency_ms=int((time.time() - t0) * 1000)))
            self._json(502, {"error": f"upstream fetch failed: {e.reason}", **base})
            return

        _audit(dict(base, op="fetch", outcome="allowed",
                    cache="hit" if cache_hit else "miss",
                    content_sha256=meta["sha256"], content_bytes=meta["bytes"],
                    ts=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    latency_ms=int((time.time() - t0) * 1000)))
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("X-Gateway-Policy", self.registry.policy_version)
        self.send_header("X-Gateway-T-Verified", decision["t_verified"] or "")
        self.send_header("X-Gateway-Sha256", meta["sha256"])
        self.send_header("X-Gateway-Cache", "hit" if cache_hit else "miss")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--bind", default="172.17.0.1")
    ap.add_argument("--port", type=int, default=8788)
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or None
    Handler.registry = gateway_policy.Registry.from_task(args.task, token=token)
    srv = ThreadingHTTPServer((args.bind, args.port), Handler)
    print(f"egress-gateway v0 | task={args.task} "
          f"policy={Handler.registry.policy_version} "
          f"surfaces={[s.kind for s in Handler.registry.surfaces]} "
          f"| http://{args.bind}:{args.port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
