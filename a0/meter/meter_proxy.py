#!/usr/bin/env python3
"""A1 metering proxy: plaintext HTTP in, `https://api.deepseek.com` over TLS out, ledger always.

Implements `INTERFACE.md` §8. What this component is *for*, stated so the design is checkable:

* Constraint (iv) — "the budget is enforceable at a point the runtime cannot lie about". This
  proxy is that point. It terminates the client's plaintext HTTP itself (so the token fields are
  readable) and it is the only thing that talks TLS to the provider, so the number a campaign is
  charged is read out of the provider's own bytes, never out of the runtime's self-report.
* Constraint (v) — "a silent gap in accounting must be visible as a gap". A response whose usage
  cannot be read produces `unmetered: true, ceq: null, reason: "<which part was unobservable>"`.
  It is never estimated and never silently zero.

Four decisions, each named with the failure it removes:

1. **Attribution is a per-campaign listener, bound before any request exists.**
   Each campaign gets its own TCP port; `(campaign_id, arm_id)` is fixed when the socket is
   bound, so a row's attribution is a property of *where the bytes arrived*, not of anything the
   runtime writes. A path prefix or a header would both be client-supplied data: a runtime that
   drops or forges the field mis-attributes its own spend, and the ledger — whose entire job is
   to be trusted about spend — would inherit that lie. As an independent second check a campaign
   may declare `X-A0-Meter-Token`; a request on campaign C's port without C's token is refused
   *and recorded under C*, so the worst a cross-port request can achieve is a refusal against
   itself.

2. **The destination is not client-controlled.** A `Host` header or an absolute-URI request
   target is *checked* against the allowlist and then discarded; the upstream host is
   `--upstream-base` plus a path from a fixed route table. No client byte selects a destination,
   so the proxy cannot be turned into an open relay, and a misconfigured client is a 403 rather
   than a silent forward.

3. **Fail-closed on the ledger.** `Ledger.preflight()` runs *before* the upstream call, and the
   row is appended and `fsync`ed *before* the response body is released. For a streamed response
   the protocol's terminal event is held back until the row is durable, so a client can never see
   a stream finish successfully for a call that is not in the ledger.

4. **CONNECT is refused, not tunnelled.** §8 makes plaintext termination the metering
   precondition and says `HTTPS_PROXY`/CONNECT is not the authority. A tunnel is bytes the proxy
   cannot read, so accepting it would create a channel whose usage is invisible; the proxy
   answers 405 `connect_not_supported` and books the refusal.

Standard library only. This process never spends anything by itself.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import socket
import ssl
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from meter_core import (  # noqa: E402
    CEQ_FORMULA,
    DEFAULT_ALLOWLIST,
    DEFAULT_MODE,
    DEFAULT_UPSTREAM_BASE,
    SCHEMA_AID,
    SCHEMA_CALL,
    SCHEMA_REGISTRY,
    Ledger,
    LedgerError,
    UsageOutcome,
    build_row,
    identify_fields,
    iter_usage_dicts,
    json_or_none,
    normalize_usage,
    parse_sse_events,
    usage_has_tokens,
)

# Longest prefix wins. `(client path prefix, upstream path prefix)`.
#
# The upstream *host* is deliberately absent from this table: it is `--upstream-base` for every
# route. `/v1/messages` is rewritten onto DeepSeek's Anthropic-compatible prefix, which is what
# lets one listener serve a Claude-Code-shaped client and an OpenAI-shaped client at once.
ROUTES = (
    ("/anthropic/v1/messages", "/anthropic/v1/messages"),
    ("/v1/messages", "/anthropic/v1/messages"),
    ("/v1/chat/completions", "/v1/chat/completions"),
    ("/chat/completions", "/chat/completions"),
    ("/v1/responses", "/v1/responses"),
    ("/responses", "/responses"),
    ("/v1/models", "/v1/models"),
    ("/models", "/models"),
)

ANTHROPIC_ROUTES = ("/v1/messages", "/anthropic/v1/messages")

# Headers whose meaning is confined to one hop. `Content-Length` is **not** one of them: it is a
# payload header, and it used to sit in this set, which is exactly how the proxy came to forward
# bodies with no framing header at all. Framing is re-derived from the bytes actually held, in
# `forward()`, so the client's numbers are dropped and ours are stated.
HOP_BY_HOP = {
    "host", "connection", "proxy-connection", "keep-alive", "transfer-encoding",
    "te", "trailer", "upgrade", "accept-encoding",
}

# Framing headers, stripped from the client's header list because `forward()` re-states them.
FRAMING_HEADERS = {"content-length", "transfer-encoding"}

MAX_HEADER_BYTES = 1 << 20
MAX_REQUEST_BODY = 64 << 20


@dataclass
class Campaign:
    campaign_id: str
    arm_id: str
    port: int
    token: str | None = None
    listen_host: str = "127.0.0.1"


@dataclass
class Config:
    upstream_base: str = DEFAULT_UPSTREAM_BASE
    allowlist: tuple[str, ...] = DEFAULT_ALLOWLIST
    ledger_path: str = "ledger.jsonl"
    events_path: str | None = None
    local_hosts: tuple[str, ...] = ("127.0.0.1", "localhost", "::1", "0.0.0.0")
    upstream_ca: str | None = None
    upstream_insecure: bool = False
    upstream_timeout: float = 600.0
    on_missing_cache_split: str = "unmetered"
    fsync: bool = True
    aid_out: str | None = None


def log(msg: str) -> None:
    sys.stderr.write("%s meter: %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), msg))
    sys.stderr.flush()


# ------------------------------------------------------------------------------------------
# HTTP plumbing (client side, raw sockets -- we need to see the exact bytes)
# ------------------------------------------------------------------------------------------


def read_head(sock: socket.socket) -> bytes:
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            return buf
        buf += chunk
        if len(buf) > MAX_HEADER_BYTES:
            raise ValueError("header block too large")
    return buf


def split_head(raw: bytes) -> tuple[str, list[str], bytes]:
    text = raw.decode("iso-8859-1")
    head, _, rest = text.partition("\r\n\r\n")
    lines = head.split("\r\n")
    return lines[0], lines[1:], rest.encode("iso-8859-1")


def header_get(headers: list[str], name: str) -> str | None:
    for h in headers:
        k, _, v = h.partition(":")
        if k.strip().lower() == name:
            return v.strip()
    return None


def dechunk(raw: bytes) -> bytes:
    out = bytearray()
    pos = 0
    while True:
        end = raw.find(b"\r\n", pos)
        if end < 0:
            return bytes(out)
        try:
            size = int(raw[pos:end].split(b";")[0].strip(), 16)
        except ValueError:
            return bytes(out)
        if size == 0:
            return bytes(out)
        start = end + 2
        out += raw[start:start + size]
        pos = start + size + 2


def chunked_body_complete(raw: bytes) -> bool:
    """Walk the chunk sizes and say whether the terminating zero-length chunk has arrived.

    Stronger than testing `raw.endswith(b"0\\r\\n\\r\\n")`: a chunk whose *data* happens to end in
    those five bytes would stop that test early, and the truncated body would then be forwarded.
    """
    pos = 0
    while True:
        end = raw.find(b"\r\n", pos)
        if end < 0:
            return False
        try:
            size = int(raw[pos:end].split(b";")[0].strip(), 16)
        except ValueError:
            return False
        if size == 0:
            return True
        pos = end + 2 + size + 2
        if pos > len(raw):
            return False


class BodyFramingError(ValueError):
    """The client's body has no usable extent. Never forwarded, never guessed at."""

    def __init__(self, label: str, detail: str) -> None:
        super().__init__("%s: %s" % (label, detail))
        self.label = label
        self.detail = detail


