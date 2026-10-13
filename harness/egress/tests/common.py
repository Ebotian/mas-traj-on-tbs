#!/usr/bin/env python3
"""Shared helpers and task-independent rule data for the egress test suite."""
import pathlib
import subprocess
import sys
import time
from typing import Any, Iterator

import yaml

EGRESS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EGRESS))
import rulelib  # noqa: E402,F401  (re-exported for the test files)

ROOT = pathlib.Path("/home/ebt/harbor-runs")
POLICIES = ROOT / "egress" / "policies"
ACTIVE_TASK = "tumor-immune-interface"

# ---------------------------------------------------------------------------
# Task-independent rule data
# ---------------------------------------------------------------------------
# The base layer's required hosts: both model providers + the install chain +
# the neutral probe target. Every task's compose must include all of them.
BASE_REQUIRED: set[str] = {
    "api.deepseek.com",
    "token-plan.cn-beijing.maas.aliyuncs.com",
    "cdn.jsdelivr.net",
    "registry.npmmirror.com",
    "cdn.npmmirror.com",
    "archive.ubuntu.com",
    "security.ubuntu.com",
    "pypi.org",
    "files.pythonhosted.org",
    "example.com",
}

# Engines blacklist (global ban: not date-adjudicable -> fail closed).
# Maintained list of the major publicly-reachable engines; extend when a new
# engine surfaces. Wildcard entries cover subdomain variants.
ENGINES: set[str] = {
    # global
    "google.com", "www.google.com", "*.google.com",
    "bing.com", "www.bing.com", "*.bing.com",
    "duckduckgo.com", "www.duckduckgo.com",
    "html.duckduckgo.com", "lite.duckduckgo.com",
    "yahoo.com", "www.yahoo.com", "search.yahoo.com", "*.yahoo.com",
    "yandex.com", "www.yandex.com", "*.yandex.com", "yandex.ru",
    "startpage.com", "www.startpage.com",
    "qwant.com", "www.qwant.com",
    "brave.com", "search.brave.com",
    "ask.com", "www.ask.com",
    "ecosia.org", "www.ecosia.org",
    "mojeek.com", "www.mojeek.com",
    # China-resident
    "baidu.com", "www.baidu.com", "*.baidu.com",
    "sogou.com", "www.sogou.com",
    "so.com", "www.so.com",
    "sm.cn", "quark.sm.cn",
}

# Behavioural engine URLs for the live matrix (must FAIL to connect).
ENGINE_URLS: list[str] = [
    "https://www.bing.com/",
    "https://www.mojeek.com/",
    "https://www.ecosia.org/",
    "https://www.google.com/",
    "https://duckduckgo.com/",
    "https://html.duckduckgo.com/html/",
    "https://www.baidu.com/",
    "https://search.yahoo.com/",
    "https://yandex.com/",
    "https://www.sogou.com/",
    "https://www.so.com/",
    "https://www.startpage.com/",
    "https://search.brave.com/",
]


def overlays() -> Iterator[tuple[str, Any]]:
    """Yield (stem, parsed) for every per-task overlay under policies/.

    base.yml is the fixed layer and `_`-prefixed files (e.g. _template.yml)
    are templates, not instances - both are excluded by design.
    """
    for p in sorted(POLICIES.glob("*.yml")):
        if p.stem == "base" or p.stem.startswith("_"):
            continue
        yield p.stem, yaml.safe_load(p.read_text())


# ---------------------------------------------------------------------------
# Live-container probe
# ---------------------------------------------------------------------------
PROBE_SRC: str = (
    "import ssl,sys,urllib.request,urllib.error\n"
    "ctx=ssl.create_default_context()\n"
    "try:\n"
    "    r=urllib.request.urlopen(urllib.request.Request(sys.argv[1],headers={'User-Agent':'policy-test'}),timeout=6,context=ctx)\n"
    "    print('OK',r.status)\n"
    "except urllib.error.HTTPError as e:\n"
    "    print('HTTP',e.code)\n"
    "except Exception as e:\n"
    "    print('FAIL',type(e).__name__)\n"
)


def probe(container: str, url: str) -> str:
    """Return 'OK <code>' | 'HTTP <code>' | 'FAIL <type>' from inside the container.

    A single retry absorbs transient hiccups at trial start (observed once on
    an allowed host); denied hosts stay denied either way.
    """
    def once() -> str:
        r = subprocess.run(
            ["docker", "exec", container, "python3", "-c", PROBE_SRC, url],
            capture_output=True, text=True, timeout=30,
        )
        out = (r.stdout or r.stderr).strip().splitlines()
        return out[-1] if out else "EMPTY"

    res = once()
    if res.startswith("FAIL"):
        time.sleep(2)
        res = once()
    return res
