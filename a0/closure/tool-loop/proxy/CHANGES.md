# Proxy variant used by the tool-loop closure

`allowlist_proxy.py` in this directory is a **byte-identical copy** of
`a0/notes/exit-closed/proxy-closure/proxy/allowlist_proxy.py`
(sha256 `3f2a9302adc2d30b578f0be9538ea2ad00146f81b43dc21453522a6c3e6dc1e5`).
The upstream file is only read; it is never written to.

`allowlist_proxy.responses.py` is the variant this workstream runs. It differs
from that copy in **two** places:

**1. One route** (what makes the codex lane work over the plaintext door):

```
@@ ROUTES
     ("/v1/messages", "api.deepseek.com", "/anthropic"),
     ("/v1/models", "api.deepseek.com", ""),
     ("/v1/chat/completions", "api.deepseek.com", ""),
+    # codex 0.155.1 speaks the Responses wire and appends /v1/responses to
+    # `base_url`; without this route the codex lane gets 403 reason=no_route.
+    ("/v1/responses", "api.deepseek.com", ""),
```

Why: codex 0.155.1 is Responses-only, so a `base_url` pointed at the proxy
plaintext listener makes it `POST /v1/responses`. The unmodified proxy's route
table has no such prefix and answers `403 a0pc-proxy: path not on allowlist`
with `event=deny ... reason=no_route` in its log. Measured, not inferred:
`evidence/02_codex_vs_unmodified_proxy.log`.

Note this is the *plaintext base_url* route only. A lane that instead sets
`HTTPS_PROXY` and keeps `base_url = https://api.deepseek.com/v1` needs **no
allowlist change at all** for codex: the request is tunnelled by the existing
`CONNECT api.deepseek.com:443` rule and the proxy never sees the path. Both
routes are exercised in `evidence/`.

**2. CONNECT matches host *and* port** (hardening; 2026-09-21, §"port pin"
below):

```
-# Hosts reachable through CONNECT. Everything else is denied.
-ALLOW_CONNECT = {
-    h.strip()
-    for h in os.environ.get(
-        "PROXY_ALLOW", "api.deepseek.com,openrouter.ai"
-    ).split(",")
-    if h.strip()
-}
+CONNECT_DEFAULT_PORT = 443
+
+def parse_allow_connect(raw):        # `host` or `host:port` -> {(host, port)}
+    ...
+def parse_connect_target(target):    # `host:port` -> (host, port)
+    ...
+ALLOW_CONNECT = parse_allow_connect(
+    os.environ.get("PROXY_ALLOW", "api.deepseek.com,openrouter.ai"))
@@ handle_connect
-    host, _, port = target.rpartition(":")
-    port = int(port or 443)
-    if host not in ALLOW_CONNECT:
+    host, port = parse_connect_target(target)
+    if host is None or (host, port) not in ALLOW_CONNECT:
```

A bare host in `PROXY_ALLOW` (or in a `CONNECT` target) still means port 443,
so the topology's `ALLOW_CONNECT=api.deepseek.com,openrouter.ai` is unchanged
in effect and both are pinned to the TLS endpoint. The whole change is
`diff -u proxy/allowlist_proxy.py proxy/allowlist_proxy.responses.py`.

## The port pin: what was wrong, what was measured

The original matches the CONNECT target by **host name only**
(`if host not in ALLOW_CONNECT`), so the allowlist meant *every TCP port on
`api.deepseek.com`*, not `api.deepseek.com:443`. An independent verifier found
it (`a0/verify/sprint-evidence/VERDICT.md`, item 3); `run/connect_port_probe.py`
re-measured it from inside the worker before changing anything, and the tunnel
turned out to be a **raw byte pipe**, so the difference is reachability, not
documentation:

```
BEFORE (port-blind)                       AFTER (host:port pinned)
CONNECT api.deepseek.com:443 -> 200       200   (control: intended endpoint, unchanged)
CONNECT api.deepseek.com:25  -> 200       403
CONNECT api.deepseek.com:80  -> 200       403
CONNECT api.deepseek.com:8443-> 200       403
CONNECT api.deepseek.com:22  -> timeout   403
CONNECT api.deepseek.com     -> <no response>   200  (bare host = :443)
CONNECT example.com:443      -> 403       403   (control: not allowlisted)
```

The 200s were not "the same TLS endpoint on another port". Through the
port-blind tunnel:

* `api.deepseek.com:25` completed a **TLS 1.3 handshake** and presented the real
  `CN=api.deepseek.com` certificate — so the client gets a live, un-inspected
  channel that no rule named;
* `api.deepseek.com:80` answered a **plaintext** `GET /` with
  `HTTP/1.1 302 Found` (`Server: TencentEdgeOne`) — so the tunnel carries
  non-TLS protocols too, and the client is not obliged to speak TLS at all.

That is the measurement that decided the question in favour of hardening rather
than justifying: "the extra ports are effectively the same TLS endpoint" is
false here (they are a raw channel to whatever the host listens on, and the
non-443 ones are not covered by any written rule), and the exposure is not a
property this workstream can bound — it depends on a third party's port
inventory, which is exactly the kind of thing the allowlist exists not to
depend on.

Evidence, all from inside `a0tl-cli` (peer `172.31.78.2`, no model calls):
`evidence/portpin/connect_port_probe.{before,after}.json`,
`evidence/portpin/inlane_probe.after.json`, and the enforcement point's own
record in `evidence/portpin/proxy-window.txt` (`target=api.deepseek.com:25
decision=ALLOW tunnel=open` before / `decision=DENY` after, same peer, same
listener).

Two notes for a reviewer:

* the `--privileged` worker is the only thing on `a0tl-internal`, and this change
  does not touch that; it narrows one decision the proxy makes;
* a bare-host `CONNECT api.deepseek.com` used to raise
  `event=error ... invalid literal for int()` and return nothing at all (the
  old `int(port or 443)`, where `port` held the host name after `rpartition`).
  It now gets a clean 200 from the default port. That was a side effect of the
  same line, fixed with it.