def read_request_body(sock: socket.socket, headers: list[str],
                      already: bytes) -> tuple[bytes, str]:
    """Read the body and return `(body, framing)`.

    `framing` is what the *client* declared: `"content-length"`, `"chunked"`, or `"none"` when it
    declared nothing. It is a statement about the client, not an instruction to the upstream --
    `forward()` re-derives the outbound framing from the bytes below.

    A body whose extent cannot be established is refused rather than forwarded: an undelimited
    body would be framed by guesswork, and a guessed body is a mis-metered one.
    """
    body = already
    te = (header_get(headers, "transfer-encoding") or "").lower()
    if "chunked" in te:
        while not chunked_body_complete(body):
            chunk = sock.recv(65536)
            if not chunk:
                break
            body += chunk
            if len(body) > MAX_REQUEST_BODY:
                raise BodyFramingError("request_body_too_large",
                                       "chunked body exceeded %d bytes" % MAX_REQUEST_BODY)
        if not chunked_body_complete(body):
            raise BodyFramingError("request_body_truncated",
                                   "chunked body ended before its terminating chunk")
        return dechunk(body), "chunked"
    cl = header_get(headers, "content-length")
    if cl is not None:
        try:
            want = int(cl)
        except ValueError:
            raise BodyFramingError("request_body_length_unparsable",
                                   "Content-Length: %r" % cl)
        if want < 0:
            raise BodyFramingError("request_body_length_unparsable", "Content-Length: %d" % want)
        if want > MAX_REQUEST_BODY:
            raise BodyFramingError("request_body_too_large",
                                   "Content-Length %d exceeds %d" % (want, MAX_REQUEST_BODY))
        while len(body) < want:
            chunk = sock.recv(min(65536, want - len(body)))
            if not chunk:
                break
            body += chunk
        if len(body) < want:
            raise BodyFramingError("request_body_truncated",
                                   "declared %d bytes, read %d" % (want, len(body)))
        return body[:want], "content-length"
    if body:
        # e.g. an HTTP/1.0-style POST. A conforming server reads none of these bytes, so
        # forwarding them as-is is what produced the 400 this proxy used to answer every call
        # with; forwarding them under a guessed length would be our invention.
        raise BodyFramingError("request_body_unframed",
                               "%d body bytes arrived with neither Content-Length nor "
                               "Transfer-Encoding: chunked" % len(body))
    return body, "none"


