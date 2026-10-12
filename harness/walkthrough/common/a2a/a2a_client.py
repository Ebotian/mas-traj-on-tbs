#!/usr/bin/env python3
"""A2A fusion client — submit / wait / fetch for the dual-agent transport.

The fusion (2026-10-12 design, verified in-container):
  A2A carries the round-level request/response; git + refs carry the artifacts.
  Each side holds the OTHER side's share file (endpoint + callerId + secret +
  agentId + workspaceId), mode 600.

Usage:
  a2a_client.py --share SHARE.json send-wait "<text>" [--context ID] [--timeout S] [--out TASK.json]
  a2a_client.py --share SHARE.json submit  "<text>" [--context ID]            # prints task id
  a2a_client.py --share SHARE.json wait    <task-id> [--timeout S] [--out T]

Exit: 0 completed; 3 failed/canceled (RETRYABLE — send a new message in the
same context); 4 timeout (still working — widen the window before retrying).

Lessons from the fusion demo (2026-10-12):
  - Normal turns: ~1.5-16 s. One review turn ran >120 s, then a deliberate
    daemon restart interrupted it: the task went FAILED with
    "The run was interrupted by a daemon restart; the workspace owner can
    retry it." The retry (same contextId) completed in 12 s.
  - So: poll generously (default 600 s) and treat FAILED as retryable.
  - contextId keeps the peer agent's native session memory, surviving daemon
    restarts; reuse the context across rounds; omit it to start a new one.
"""
import argparse
import json
import sys
import time
import urllib.request

TERMINAL = ("TASK_STATE_COMPLETED", "TASK_STATE_FAILED", "TASK_STATE_CANCELED")


def call(share, method, params, timeout=30):
    req = urllib.request.Request(
        share["endpoint"],
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
        headers={
            "content-type": "application/json",
            "A2A-Version": "1.0",
            "authorization": "Bearer " + share["secret"],
            "x-qwen-caller-id": share["callerId"],
            "x-qwen-agent-id": share["agentId"],
            "x-qwen-workspace-id": share["workspaceId"],
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def send(share, text, context=None):
    msg = {"role": "ROLE_USER", "messageId": "msg-%d" % (time.time() * 1000), "parts": [{"text": text}]}
    if context:
        msg["contextId"] = context
    task = call(share, "SendMessage", {"message": msg})["result"]["task"]
    return task


def wait(share, tid, timeout_s=600, interval=3, out=None):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        time.sleep(interval)
        t = call(share, "GetTask", {"id": tid})["result"]
        st = t["status"]["state"]
        if st in TERMINAL:
            if out:
                json.dump(t, open(out, "w"), indent=1)
            answer = ""
            arts = t.get("artifacts") or []
            if arts and arts[0].get("parts"):
                answer = arts[0]["parts"][0].get("text", "")
            return st, answer, t
    return "TIMEOUT", "", None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--share", required=True)
    p.add_argument("cmd", choices=["submit", "wait", "send-wait"])
    p.add_argument("arg")
    p.add_argument("--context")
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--out")
    a = p.parse_args()
    share = json.load(open(a.share))
    if a.cmd == "submit":
        t = send(share, a.arg, a.context)
        print(t["id"])
        return 0
    if a.cmd == "wait":
        st, ans, _ = wait(share, a.arg, a.timeout, out=a.out)
        print(st)
        print(ans)
        return 0 if st == "TASK_STATE_COMPLETED" else (3 if st in TERMINAL else 4)
    t = send(share, a.arg, a.context)
    print("task", t["id"], file=sys.stderr)
    st, ans, _ = wait(share, t["id"], a.timeout, out=a.out)
    print(st)
    print(ans)
    return 0 if st == "TASK_STATE_COMPLETED" else (3 if st in TERMINAL else 4)


if __name__ == "__main__":
    sys.exit(main())
