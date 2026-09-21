#!/usr/bin/env python3
"""Offline fake OpenAI-compatible endpoint used to prove kilo's provider is bundled.

Serves /v1/chat/completions (streaming SSE) on 127.0.0.1. Step 1 asks for the
`write` tool; step 2 answers with plain text. No external network is used.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1])
LOGFILE = sys.argv[2]

STATE = {"calls": 0}


def sse(payload):
    return ("data: " + json.dumps(payload) + "\n\n").encode()


def chunk(delta, finish=None):
    return {
        "id": "chatcmpl-fake",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": "deepseek-v4-pro",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        STATE["calls"] += 1
        with open(LOGFILE, "a") as fh:
            fh.write(json.dumps({
                "call": STATE["calls"],
                "path": self.path,
                "model": body.get("model"),
                "stream": body.get("stream"),
                "tools": [t.get("function", {}).get("name") for t in (body.get("tools") or [])][:12],
                "n_messages": len(body.get("messages") or []),
            }) + "\n")

        saw_tool_result = any(m.get("role") == "tool" for m in (body.get("messages") or []))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        if not saw_tool_result:
            self.wfile.write(sse(chunk({"role": "assistant", "content": ""})))
            self.wfile.write(sse(chunk({"tool_calls": [{
                "index": 0, "id": "call_offline_1", "type": "function",
                "function": {"name": "write", "arguments": ""},
            }]})))
            args = json.dumps({
                "filePath": "/tmp/kilo-offline-wt/offline.txt",
                "content": "kilo-offline-ok",
            })
            self.wfile.write(sse(chunk({"tool_calls": [{
                "index": 0, "function": {"arguments": args},
            }]})))
            self.wfile.write(sse(chunk({}, finish="tool_calls")))
            usage = {"prompt_tokens": 1000, "completion_tokens": 40, "total_tokens": 1040}
        else:
            self.wfile.write(sse(chunk({"role": "assistant", "content": "Done."})))
            self.wfile.write(sse(chunk({}, finish="stop")))
            usage = {"prompt_tokens": 50, "completion_tokens": 3, "total_tokens": 53}

        final = chunk({})
        final["choices"] = []
        final["usage"] = usage
        self.wfile.write(sse(final))
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
