"""Framing tests: the proxy must state a body's framing itself, and must not guess at one.

The defect these pin was invisible to every response-side assertion in the suite: `endheaders`
adds no `Content-Length`, the client's own header was being stripped as "hop-by-hop", and the
mock upstream read zero body bytes and answered from its defaults anyway. So the tests here are
all request-side: what goes on the wire, and what happens to a body whose extent nobody declared.

Layer 1 (`TestForwardFraming`) drives `forward()` with a recording stand-in for
`http.client.HTTPConnection`, so it asserts on the exact header list and body bytes.
Layer 2 (`TestBodyFraming`) drives `read_request_body` over a real socketpair, including the
truncated and unframed cases.
Layer 3 (`test_raw_tap_proof_*`) runs the whole proxy against `raw_tap.py`, a raw socket that
records the bytes the upstream receives -- the proof that does not depend on any mock's parsing.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
METER = os.path.dirname(HERE)
sys.path.insert(0, METER)

import meter_proxy  # noqa: E402
from meter_proxy import BodyFramingError, forward, read_request_body  # noqa: E402

CLIENT_HEADERS = [
    "Content-Type: application/json",
    "Authorization: Bearer sk-not-real",
    "Content-Length: 999",           # deliberately wrong: ours must win
    "Connection: close",             # hop-by-hop: must not be forwarded
    "X-A0-Meter-Token: tok",
]
BODY = b'{"model":"deepseek-flash","messages":[]}'


class RecordingConnection:
    """Stands in for `http.client.HTTPConnection`; records exactly what the proxy sends."""

    instances: list["RecordingConnection"] = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.timeout = host, port, timeout
        self.request_line = None
        self.headers: list[tuple[str, str]] = []
        self.sent: list[bytes] = []
        self.chunked_encoder = None
        RecordingConnection.instances.append(self)

    def putrequest(self, method, path, skip_host=False, skip_accept_encoding=False):
        self.request_line = "%s %s" % (method, path)

    def putheader(self, name, value=None):
        self.headers.append((str(name), str(value)))

    def endheaders(self, message_body=None, encode_chunked=False):
        self.chunked_encoder = encode_chunked
        if message_body:
            self.sent.append(message_body)

    def getresponse(self):
        raise meter_proxy.http.client.HTTPException("stop after the request is built")

    def header(self, name: str) -> str | None:
        for key, value in self.headers:
            if key.lower() == name.lower():
                return value
        return None


@pytest.fixture
def recorder(monkeypatch):
    RecordingConnection.instances = []
    monkeypatch.setattr(meter_proxy.http.client, "HTTPConnection", RecordingConnection)
    monkeypatch.setattr(meter_proxy.http.client, "HTTPSConnection", RecordingConnection)

    class Cfg:
        upstream_timeout = 5.0
        upstream_insecure = False
        upstream_ca = None
        upstream_base = "http://127.0.0.1:1"

    class Svc:
        config = Cfg()

        def upstream_context(self):
            return None

    return Svc()


def build(recorder, body, framing):
    try:
        forward(recorder, "POST", "127.0.0.1", 9999, "/v1/chat/completions",
                CLIENT_HEADERS, body, "http", framing)
    except meter_proxy.http.client.HTTPException:
        pass
    return RecordingConnection.instances[-1]


class TestForwardFraming:
    def test_content_length_is_stated_from_the_body_we_hold(self, recorder):
        conn = build(recorder, BODY, "content-length")
        assert conn.header("Content-Length") == str(len(BODY))
        assert conn.header("Transfer-Encoding") is None
        assert conn.sent == [BODY]

    def test_the_clients_wrong_length_is_not_reused(self, recorder):
        # CLIENT_HEADERS claims 999 bytes; the upstream must be told the truth.
        conn = build(recorder, BODY, "content-length")
        assert conn.header("Content-Length") == str(len(BODY)) != "999"

    def test_hop_by_hop_headers_are_still_dropped(self, recorder):
        conn = build(recorder, BODY, "content-length")
        assert conn.header("Connection") is None
        assert conn.header("Authorization") == "Bearer sk-not-real"
        assert conn.header("Accept-Encoding") == "identity"

    def test_chunked_client_body_is_re_encoded_not_copied(self, recorder):
        conn = build(recorder, BODY, "chunked")
        assert conn.header("Transfer-Encoding") == "chunked"
        assert conn.header("Content-Length") is None
        assert conn.chunked_encoder is True
        assert conn.sent == [BODY]          # the *decoded* body, re-encoded by http.client

    def test_empty_body_with_a_declared_length_is_still_framed(self, recorder):
        conn = build(recorder, b"", "content-length")
        assert conn.header("Content-Length") == "0"
        assert conn.sent == []

    def test_no_body_and_no_declaration_sends_no_framing_header(self, recorder):
        conn = build(recorder, b"", "none")
        assert conn.header("Content-Length") is None
        assert conn.header("Transfer-Encoding") is None

    def test_every_body_is_framed(self, recorder):
        """The regression itself: a non-empty body must never go out unframed."""
        for framing in ("content-length", "chunked"):
            conn = build(recorder, BODY, framing)
            assert conn.header("Content-Length") is not None \
                or conn.header("Transfer-Encoding") is not None, framing


class TestBodyFraming:
    def read(self, raw: bytes) -> tuple[bytes, str]:
        client, server = socket.socketpair()
        try:
            client.sendall(raw)
            client.shutdown(socket.SHUT_WR)
            # Mirror the proxy's own read order: the head is consumed off the socket first, so
            # what `read_request_body` sees on the socket is the body alone.
            line, headers, rest = meter_proxy.split_head(meter_proxy.read_head(server))
            assert line.startswith(("POST", "GET"))
            return read_request_body(server, headers, rest)
        finally:
            client.close()
            server.close()

    def test_content_length(self):
        body, framing = self.read(b"POST /x HTTP/1.1\r\nContent-Length: 4\r\n\r\nabcd")
        assert (body, framing) == (b"abcd", "content-length")

    def test_chunked_is_decoded(self):
        raw = (b"POST /x HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n"
               b"4\r\nabcd\r\n3\r\nefg\r\n0\r\n\r\n")
        assert self.read(raw) == (b"abcdefg", "chunked")

    def test_chunk_data_ending_like_a_terminator_is_not_a_terminator(self):
        # `endswith(b"0\r\n\r\n")` used to end the read early on data like this; the size walk
        # does not.
        raw = (b"POST /x HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n"
               b"5\r\n0\r\n\r\n\r\n0\r\n\r\n")
        assert self.read(raw) == (b"0\r\n\r\n", "chunked")

    def test_empty_body(self):
        assert self.read(b"POST /x HTTP/1.1\r\nContent-Length: 0\r\n\r\n") == (b"", "content-length")

    def test_no_body_no_declaration(self):
        assert self.read(b"GET /v1/models HTTP/1.1\r\nHost: x\r\n\r\n") == (b"", "none")

    def test_unframed_body_is_refused_not_guessed(self):
        with pytest.raises(BodyFramingError) as excinfo:
            self.read(b"POST /x HTTP/1.1\r\nHost: x\r\n\r\n{\"a\":1}")
        assert excinfo.value.label == "request_body_unframed"

    def test_truncated_body_is_refused(self):
        with pytest.raises(BodyFramingError) as excinfo:
            self.read(b"POST /x HTTP/1.1\r\nContent-Length: 10\r\n\r\nshort")
        assert excinfo.value.label == "request_body_truncated"

    def test_truncated_chunked_body_is_refused(self):
        raw = b"POST /x HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n4\r\nabcd\r\n"
        with pytest.raises(BodyFramingError) as excinfo:
            self.read(raw)
        assert excinfo.value.label == "request_body_truncated"

    def test_unparsable_length_is_refused(self):
        with pytest.raises(BodyFramingError) as excinfo:
            self.read(b"POST /x HTTP/1.1\r\nContent-Length: 12abc\r\n\r\nx")
        assert excinfo.value.label == "request_body_length_unparsable"


def test_raw_tap_proof_passes_for_the_current_proxy(tmp_path):
    """The tap proof is the mock-free check: it reads the bytes the upstream received."""
    proc = subprocess.run(
        [sys.executable, os.path.join(METER, "raw_tap.py"), "--proof",
         "--out", str(tmp_path), "--work", str(tmp_path / "work"), "--label", "pytest"],
        capture_output=True, text=True, timeout=300, cwd=METER)
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-2000:]
    payload = json.loads((tmp_path / "framing_pytest.json").read_text())
    assert payload["ok"] is True
    by_shape = {v["shape"][0]: v for v in payload["verdicts"]}
    for shape in ("A", "B"):
        assert by_shape[shape]["framing_header_present"], by_shape[shape]
        assert by_shape[shape]["declared_length_matches_body"], by_shape[shape]
        assert by_shape[shape]["body_identical_to_client"], by_shape[shape]
        assert by_shape[shape]["upstream_status"] == "HTTP/1.1 200 OK"
    assert any(not r["unmetered"] and r["ceq"] for r in payload["ledger_rows"])
