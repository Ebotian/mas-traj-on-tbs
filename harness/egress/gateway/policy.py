#!/usr/bin/env python3
"""Gateway policy: layered rule engine (base mechanisms ∘ task overlay).

Layers (2026-10-10 rulings):
- base.yml `gateway:`          — task-INDEPENDENT mechanism (guards + adapter
  catalog; every enabled surface kind must be in the catalog);
- <task>.yml `gateway:`        — task-related enablement (which surfaces are
  open, with their hosts);
- <task>.yml forbidden_sources — task-related answer-source exclusion, enforced
  INDEPENDENTLY of dates: a designated answer link denies even when its dates
  would pass.

Decision order: declared surface host -> URL-level forbidden check -> parse ->
resolution (dates + immutable fetch spec) -> every date strictly before the
cutoff (rulelib.allowed_by_date; same-day and unknown fail closed).
"""
import hashlib
import pathlib
import re
import sys
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import rulelib  # noqa: E402
from surfaces import FetchError, GithubSurface, NatureSurface  # noqa: E402

POLICIES = HERE.parent / "policies"

_CATALOG: dict[str, type[GithubSurface] | type[NatureSurface]] = {
    "github": GithubSurface,
    "nature": NatureSurface,
}


def _host_of(url: str) -> str:
    return url.split("/", 3)[2].split(":")[0] if "://" in url else ""


class ForbiddenMatcher:
    """Task-related answer-source exclusion, independent of dates.

    Entries: `doi:`/`conceptdoi:` values, host/path patterns, or prose whose
    identifier-like tokens are extracted. A match denies; a non-match says
    nothing (date rules still apply). Matching is deliberately conservative
    (fail closed): over-matching is the safe direction.
    """

    def __init__(self, entries: Any) -> None:
        self.url_patterns: list[str] = []
        self.id_patterns: list[str] = []
        for raw in entries or []:
            e = str(raw).split("#", 1)[0].strip()
            if not e:
                continue
            if " " in e:  # prose entry -> extract identifier-like tokens
                self.id_patterns += re.findall(r"\d[\w.\-/]{4,}", e)
                continue
            if e.startswith(("doi:", "conceptdoi:")):
                val = e.split(":", 1)[1].strip()
                self.id_patterns.append(val)
                if "/" in val:
                    self.id_patterns.append(val.split("/", 1)[1])
                self.id_patterns += re.findall(r"\d{5,}", val)
            elif "/" in e:
                self.url_patterns.append(e.split("://", 1)[-1])
            else:
                self.url_patterns.append(e)

    def match(self, url: str) -> str | None:
        u = url.split("://", 1)[-1]
        for p in self.url_patterns:
            if p and p in u:
                return p
            if "/" in p and p.split("/", 1)[1] in u:
                return p
        for p in self.id_patterns:
            if p and p in u:
                return p
        return None


class Registry:
    def __init__(
        self,
        task: str,
        cutoff_iso: str,
        surfaces: list[Any],
        forbidden: ForbiddenMatcher | None = None,
        policy_version: str = "",
        direct_hosts: set[str] | None = None,
    ) -> None:
        self.task = task
        self.cutoff_iso = cutoff_iso
        self.surfaces = surfaces
        self.forbidden = forbidden or ForbiddenMatcher([])
        self.policy_version = policy_version
        self.direct_hosts = direct_hosts or set()

    @classmethod
    def from_task(cls, task: str, token: str | None = None) -> "Registry":
        base, overlay = rulelib.load_layers(task)
        catalog = set((base.get("gateway") or {}).get("adapters") or _CATALOG)
        cutoff = (overlay.get("temporal_policy") or {}).get("cutoff")
        if not cutoff:
            raise RuntimeError(f"{task}: temporal_policy.cutoff missing")
        surfaces: list[Any] = []
        for spec in (overlay.get("gateway") or {}).get("surfaces", []):
            kind = spec.get("kind")
            if kind not in catalog:
                raise RuntimeError(f"surface kind {kind!r} not in base adapter catalog")
            surfaces.append(_CATALOG[kind](cutoff_iso=cutoff, token=token,
                                           hosts=spec.get("hosts")))
        forbidden = ForbiddenMatcher(overlay.get("forbidden_sources"))
        direct_hosts = set(rulelib.compose(base, overlay))
        ver = hashlib.sha256((POLICIES / f"{task}.yml").read_bytes()).hexdigest()[:12]
        return cls(task, cutoff, surfaces, forbidden=forbidden,
                   policy_version=ver, direct_hosts=direct_hosts)

    def _surface_for(self, url: str) -> Any | None:
        host = _host_of(url)
        for s in self.surfaces:
            if host in s.hosts:
                return s
        return None

    def decide(self, url: str) -> dict[str, Any]:
        """Full decision incl. resolution. Never raises; failures become deny."""
        d: dict[str, Any] = {
            "url": url, "allow": False, "reason": "", "form": None,
            "forbidden": None, "t_verified": None, "dates": {}, "resolved": {},
            "fetch": None, "policy_version": self.policy_version,
            "cutoff": self.cutoff_iso,
        }
        surface = self._surface_for(url)
        if surface is None:
            reason = "host is not a declared gateway surface"
            if _host_of(url) in self.direct_hosts:
                reason += "; host is on the direct allowlist - fetch it directly"
            d["reason"] = reason
            return d
        m = self.forbidden.match(url)
        if m:
            d["forbidden"] = m
            d["reason"] = f"forbidden answer source (task list): {m}"
            return d
        parsed = surface.parse(url)
        if parsed is None:
            d["reason"] = "unparseable or undeclared URL form"
            return d
        d["form"] = parsed["form"]
        try:
            res = surface.resolve(parsed)
        except FetchError as e:
            d["reason"] = f"resolution failed: {e.reason}"
            return d
        d["dates"] = res["dates"]
        d["t_verified"] = res["t_verified"]
        d["resolved"] = res["resolved"]
        bad = [f"{k}={v}" for k, v in res["dates"].items()
               if not rulelib.allowed_by_date(v, self.cutoff_iso)]
        if bad:
            d["reason"] = "post-cutoff date(s): " + ", ".join(bad)
            return d
        if not res["dates"]:
            d["reason"] = "no verifiable dates (fail closed)"
            return d
        d["allow"] = True
        d["fetch"] = res["fetch"]
        d["reason"] = "all dates strictly before cutoff" + (
            "" if res["fetch"] else "; check-only (html pages are not served)")
        return d

    def fetch(self, decision: dict[str, Any]) -> bytes:
        """Fetch content for an allowed decision. Raises FetchError."""
        if not decision.get("allow"):
            raise FetchError("decision is not allowed")
        if not decision.get("fetch"):
            raise FetchError("check-only form (the page content is not served)")
        surface = self._surface_for(decision["url"])
        if surface is None:
            raise FetchError("surface vanished between decide and fetch")
        return surface.fetch(decision["fetch"])
