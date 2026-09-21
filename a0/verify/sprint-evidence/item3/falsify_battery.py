#!/usr/bin/env python3
"""Independent falsification battery for the tool-loop closure claim.

Runs INSIDE a0tl-cli (the closed-network worker) and probes egress shapes the
README's stored evidence does not cover:

  T1  host bridge gateway 172.31.78.1 on common ports (lateral path to the host)
  T2  CONNECT api.deepseek.com:25 via the proxy  -- is the allowlist port-blind?
  T3  CONNECT api.deepseek.com:443 (control: must ALLOW)
  T4  CONNECT example.com:443 (control: must DENY)
  T5  origin-form GET /v1/models with a spoofed Host header
  T6  absolute-form GET http://example.com/v1/models (path-only routing)
  T7  tools available for route manipulation (ip / route / busybox / iptables)
Writes nothing outside /tmp.
"""
import json, socket, subprocess, os, sys

PROXY = ("a0tl-proxy", 8787)
out = {}

def tcp(host, port, t=4.0):
    s = socket.socket(); s.settimeout(t)
    try:
        s.connect((host, port)); return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    finally:
        s.close()

out["T1_gateway"] = {f"172.31.78.1:{p}": tcp("172.31.78.1", p) for p in (22, 80, 443, 2375, 2376, 8787)}

def connect_probe(target, t=6.0):
    s = socket.socket(); s.settimeout(t)
    try:
        s.connect(PROXY)
        s.sendall(f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n".encode())
        head = s.recv(200).decode("iso-8859-1", "replace")
        return head.splitlines()[0] if head else "<no response>"
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    finally:
        s.close()

out["T2_connect_port25"] = connect_probe("api.deepseek.com:25")
out["T2_connect_port22"] = connect_probe("api.deepseek.com:22")
out["T3_connect_443"] = connect_probe("api.deepseek.com:443")
out["T4_connect_example"] = connect_probe("example.com:443")

def http_raw(request, t=6.0):
    s = socket.socket(); s.settimeout(t)
    try:
        s.connect(PROXY)
        s.sendall(request.encode())
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = s.recv(4096)
            if not chunk: break
            data += chunk
        return data.decode("iso-8859-1", "replace").split("\r\n\r\n")[0][:300]
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    finally:
        s.close()

out["T5_origin_host_spoof"] = http_raw(
    "GET /v1/models HTTP/1.1\r\nHost: example.com\r\nConnection: close\r\n\r\n")
out["T6_absolute_form"] = http_raw(
    "GET http://example.com/v1/models HTTP/1.1\r\nHost: example.com\r\nConnection: close\r\n\r\n")

tools = {}
for cmd in (["ip", "-V"], ["route"], ["busybox"], ["iptables", "-L", "-n"], ["nsenter", "--version"]):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        tools[cmd[0]] = {"rc": p.returncode, "out": (p.stdout or p.stderr)[:120]}
    except FileNotFoundError:
        tools[cmd[0]] = "not found"
    except Exception as e:
        tools[cmd[0]] = f"{type(e).__name__}: {e}"
out["T7_tools"] = tools

print(json.dumps(out, indent=1, sort_keys=True))
