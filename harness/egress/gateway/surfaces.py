#!/usr/bin/env python3
"""Gateway surface adapters (v1: github, nature).

Design rules (design note SS7):
- strict URL classification: only declared forms parse; anything else denies;
- every reference is resolved to an immutable object (commit sha) or a
  server-side date (repo created/pushed, tag date, article publication date)
  BEFORE any content fetch;
- the content fetch URL is CONSTRUCTED from parsed components, never reused
  from user input (SSRF guard);
- redirects are never followed: any 3xx denies;
- anything ambiguous or failing denies (fail closed).

This module owns parse/resolve/fetch. Date COMPARISON lives in policy.py and
uses the shared rulelib.allowed_by_date, so the strict-fail-closed semantics
have exactly one implementation.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterable

SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class FetchError(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: Any, msg: Any,
                         headers: Any, newurl: Any) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def http_get(url: str, timeout: int = 10, token: str | None = None,
             accept: str | None = None, retries: int = 1) -> tuple[int, bytes]:
    """GET, no redirects, no HTTP-error retries. Connection-level transients
    (SSL EOF etc.) get `retries` extra attempts - the same single-retry policy
    as the container probes. Returns (status, bytes). Raises FetchError."""
    headers = {"User-Agent": "harbor-egress-gateway/0.1"}
    if accept:
        headers["Accept"] = accept
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    attempt = 0
    while True:
        try:
            with _OPENER.open(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if 300 <= e.code < 400:
                raise FetchError(f"redirect blocked: {e.code}")
            raise FetchError(f"http {e.code}")
        except Exception as e:
            if attempt < retries:
                attempt += 1
                time.sleep(1.5)
                continue
            raise FetchError(f"{type(e).__name__}: {str(e)[:120]}")


class GithubSurface:
    kind = "github"
    DEFAULT_HOSTS: set[str] = {"github.com", "www.github.com",
                               "raw.githubusercontent.com", "codeload.github.com"}

    def __init__(self, cutoff_iso: str, token: str | None = None,
                 hosts: Iterable[str] | None = None, timeout: int = 10) -> None:
        self.cutoff_iso = cutoff_iso
        self.token = token
        self.hosts: set[str] = set(hosts) if hosts else set(self.DEFAULT_HOSTS)
        self.timeout = timeout

    # ---------------- api ----------------
    def _api_json(self, path: str) -> dict[str, Any]:
        _, body = http_get("https://api.github.com" + path,
                           timeout=self.timeout, token=self.token,
                           accept="application/vnd.github+json")
        try:
            return json.loads(body)
        except Exception:
            raise FetchError("non-json api response")

    # ---------------- classification ----------------
    def parse(self, url: str) -> dict[str, Any] | None:
        u = urllib.parse.urlsplit(url)
        if u.scheme != "https" or u.query or u.fragment or not u.hostname \
                or u.hostname not in self.hosts:
            return None
        segs = [s for s in u.path.split("/") if s]

        if u.hostname == "raw.githubusercontent.com":
            # /<owner>/<repo>/<ref>/<path...>; multi-segment refs are denied in v0
            if len(segs) >= 4:
                return {"form": "raw", "owner": segs[0], "repo": segs[1],
                        "ref": segs[2], "path": "/".join(segs[3:])}
            return None

        if u.hostname == "codeload.github.com":
            # /<owner>/<repo>/(tar.gz|zip)/<ref>
            if len(segs) == 4 and segs[2] in ("tar.gz", "zip"):
                return {"form": "archive", "owner": segs[0], "repo": segs[1],
                        "fmt": segs[2], "ref": segs[3]}
            return None

        # github.com / www.github.com
        if len(segs) == 2:
            return {"form": "repo", "owner": segs[0], "repo": segs[1]}
        if len(segs) == 4 and segs[2] in ("commit", "commits"):
            return {"form": "commit", "owner": segs[0], "repo": segs[1], "ref": segs[3]}
        if len(segs) == 5 and segs[2] == "releases" and segs[3] == "tag":
            return {"form": "release", "owner": segs[0], "repo": segs[1], "tag": segs[4]}
        if len(segs) == 4 and segs[2] == "archive":
            for fmt in ("tar.gz", "zip"):
                if segs[3].endswith("." + fmt):
                    return {"form": "archive", "owner": segs[0], "repo": segs[1],
                            "fmt": fmt, "ref": segs[3][: -(len(fmt) + 1)]}
            return None
        return None

    # ---------------- resolution (dates + immutable fetch spec) ----------------
    def _resolve_commit(self, owner: str, repo: str, ref: str) -> tuple[str, str]:
        d = self._api_json(f"/repos/{owner}/{repo}/commits/{urllib.parse.quote(ref, safe='')}")
        sha = d.get("sha")
        date = ((d.get("commit") or {}).get("committer") or {}).get("date")
        if not sha or not date:
            raise FetchError("commit resolution incomplete")
        return sha, date

    def resolve(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """Return {'dates': [...], 't_verified': iso, 'resolved': {...}, 'fetch': spec|None}."""
        form, owner, repo = parsed["form"], parsed["owner"], parsed["repo"]
        base = {"owner": owner, "repo": repo, "form": form}

        if form == "repo":
            d = self._api_json(f"/repos/{owner}/{repo}")
            created, pushed = d.get("created_at"), d.get("pushed_at")
            if not created or not pushed:
                raise FetchError("repo dates missing")
            return {
                "dates": {"created_at": created, "pushed_at": pushed},
                "t_verified": pushed,
                "resolved": base,
                "fetch": None,  # html pages are not served in v0 (check-only)
            }

        if form in ("commit", "raw", "archive"):
            sha, date = self._resolve_commit(owner, repo, parsed["ref"])
            resolved = dict(base, ref=parsed.get("ref"), sha=sha)
            if form == "commit":
                fetch: dict[str, Any] = {"url": f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}",
                                         "accept": "application/vnd.github+json"}
            elif form == "raw":
                fetch = {"url": f"https://raw.githubusercontent.com/{owner}/{repo}/{sha}/{parsed['path']}",
                         "accept": None}
                resolved["path"] = parsed["path"]
            else:  # archive
                fetch = {"url": f"https://codeload.github.com/{owner}/{repo}/{parsed['fmt']}/{sha}",
                         "accept": None}
                resolved["fmt"] = parsed["fmt"]
            return {"dates": {"commit": date}, "t_verified": date,
                    "resolved": resolved, "fetch": fetch}

        if form == "release":
            tag = parsed["tag"]
            ref = self._api_json(f"/repos/{owner}/{repo}/git/ref/tags/{urllib.parse.quote(tag, safe='')}")
            obj = ref.get("object") or {}
            if obj.get("type") == "tag":  # annotated tag
                tagobj = self._api_json(f"/repos/{owner}/{repo}/git/tags/{obj.get('sha')}")
                tag_date = ((tagobj.get("tagger") or {}).get("date"))
            else:  # lightweight -> commit
                _, tag_date = self._resolve_commit(owner, repo, obj.get("sha") or tag)
            rel = self._api_json(f"/repos/{owner}/{repo}/releases/tags/{urllib.parse.quote(tag, safe='')}")
            published = rel.get("published_at")
            if not tag_date or not published:
                raise FetchError("release dates missing")
            return {
                "dates": {"tag": tag_date, "published_at": published},
                "t_verified": max(tag_date, published),
                "resolved": dict(base, tag=tag,
                                 note="release body/assets are mutable post-publish; "
                                      "dates use the tag object and published_at"),
                "fetch": {"url": f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}",
                          "accept": "application/vnd.github+json"},
            }

        raise FetchError(f"form not implemented: {form}")

    # ---------------- content fetch (constructed URLs only) ----------------
    def fetch(self, fetch_spec: dict[str, Any]) -> bytes:
        _, body = http_get(fetch_spec["url"], timeout=self.timeout,
                           token=self.token, accept=fetch_spec.get("accept"))
        return body


# ---------------------------------------------------------------------------
# nature.com (T2: dates from Crossref metadata; see resolve() for why)
# ---------------------------------------------------------------------------
class NatureSurface:
    kind = "nature"
    DEFAULT_HOSTS: set[str] = {"nature.com", "www.nature.com"}

    def __init__(self, cutoff_iso: str, token: str | None = None,
                 hosts: Iterable[str] | None = None, timeout: int = 15) -> None:
        self.cutoff_iso = cutoff_iso
        self.token = token
        self.hosts: set[str] = set(hosts) if hosts else set(self.DEFAULT_HOSTS)
        self.timeout = timeout

    def parse(self, url: str) -> dict[str, Any] | None:
        u = urllib.parse.urlsplit(url)
        if u.scheme != "https" or u.query or u.fragment or not u.hostname \
                or u.hostname not in self.hosts:
            return None
        segs = [s for s in u.path.split("/") if s]
        if len(segs) == 2 and segs[0] == "articles":
            ident = segs[1]
            pdf = ident.endswith(".pdf")
            if pdf:
                ident = ident[:-4]
            if not re.match(r"^[a-z0-9][a-z0-9-]*$", ident):
                return None
            return {"form": "article", "id": ident, "pdf": pdf}
        return None

    def resolve(self, parsed: dict[str, Any]) -> dict[str, Any]:
        # The article page 303s to a cookie-consent flow (idp.nature.com) for
        # every client we probed, and redirects are banned. The authoritative
        # date source is therefore Crossref metadata for the article DOI
        # (10.1038/<id>; its dates match the site's own). Fail closed: no
        # Crossref dates -> deny. Content is check-only in v1 (the page cannot
        # be fetched without following the consent redirect).
        doi = f"10.1038/{parsed['id']}"
        _, body = http_get(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}",
                           timeout=self.timeout, accept="application/json")
        try:
            msg = json.loads(body)["message"]
        except Exception:
            raise FetchError("crossref metadata unreadable (fail closed)")
        stamps = []
        for key in ("published-online", "published-print", "published"):
            dp = (msg.get(key) or {}).get("date-parts") or []
            if dp and dp[0]:
                y = dp[0][0]
                mo = dp[0][1] if len(dp[0]) > 1 else 1
                d = dp[0][2] if len(dp[0]) > 2 else 1
                stamps.append(f"{y:04d}-{mo:02d}-{d:02d}T00:00:00Z")
        if not stamps:
            raise FetchError("crossref dates absent (fail closed)")
        t = min(stamps)  # earliest public date; the fail-closed direction
        return {
            "dates": {"published_earliest": t},
            "t_verified": t,
            "resolved": {"id": parsed["id"], "doi": doi, "source": "crossref"},
            "fetch": None,
        }

    def fetch(self, fetch_spec: dict[str, Any]) -> bytes:
        _, body = http_get(fetch_spec["url"], timeout=self.timeout,
                           accept=fetch_spec.get("accept"))
        return body
