"""One metering-proxy listener per campaign, and the OpenAI-compatible client.

Two responsibilities, both on the *harness* side of the boundary:

* ``MeterProxy`` — supervises ``a0/meter/meter_proxy.py`` for exactly one
  campaign, on exactly one port, with the ledger and the ``AID_r`` fragment in
  the campaign's own directory.  The proxy's startup is fail-closed
  (``a0/meter/README.md`` §4), so "the proxy is up" already means "it can book
  what it spends".  The upstream leg goes straight to the provider: a framing
  defect made a compensating hop necessary here until `a0/meter` `86987235`
  fixed it, and that hop is gone (`a0/a1/DEVIATIONS.md` D-A1-3).
* ``chat_completion`` — the model call itself, in the standard library, against
  a caller-supplied ``base_url``.  The A1 runtime's only model access is this
  call against ``http://127.0.0.1:<campaign port>/v1``.

The module is deliberately the *only* place in ``a0/a1`` that opens an HTTP
connection to a model: a harness whose model lane lives in one function can be
read for "is there an unmetered path?".
"""

from __future__ import annotations

import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROXY = REPO_ROOT / "a0" / "meter" / "meter_proxy.py"
DEFAULT_ALLOWLIST = "api.deepseek.com"
DEFAULT_UPSTREAM = "https://api.deepseek.com"


class MeterError(RuntimeError):
    """The proxy could not be brought up, or the ledger cannot be read."""