def send_simple(conn: socket.socket, code: int, phrase: str, body: bytes) -> None:
    head = "HTTP/1.1 %d %s\r\nContent-Length: %d\r\n" % (code, phrase, len(body))
    head += "Content-Type: text/plain; charset=utf-8\r\nConnection: close\r\n\r\n"
    try:
        conn.sendall(head.encode("iso-8859-1") + body)
    except OSError:
        pass


def write_chunk(conn: socket.socket, data: bytes) -> None:
    if data:
        conn.sendall(b"%x\r\n" % len(data) + data + b"\r\n")


def end_chunks(conn: socket.socket) -> None:
    conn.sendall(b"0\r\n\r\n")


# ------------------------------------------------------------------------------------------
# Routing / destination policy
# ------------------------------------------------------------------------------------------


def route(path: str) -> tuple[str, bool] | None:
    """Map a client path to `(upstream_path, anthropic_route)`, longest prefix first."""
    best: tuple[int, str, bool] | None = None
    for prefix, upstream_prefix in ROUTES:
        if path == prefix or path.startswith(prefix + "/") or path.startswith(prefix + "?"):
            if best is None or len(prefix) > best[0]:
                best = (len(prefix), upstream_prefix + path[len(prefix):],
                        prefix in ANTHROPIC_ROUTES)
    if best is None:
        return None
    return best[1], best[2]


def split_target(target: str) -> tuple[str | None, str]:
    """Return `(declared_host_or_None, path)` for either request-target form."""
    for scheme in ("http://", "https://"):
        if target.startswith(scheme):
            rest = target[len(scheme):]
            authority, _, path = rest.partition("/")
            return hostname_of(authority), "/" + path
    return None, target


def hostname_of(host_header: str) -> str:
    host = host_header.rsplit("@", 1)[-1]
    if host.startswith("["):
        return (host[1:host.find("]")] if "]" in host else host[1:]).lower()
    return host.split(":")[0].lower()


def host_header_ok(host_header: str | None, cfg: Config) -> bool:
    if not host_header:
        return True  # HTTP/1.0 clients may omit it; routing never depends on it
    name = hostname_of(host_header)
    return name in {h.lower() for h in cfg.local_hosts} or name in {h.lower() for h in cfg.allowlist}


def forward(svc: "Service", method: str, up_host: str, up_port: int, up_path: str,
            headers: list[str], body: bytes, scheme: str,
            client_framing: str = "content-length") -> tuple[int, str, list, Any]:
    """Send one request upstream with framing the proxy states itself.

    `http.client.endheaders(message_body)` adds **no** framing header: it writes the head, then
    the bytes. Every framing header therefore has to come from this function, derived from the
    length of `body` -- the bytes that will actually be written. The client's own framing header
    is not forwarded, and `client_framing` is used only to keep the client's *choice* of framing
    (a chunked request stays chunked); its numbers are never reused.
    """
    if scheme == "https":
        conn: http.client.HTTPConnection = http.client.HTTPSConnection(
            up_host, up_port, timeout=svc.config.upstream_timeout, context=svc.upstream_context())
    else:
        conn = http.client.HTTPConnection(up_host, up_port, timeout=svc.config.upstream_timeout)
    conn.putrequest(method, up_path, skip_host=True, skip_accept_encoding=True)
    for h in headers:
        name, _, value = h.partition(":")
        if name.strip().lower() in HOP_BY_HOP | FRAMING_HEADERS:
            continue
        conn.putheader(name.strip(), value.strip())
    conn.putheader("Host", up_host if up_port in (80, 443) else "%s:%d" % (up_host, up_port))
    # Metering correctness beats transfer savings: a compressed body is not parseable.
    conn.putheader("Accept-Encoding", "identity")
    if client_framing == "chunked":
        conn.putheader("Transfer-Encoding", "chunked")
        conn.endheaders(body, encode_chunked=True)
    elif body or client_framing == "content-length":
        conn.putheader("Content-Length", str(len(body)))
        conn.endheaders(body if body else None)
    else:
        conn.endheaders()
    resp = conn.getresponse()
    return resp.status, resp.reason, list(resp.getheaders()), resp


def usage_from_json_body(payload: Any, anthropic_route: bool, cfg: Config) -> UsageOutcome:
    """Merge every `usage` object in one decoded JSON body, then normalise it."""
    if payload is None:
        return UsageOutcome(None, "none", "unparseable_response_body", None)
    merged: dict = {}
    for usage in iter_usage_dicts(payload):
        if not usage_has_tokens(usage):
            continue
        for key, value in usage.items():
            if value is not None:
                merged[key] = value
    if not merged:
        return UsageOutcome(None, "none", "no_usage_field_in_response", None)
    return normalize_usage(merged, anthropic_route=anthropic_route,
                           on_missing_cache_split=cfg.on_missing_cache_split)


