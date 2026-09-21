"""Minimal plaintext-HTTP reverse proxy to https://api.deepseek.com.

Purpose: prove that an opencode provider `baseURL` of the form
`http://127.0.0.1:<port>/v1` (plaintext, local) is honoured, by logging every
request line and forwarding it upstream.  Secrets are never logged: the
Authorization header is recorded only as present/absent.
"""
import http.server
import json
import sys
import urllib.request

UPSTREAM = "https://api.deepseek.com"
LOG = sys.argv[2] if len(sys.argv) > 2 else "/dev/stdout"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8099


def record(line):
    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        pass

    def _proxy(self):
        length = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {}
        record(
            json.dumps(
                {
                    "method": self.command,
                    "path": self.path,
                    "host_header": self.headers.get("host"),
                    "authorization_present": bool(self.headers.get("authorization")),
                    "body_model": payload.get("model"),
                }
            )
        )
        request = urllib.request.Request(
            UPSTREAM + self.path,
            data=body or None,
            method=self.command,
            headers={
                key: value
                for key, value in self.headers.items()
                if key.lower() not in {"host", "content-length", "connection"}
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                status = response.status
                headers = list(response.headers.items())
                payload_out = response.read()
        except urllib.error.HTTPError as error:
            status = error.code
            headers = list(error.headers.items())
            payload_out = error.read()
        self.send_response(status)
        for key, value in headers:
            if key.lower() in {"transfer-encoding", "connection", "content-encoding", "content-length"}:
                continue
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload_out)))
        self.end_headers()
        self.wfile.write(payload_out)

    do_GET = _proxy
    do_POST = _proxy


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    record(json.dumps({"proxy": "listening", "port": PORT}))
    server.serve_forever()