def free_port() -> int:
    """A port the kernel says is free.  Allocation is a harness responsibility."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def canonical_host_path(path: Optional[Path]) -> Optional[str]:
    """Keep host paths out of the artifacts that leave this machine."""
    if path is None:
        return None
    return str(Path(path).resolve())


@dataclass
class MeterProxy:
    """A single-campaign metering listener."""

    campaign_id: str
    arm_id: str
    work_dir: Path
    port: int = 0
    token: Optional[str] = None
    proxy_script: Path = DEFAULT_PROXY
    upstream_base: str = DEFAULT_UPSTREAM
    allowlist: str = DEFAULT_ALLOWLIST
    python: Path = field(default_factory=lambda: Path(sys.executable))
    #: When False the client may not send the token, which is how the
    #: attribution-refusal control is produced.
    issue_token: bool = True
    process: Optional[subprocess.Popen] = None
    ready: bool = False

    def __post_init__(self) -> None:
        self.work_dir = Path(self.work_dir).resolve()
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.port = self.port or free_port()
        if self.issue_token and not self.token:
            self.token = secrets.token_urlsafe(24)
        self.ledger = self.work_dir / "ledger.jsonl"
        self.events = self.work_dir / "events.jsonl"
        self.aid_out = self.work_dir / "meter.aid.json"
        self.ready_file = self.work_dir / "proxy.ready"
        self.console = self.work_dir / "proxy.console.txt"

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    def command(self, *, port: Optional[int] = None) -> List[str]:
        """The argv, with `--port` overridable for the namespace-side forwarder."""
        return [
            str(self.python),
            str(self.proxy_script),
            "--campaign-id", self.campaign_id,
            "--arm-id", self.arm_id,
            "--port", str(port or self.port),
            "--ledger", str(self.ledger),
            "--events", str(self.events),
            "--aid-out", str(self.aid_out),
            "--upstream-base", self.upstream_base,
            "--allowlist", self.allowlist,
            "--ready-file", str(self.ready_file),
        ] + (["--token", str(self.token)] if self.token else [])

    def start(self, *, timeout: float = 20.0) -> None:
        if self.ready_file.exists():
            self.ready_file.unlink()
        console = self.console.open("wb")
        self.process = subprocess.Popen(
            self.command(), stdout=console, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL
        )
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.ready_file.exists():
                self.ready = True
                return
            if self.process.poll() is not None:
                raise MeterError(
                    f"meter proxy for {self.campaign_id} exited {self.process.returncode}: "
                    f"{(self.console).read_text(errors='replace')[-600:]}"
                )
            time.sleep(0.05)
        raise MeterError(f"meter proxy for {self.campaign_id} did not become ready in {timeout}s")

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

    def aid(self) -> dict:
        return json.loads(self.aid_out.read_text(encoding="utf-8"))

    def call_events(self) -> List[dict]:
        """The proxy's own per-call sidecar, one `kind: "call"` record per upstream call.

        `a0/meter/README.md` §2 is explicit that the sidecar is *diagnostic and
        never authoritative* for spend. It is used here for the one thing it is
        good for: an independent count of the calls the proxy handled, so the
        ledger can be checked for a missing row rather than trusted.
        """
        path = Path(self.events)
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def verify_ledger(self) -> dict:
        """Run `a0/meter/verify_ledger.py` over this campaign's ledger.

        A ledger that only its author can check is not evidence: that program
        recomputes every metered row's `ceq` from the row's own usage and asserts
        the frozen key set and order.
        """
        script = REPO_ROOT / "a0" / "meter" / "verify_ledger.py"
        proc = subprocess.run(
            [sys.executable, str(script), str(self.ledger), "--json"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        return {"returncode": proc.returncode,
                "stdout": (proc.stdout or "").strip()[-2000:],
                "stderr": (proc.stderr or "").strip()[-800:]}

    def ledger_summary(self) -> dict:
        rows = 0
        ceq = 0
        unmetered = 0
        if self.ledger.is_file():
            for line in self.ledger.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                rows += 1
                if row.get("unmetered"):
                    unmetered += 1
                elif isinstance(row.get("ceq"), int):
                    ceq += row["ceq"]
        return {"rows": rows, "ceq": ceq, "unmetered": unmetered, "ledger": str(self.ledger)}


# ---------------------------------------------------------------------------
# the model call
# ---------------------------------------------------------------------------
class ModelCallError(RuntimeError):
    def __init__(self, message: str, *, status: Optional[int] = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


def chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str = "deepseek-flash",
    messages: List[dict],
    token: Optional[str] = None,
    max_tokens: int = 256,
    temperature: float = 0.0,
    timeout: float = 120.0,
    stream: bool = False,
    extra_headers: Optional[Dict[str, str]] = None,
    path: str = "/chat/completions",
) -> dict:
    """One OpenAI-compatible chat completion.  Returns the parsed body.

    ``token`` is the campaign's meter token; when the campaign declares one the
    request must carry it or the proxy refuses (and books the refusal against
    this campaign — ``a0/meter/README.md`` §3).

    ``HTTPS_PROXY`` is deliberately *not* consulted: the whole point of the
    plaintext hop is that the metering boundary is the ``base_url``.
    """
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Host": urllib.parse.urlsplit(base_url).netloc,
    }
    if token:
        headers["X-A0-Meter-Token"] = token
    headers.update(extra_headers or {})
    request = urllib.request.Request(
        base_url.rstrip("/") + path, data=body, headers=headers, method="POST"
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return {"status": response.status, "body": json.loads(raw) if raw else None}
    except urllib.error.HTTPError as exc:
        raise ModelCallError(
            f"model call refused with HTTP {exc.code}",
            status=exc.code,
            body=exc.read().decode("utf-8", errors="replace")[:500],
        ) from exc
    except urllib.error.URLError as exc:
        raise ModelCallError(f"model call failed: {type(exc.reason).__name__}: {exc.reason}") from exc


def probe_direct(host: str, port: int = 443, *, timeout: float = 5.0) -> dict:
    """Try to open a TCP connection *without* the meter.  Used by the probes."""
    started = time.monotonic()
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return {"target": f"{host}:{port}", "result": "REACHED", "seconds": time.monotonic() - started}
    except OSError as exc:
        return {
            "target": f"{host}:{port}",
            "result": f"BLOCKED:{type(exc).__name__}",
            "detail": str(exc),
            "seconds": time.monotonic() - started,
        }


def api_key_from_environment() -> str:
    """The DeepSeek key, read into an env var by the caller, never persisted.

    The key is never written to an artifact and never placed on an argv: this
    function reads the environment the caller exported it into.
    """
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("A0_MODEL_KEY")
    if not key:
        raise MeterError("no model credential in the environment (DEEPSEEK_API_KEY)")
    return key


if __name__ == "__main__":  # pragma: no cover - a convenience, not an interface
    proxy = MeterProxy(campaign_id="C_probe", arm_id="A_probe", work_dir=Path("/tmp/a1meter"))
    proxy.start()
    print(json.dumps({"port": proxy.port, "base_url": proxy.base_url}, indent=1))
    proxy.stop()