def carries_final_usage(payload: Any, event_name: str | None) -> bool:
    """Is this event's usage object a *final* report, rather than an initial snapshot?

    Anthropic's `message_start.message.usage` carries `output_tokens: 1` as a placeholder; if it
    counted as final, a stream cut right after it would book a completion of one token. The
    OpenAI Responses API carries partial usage on `response.in_progress`; only
    `response.completed` is final. A top-level `usage` is final by construction.
    """
    if not isinstance(payload, dict):
        return False
    for path in (("usage",), ("message", "usage"), ("response", "usage")):
        node: Any = payload
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
        if not isinstance(node, dict) or not usage_has_tokens(node):
            continue
        if path == ("message", "usage"):
            continue
        if path == ("response", "usage") and event_name not in (None, "response.completed"):
            continue
        return True
    return False


# ------------------------------------------------------------------------------------------
# Service
# ------------------------------------------------------------------------------------------


@dataclass
class Service:
    config: Config
    ledger: Ledger
    stats: dict = field(default_factory=lambda: {
        "calls": 0, "metered": 0, "unmetered": 0, "refused": 0, "ledger_failures": 0,
    })
    _stats_lock: threading.Lock = field(default_factory=threading.Lock)

    def bump(self, key: str, n: int = 1) -> None:
        with self._stats_lock:
            self.stats[key] = self.stats.get(key, 0) + n

    def upstream_context(self) -> ssl.SSLContext | None:
        if not self.config.upstream_base.startswith("https://"):
            return None
        if self.config.upstream_insecure:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx
        if self.config.upstream_ca:
            return ssl.create_default_context(cafile=self.config.upstream_ca)
        return ssl.create_default_context()

    def note(self, record: dict) -> None:
        """Diagnostic sidecar. Never authoritative, never fatal."""
        if self.config.events_path:
            self.ledger.append_best_effort(record, self.config.events_path)


def book(svc: Service, row: dict) -> bool:
    """Durably append one row. False means the ledger is unwritable -- the call must not succeed."""
    try:
        svc.ledger.append(row)
        return True
    except LedgerError as exc:
        svc.bump("ledger_failures")
        svc.note({"kind": "ledger_write_failed", "booked": False, "error": str(exc),
                  "row_pending": row})
        log("LEDGER WRITE FAILED: %s" % exc)
        return False


# ------------------------------------------------------------------------------------------
# Request handling
# ------------------------------------------------------------------------------------------


def handle_request(conn: socket.socket, peer: str, campaign: Campaign, svc: Service) -> None:
    cfg = svc.config
    raw = read_head(conn)
    if not raw:
        return
    request_line, headers, rest = split_head(raw)
    parts = request_line.split()
    if len(parts) != 3:
        send_simple(conn, 400, "Bad Request", b"a0-meter: malformed request line\n")
        return
    method, target, _version = parts

    declared_host, path = split_target(target)
    host_header = header_get(headers, "host")
    query = ""
    if "?" in path:
        path, _, query = path.partition("?")

    def refuse(code: int, phrase: str, label: str, detail: str) -> None:
        svc.bump("refused")
        svc.note({"kind": "refusal", "campaign_id": campaign.campaign_id,
                  "arm_id": campaign.arm_id, "peer": peer, "method": method,
                  "target": target, "reason": label})
        endpoint = target if declared_host is not None else (
            "http://%s%s" % (host_header, path) if path.startswith("/") and host_header
            else target)
        row = build_row(
            campaign_id=campaign.campaign_id, arm_id=campaign.arm_id, endpoint=endpoint,
            model_requested=None, model_reported=None, provider_request_id=None,
            stream=False, outcome=UsageOutcome(None, "refused", label), reason=label)
        book(svc, row)
        send_simple(conn, code, phrase,
                    ("a0-meter: %s\nreason=%s\n" % (detail, label)).encode())

    if method.upper() == "CONNECT":
        refuse(405, "Method Not Allowed", "connect_not_supported",
               "CONNECT tunnels cannot be metered; point the runtime's base_url at this proxy")
        return

    if declared_host is not None and declared_host not in {h.lower() for h in cfg.allowlist}:
        refuse(403, "Forbidden", "non_allowlisted_host:%s" % declared_host,
               "destination %s is not on the meter allowlist" % declared_host)
        return

    if not host_header_ok(host_header, cfg):
        refuse(403, "Forbidden", "host_header_not_allowlisted:%s" % host_header,
               "Host header %s is not this proxy" % host_header)
        return

    routed = route(path)
    if routed is None:
        refuse(403, "Forbidden", "path_not_routed:%s" % path,
               "path %s is not a metered route" % path)
        return
    up_path, anthropic_route = routed
    if query:
        up_path = up_path + "?" + query

    if campaign.token is not None and header_get(headers, "x-a0-meter-token") != campaign.token:
        refuse(403, "Forbidden", "attribution_token_mismatch",
               "request on campaign %s's port lacks that campaign's attribution token"
               % campaign.campaign_id)
        return

    try:
        body, client_framing = read_request_body(conn, headers, rest)
    except BodyFramingError as exc:
        # A body we cannot delimit is a body we cannot forward honestly. Refused *and* recorded,
        # like every other refusal, so an unframed client is visible in the ledger.
        refuse(400, "Bad Request", exc.label, exc.detail)
        log("body framing refused peer=%s label=%s detail=%s"
            % (peer, exc.label, exc.detail))
        return
    except (OSError, ValueError) as exc:
        send_simple(conn, 400, "Bad Request", b"a0-meter: bad request body\n")
        log("body read failed peer=%s: %s" % (peer, exc))
        return

    req_json = json_or_none(body) if body else None
    model_requested = req_json.get("model") if isinstance(req_json, dict) else None
    stream_requested = bool(req_json.get("stream")) if isinstance(req_json, dict) else False

    # Fail closed *before* spending: an unwritable ledger stops the call here, not after it.
    try:
        svc.ledger.preflight()
    except LedgerError as exc:
        svc.bump("ledger_failures")
        svc.note({"kind": "ledger_preflight_failed", "campaign_id": campaign.campaign_id,
                  "arm_id": campaign.arm_id, "path": path, "error": str(exc)})
        log("LEDGER PREFLIGHT FAILED, refusing call before contacting upstream: %s" % exc)
        send_simple(conn, 500, "Internal Server Error",
                    b"a0-meter: ledger not writable; call refused rather than unmetered\n")
        return

    base = urlsplit(cfg.upstream_base)
    up_host = base.hostname or ""
    up_port = base.port or (443 if base.scheme == "https" else 80)
    endpoint = "%s://%s%s" % (base.scheme, base.netloc, up_path)

    svc.bump("calls")
    try:
        status, reason_phrase, resp_headers, resp = forward(
            svc, method, up_host, up_port, up_path, headers, body, base.scheme, client_framing)
    except (OSError, http.client.HTTPException) as exc:
        label = "upstream_unreachable:%s" % type(exc).__name__
        svc.bump("unmetered")
        book(svc, build_row(
            campaign_id=campaign.campaign_id, arm_id=campaign.arm_id, endpoint=endpoint,
            model_requested=model_requested, model_reported=None, provider_request_id=None,
            stream=stream_requested, outcome=UsageOutcome(None, "transport", label), reason=label))
        send_simple(conn, 502, "Bad Gateway", b"a0-meter: upstream unreachable\n")
        log("upstream error peer=%s endpoint=%s err=%s" % (peer, endpoint, exc))
        return

    content_type = ""
    content_encoding = None
    request_id_header = None
    for key, value in resp_headers:
        lowered = key.lower()
        if lowered == "content-type":
            content_type = value.lower()
        elif lowered == "content-encoding" and value.lower() not in ("", "identity"):
            content_encoding = value.lower()
        elif lowered in ("x-request-id", "x-ds-request-id") and request_id_header is None:
            request_id_header = value

    is_sse = "text/event-stream" in content_type
    stream_flag = bool(is_sse or stream_requested)
    out_headers = [(k, v) for k, v in resp_headers
                   if k.lower() not in ("connection", "keep-alive", "proxy-connection",
                                        "transfer-encoding", "content-length")]

    if content_encoding is not None:
        # We forced `Accept-Encoding: identity` upstream; if the provider compressed anyway the
        # body is not parseable. Pass it through intact and book the honest gap.
        body_bytes = resp.read()
        outcome = UsageOutcome(None, "transport",
                               "content_encoding_%s_not_parseable" % content_encoding)
        svc.bump("unmetered")
        commit_nonstream(svc, conn, campaign, endpoint, model_requested, None,
                         request_id_header, stream_flag, outcome, body_bytes, status,
                         reason_phrase, out_headers)
        return

    if not is_sse:
        body_bytes = resp.read()
        payload = json_or_none(body_bytes) if body_bytes else None
        ident = identify_fields(payload)
        outcome = usage_from_json_body(payload, anthropic_route, cfg)
        if outcome.usage is None:
            # A body that yields no usage says nothing about the status by itself, and an audit
            # reads the status off the row. So a non-2xx must name it -- whether the body was
            # JSON without a `usage` object or not JSON at all (a gateway page, a truncated
            # body). `unparseable_response_body` alone cannot tell a 401 from a 500.
            no_usage_reason = outcome.unmetered_reason in ("no_usage_field_in_response",
                                                           "unparseable_response_body")
            if status >= 400 and no_usage_reason:
                outcome = UsageOutcome(None, "none", "upstream_http_%d_no_usage" % status,
                                       outcome.raw)
            elif not body_bytes:
                outcome = UsageOutcome(None, "none", "empty_response_body", None)
        svc.bump("metered" if outcome.usage is not None else "unmetered")
        commit_nonstream(svc, conn, campaign, endpoint, model_requested,
                         ident["model"] or None, ident["request_id"] or request_id_header,
                         stream_flag, outcome, body_bytes, status, reason_phrase, out_headers)
        return

    relay_stream(svc, conn, resp, out_headers, status, reason_phrase, campaign, endpoint,
                 model_requested, request_id_header, anthropic_route)


def commit_nonstream(svc: Service, conn: socket.socket, campaign: Campaign, endpoint: str,
                     model_requested: Any, model_reported: Any, provider_request_id: Any,
                     stream_flag: bool, outcome: UsageOutcome, body: bytes, status: int,
                     reason_phrase: str, out_headers: list[tuple[str, str]]) -> None:
    """Durable ledger append first; only then is the client allowed to see the response."""
    row = build_row(
        campaign_id=campaign.campaign_id, arm_id=campaign.arm_id, endpoint=endpoint,
        model_requested=model_requested, model_reported=model_reported,
        provider_request_id=provider_request_id, stream=stream_flag, outcome=outcome,
        reason=outcome.unmetered_reason)
    if not book(svc, row):
        send_simple(conn, 500, "Internal Server Error",
                    b"a0-meter: ledger write failed; response withheld (fail-closed)\n")
        return
    svc.note({"kind": "call", "booked": True, "campaign_id": campaign.campaign_id,
              "arm_id": campaign.arm_id, "endpoint": endpoint, "status": status,
              "streamed": False, "usage_source": outcome.source, "raw_usage": outcome.raw,
              "row_ceq": row["ceq"], "unmetered": row["unmetered"], "reason": row["reason"]})
    head = "HTTP/1.1 %d %s\r\n" % (status, reason_phrase)
    for key, value in out_headers:
        head += "%s: %s\r\n" % (key, value)
    head += "Content-Length: %d\r\nConnection: close\r\n\r\n" % len(body)
    conn.sendall(head.encode("iso-8859-1") + body)


def relay_stream(svc: Service, conn: socket.socket, resp: Any, out_headers: list[tuple[str, str]],
                 status: int, reason_phrase: str, campaign: Campaign, endpoint: str,
                 model_requested: Any, request_id_header: str | None,
                 anthropic_route: bool) -> None:
    """Relay an SSE response while reading usage out of it.

    Hold-back rule: once the protocol's terminal event appears, or the first *final* usage event
    appears, nothing further is shown to the client until the ledger row for this call is
    durable. A client that receives all its content but no terminator treats the call as failed,
    which is exactly the fail-closed semantics we want. Content that precedes the hold point is
    released immediately, so streaming fidelity is unaffected until the end of the stream.
    """
    head = "HTTP/1.1 %d %s\r\n" % (status, reason_phrase)
    for key, value in out_headers:
        if key.lower() in ("content-length", "transfer-encoding"):
            continue
        head += "%s: %s\r\n" % (key, value)
    head += "Transfer-Encoding: chunked\r\nConnection: close\r\n\r\n"
    conn.sendall(head.encode("iso-8859-1"))

    buf = bytearray()
    parse_pos = 0
    forward_pos = 0
    hold_pos: int | None = None
    row_written = False
    merged: dict = {}
    identity = {"model": None, "request_id": None}
    final_usage_seen = False
    terminator_seen = False
    read_error: str | None = None

    def flush(upto: int) -> None:
        nonlocal forward_pos
        if upto > forward_pos:
            write_chunk(conn, bytes(buf[forward_pos:upto]))
            forward_pos = upto

    def reason_for_gap() -> tuple[None, str, str | None]:
        """Why a stream that never reported final usage is unmetered. Says *which* way it failed."""
        if read_error is not None:
            return None, "stream_truncated_before_usage:%s" % read_error, None
        if not terminator_seen:
            return None, "stream_truncated_before_usage", None
        return None, "stream_ended_without_usage", None

    def write_row(final: bool) -> str:
        """Returns 'written' | 'deferred' | 'failed'."""
        nonlocal row_written
        if row_written:
            return "written"
        outcome = (normalize_usage(merged, anthropic_route=anthropic_route,
                                   on_missing_cache_split=svc.config.on_missing_cache_split)
                   if merged else UsageOutcome(None, "stream", "stream_ended_without_usage"))
        if not final_usage_seen:
            # Nothing in this stream claimed to be a *final* usage report. Anthropic's
            # `message_start` alone would normalise to a complete-looking triple with
            # `output_tokens: 1`; booking that would under-count a truncated call, so a stream
            # is only ever charged on a figure the provider marked final.
            if not final:
                return "deferred"
            _, reason, raw = reason_for_gap()
            outcome = UsageOutcome(None, outcome.source, reason, raw)
        elif outcome.usage is None:
            outcome = UsageOutcome(None, outcome.source,
                                   outcome.unmetered_reason or "stream_usage_incomplete",
                                   outcome.raw)
        row = build_row(
            campaign_id=campaign.campaign_id, arm_id=campaign.arm_id, endpoint=endpoint,
            model_requested=model_requested, model_reported=identity["model"] or None,
            provider_request_id=identity["request_id"] or request_id_header,
            stream=True, outcome=outcome, reason=outcome.unmetered_reason)
        if not book(svc, row):
            return "failed"
        row_written = True
        svc.note({"kind": "call", "booked": True, "campaign_id": campaign.campaign_id,
                  "arm_id": campaign.arm_id, "endpoint": endpoint, "status": status,
                  "streamed": True, "usage_source": outcome.source, "raw_usage": outcome.raw,
                  "row_ceq": row["ceq"], "unmetered": row["unmetered"], "reason": row["reason"],
                  "terminator_seen_at_row_commit": terminator_seen, "read_error": read_error})
        svc.bump("metered" if outcome.usage is not None else "unmetered")
        return "written"

    while True:
        try:
            chunk = resp.read1(65536)
        except (OSError, http.client.HTTPException) as exc:
            read_error = type(exc).__name__
            break
        if not chunk:
            break
        buf += chunk
        events, parse_pos = parse_sse_events(buf, parse_pos)
        for ev in events:
            payload = json_or_none(ev.data) if ev.data else None
            event_is_final = False
            if payload is not None:
                for usage in iter_usage_dicts(payload):
                    if not usage_has_tokens(usage):
                        continue
                    for key, value in usage.items():
                        if value is not None:
                            merged[key] = value
                event_is_final = carries_final_usage(payload, ev.name)
                ident = identify_fields(payload)
                for key in ("model", "request_id"):
                    if identity[key] is None and ident[key] is not None:
                        identity[key] = ident[key]
            if ev.is_terminator:
                terminator_seen = True
            if event_is_final:
                final_usage_seen = True

            if row_written:
                flush(len(buf))
                continue
            if hold_pos is not None:
                flush(hold_pos)
            elif event_is_final or ev.is_terminator:
                hold_pos = ev.start
                flush(hold_pos)
            else:
                flush(ev.end)

            if (event_is_final or ev.is_terminator) and hold_pos == ev.start:
                state = write_row(final=ev.is_terminator)
                if state == "failed":
                    # Ledger unwritable: never let this call look successful.
                    try:
                        conn.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    return
                if state == "written":
                    flush(len(buf))

        # Hold-back needs the bytes from the hold point onward, nothing before it. Drop the
        # already-forwarded prefix once it is large, so a long agentic stream does not pin the
        # whole response in memory. Only bytes strictly before `forward_pos` are dropped, and
        # `hold_pos >= forward_pos` whenever a row is still pending, so nothing held is lost.
        if forward_pos > (4 << 20):
            del buf[:forward_pos]
            parse_pos -= forward_pos
            if hold_pos is not None:
                hold_pos -= forward_pos
            forward_pos = 0

    if not row_written:
        if write_row(final=True) == "failed":
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            return
    flush(len(buf))
    try:
        end_chunks(conn)
    except OSError:
        pass


def serve_conn(conn: socket.socket, addr: tuple, campaign: Campaign, svc: Service) -> None:
    peer = "%s:%d" % addr
    try:
        conn.settimeout(svc.config.upstream_timeout + 60)
        handle_request(conn, peer, campaign, svc)
    except (OSError, ValueError) as exc:
        log("connection error peer=%s: %s" % (peer, exc))
    except Exception:  # noqa: BLE001 - a handler must never kill the listener
        log("unhandled error peer=%s\n%s" % (peer, traceback.format_exc()))
    finally:
        try:
            conn.close()
        except OSError:
            pass


def serve_campaign(campaign: Campaign, svc: Service, ready: threading.Event | None = None) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((campaign.listen_host, campaign.port))
    srv.listen(128)
    log("listener up campaign=%s arm=%s %s:%d token=%s"
        % (campaign.campaign_id, campaign.arm_id, campaign.listen_host, campaign.port,
           "yes" if campaign.token else "no"))
    if ready is not None:
        ready.set()
    while True:
        try:
            conn, addr = srv.accept()
        except OSError:
            continue
        threading.Thread(target=serve_conn, args=(conn, addr, campaign, svc), daemon=True).start()


# ------------------------------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------------------------------


def load_registry(path: str) -> tuple[str, list[Campaign]]:
    with open(path, "r", encoding="utf-8") as handle:
        doc = json.load(handle)
    if doc.get("schema") != SCHEMA_REGISTRY:
        raise SystemExit("registry %s: schema must be %s" % (path, SCHEMA_REGISTRY))
    listen_host = doc.get("listen_host", "127.0.0.1")
    campaigns: list[Campaign] = []
    seen_ports: set[int] = set()
    seen_ids: set[str] = set()
    for entry in doc.get("campaigns", []):
        campaign = Campaign(campaign_id=entry["campaign_id"], arm_id=entry["arm_id"],
                            port=int(entry["port"]), token=entry.get("token"),
                            listen_host=listen_host)
        if campaign.port in seen_ports:
            raise SystemExit("registry: port %d used twice" % campaign.port)
        if campaign.campaign_id in seen_ids:
            raise SystemExit("registry: campaign_id %s used twice" % campaign.campaign_id)
        seen_ports.add(campaign.port)
        seen_ids.add(campaign.campaign_id)
        campaigns.append(campaign)
    if not campaigns:
        raise SystemExit("registry: no campaigns")
    return listen_host, campaigns


def build_aid(cfg: Config, campaigns: list[Campaign]) -> dict:
    endpoints = []
    for c in campaigns:
        host = c.listen_host if c.listen_host != "0.0.0.0" else "127.0.0.1"
        endpoints.append({
            "campaign_id": c.campaign_id, "arm_id": c.arm_id,
            "base_url": "http://%s:%d/v1" % (host, c.port),
            "anthropic_base_url": "http://%s:%d" % (host, c.port),
            "token": c.token,
        })
    return {
        "schema": SCHEMA_AID,
        "meter": {
            "mode": DEFAULT_MODE,
            "allowlist": list(cfg.allowlist),
            "upstream_base": cfg.upstream_base,
            "ledger": os.path.abspath(cfg.ledger_path),
            "row_schema": SCHEMA_CALL,
            "ceq_formula": CEQ_FORMULA,
            "missing_usage": "unmetered:true,ceq:null",
            "connect": "refused",
            "attribution": "per_campaign_listener_port(+optional X-A0-Meter-Token)",
            "on_missing_cache_split": cfg.on_missing_cache_split,
        },
        "endpoints": endpoints,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="A1 metering proxy (INTERFACE.md §8)")
    parser.add_argument("--registry", help="campaign registry json (preferred)")
    parser.add_argument("--campaign-id")
    parser.add_argument("--arm-id")
    parser.add_argument("--port", type=int)
    parser.add_argument("--token")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--ledger", default="ledger.jsonl")
    parser.add_argument("--events", help="diagnostic sidecar jsonl (never authoritative)")
    parser.add_argument("--upstream-base", default=DEFAULT_UPSTREAM_BASE)
    parser.add_argument("--allowlist", default=",".join(DEFAULT_ALLOWLIST),
                        help="comma-separated destination hosts the proxy may connect to")
    parser.add_argument("--local-host", action="append", default=[],
                        help="extra Host-header values that mean 'this proxy'")
    parser.add_argument("--upstream-ca", help="PEM bundle trusted for the upstream TLS leg")
    parser.add_argument("--upstream-insecure", action="store_true",
                        help="TEST ONLY: skip upstream certificate verification")
    parser.add_argument("--upstream-timeout", type=float, default=600.0)
    parser.add_argument("--on-missing-cache-split", choices=("unmetered", "conservative-miss"),
                        default="unmetered")
    parser.add_argument("--no-fsync", action="store_true")
    parser.add_argument("--ready-file")
    parser.add_argument("--aid-out")
    args = parser.parse_args(argv)

    if args.registry:
        _, campaigns = load_registry(args.registry)
        if args.listen_host != "127.0.0.1":
            for campaign in campaigns:
                campaign.listen_host = args.listen_host
    else:
        if not (args.campaign_id and args.arm_id and args.port):
            parser.error("either --registry, or --campaign-id/--arm-id/--port")
        campaigns = [Campaign(args.campaign_id, args.arm_id, args.port, args.token,
                              args.listen_host)]

    allowlist = tuple(h.strip().lower() for h in args.allowlist.split(",") if h.strip())
    if not allowlist:
        parser.error("--allowlist must not be empty (fail closed)")

    base_host = (urlsplit(args.upstream_base).hostname or "").lower()
    if base_host not in allowlist:
        # Refusing to start is the only fail-closed answer: a proxy that can reach an unlisted
        # upstream is not a metering boundary.
        raise SystemExit("refusing to start: upstream host %r is not in --allowlist %s"
                         % (base_host, list(allowlist)))

    local_hosts = tuple(dict.fromkeys(("127.0.0.1", "localhost", "::1", "0.0.0.0")
                                      + tuple(args.local_host) + (base_host,)))

    cfg = Config(upstream_base=args.upstream_base, allowlist=allowlist,
                 ledger_path=args.ledger, events_path=args.events, local_hosts=local_hosts,
                 upstream_ca=args.upstream_ca, upstream_insecure=args.upstream_insecure,
                 upstream_timeout=args.upstream_timeout,
                 on_missing_cache_split=args.on_missing_cache_split, fsync=not args.no_fsync,
                 aid_out=args.aid_out)

    if cfg.upstream_insecure:
        log("WARNING --upstream-insecure is set: upstream certificate verification is OFF")

    ledger = Ledger(cfg.ledger_path, fsync=cfg.fsync)
    ledger.preflight()  # a proxy whose ledger is unwritable must not start at all
    if cfg.events_path:
        # Create it up front so "the sidecar is empty" and "the sidecar is missing" differ.
        open(cfg.events_path, "a", encoding="utf-8").close()
    svc = Service(config=cfg, ledger=ledger)

    if cfg.aid_out:
        with open(cfg.aid_out, "w", encoding="utf-8") as handle:
            json.dump(build_aid(cfg, campaigns), handle, indent=2, sort_keys=True)
            handle.write("\n")

    ready = threading.Event()
    for campaign in campaigns:
        threading.Thread(target=serve_campaign, args=(campaign, svc, ready), daemon=True).start()
    ready.wait(timeout=10)
    log("proxy ready allowlist=%s upstream=%s ledger=%s campaigns=%d"
        % (list(allowlist), cfg.upstream_base, os.path.abspath(cfg.ledger_path), len(campaigns)))
    if args.ready_file:
        with open(args.ready_file, "w", encoding="utf-8") as handle:
            handle.write("ready\n")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
