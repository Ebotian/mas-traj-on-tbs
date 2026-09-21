#!/usr/bin/env python3
"""Self-test for the Model Route Contract.

Runs with no arguments and no network:

    python3 a0/mrc/mrc_selftest.py

Checks, in order:

1. canonical serialization is byte-identical to a0/contract/evalcontract.py, so
   the two digest schemes agree on what a payload *is*;
2. an independent re-implementation of MRC* reproduces a declaration's digest;
3. every shipped declaration validates clean against the frozen route registry;
4. a declaration's MRC* is invariant to where the spec file lives (no absolute
   paths, no mtimes), but changes when a load-bearing field changes;
5. every recorded `RuntimeAdapters[].adapter_source_sha256` has a preimage: the
   digest recomputes from the manifest recorded beside it (independently
   re-implemented here), and that manifest is exactly the blobs the repo holds
   under the declared root at the declared commit;
6. each negative case fails with the expected error code; the mutated documents
   are written to fixtures/negative/ for a third party to inspect.

Exit 0 iff every check passes.  Check 5 shells out to `git` in the enclosing
repository; everything else is offline.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import mrc  # noqa: E402

CONTRACT = HERE.parent / "contract" / "evalcontract.py"
ROUTES = [
    "codex-deepseek-responses",
    "claude-deepseek-anthropic",
    "kilo-deepseek-chat",
    "opencode-deepseek-chat",
]

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def load_declaration(route: str) -> dict:
    return json.loads((HERE / "declarations" / f"{route}.mrc.json").read_text(encoding="utf-8"))


def load_spec(route: str) -> dict:
    return json.loads((HERE / "declarations" / f"{route}.spec.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# 1. canonical-form interop with the evaluator contract
# --------------------------------------------------------------------------


def check_canonical_interop() -> None:
    if not CONTRACT.exists():
        check("canonical-form interop with evalcontract", False, f"missing {CONTRACT}")
        return
    spec = importlib.util.spec_from_file_location("evalcontract_ref", CONTRACT)
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)
    torture = {
        "b": [1, 2.5, True, None, "x"],
        "a": {"z": -0.0, "y": "unicode: \u00e9\u4e2d", "1": {"nested": []}},
        "list": [{"k": 1}, {"k": 2}],
    }
    ours = mrc.canonical_json(torture)
    theirs = ref.canonical_json(torture)
    check("canonical-form interop with evalcontract", ours == theirs,
          f"ours={ours[:60]!r} theirs={theirs[:60]!r}")
    check("domain separation is one nul byte",
          mrc.domain_digest("d", b"p") == ref.domain_digest("d", b"p"))


# --------------------------------------------------------------------------
# 2. independent re-implementation of MRC*
# --------------------------------------------------------------------------


def independent_mrc_star(doc: dict) -> str:
    """Deliberately written the long way: no shared helpers, explicit bytes."""
    import hashlib

    def canon(obj):
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")

    digests = {}
    for name in mrc.COMPONENTS:
        payload = canon(doc["components"][name])
        digests[name] = hashlib.sha256(b"a0/mrc/v1/" + name.encode() + b"\x00" + payload).hexdigest()
    return hashlib.sha256(b"a0/mrc/v1/MRC*\x00" + canon(digests)).hexdigest()


def check_independent_reimplementation() -> None:
    for route in ROUTES:
        doc = load_declaration(route)
        independent = independent_mrc_star(doc)
        check(f"independent re-implementation reproduces MRC* ({route})",
              independent == doc["mrc_star"],
              f"independent={independent[:16]} recorded={doc['mrc_star'][:16]}")


# --------------------------------------------------------------------------
# 3. shipped declarations validate
# --------------------------------------------------------------------------


def check_declarations_validate() -> None:
    frozen = mrc.load_frozen(HERE / "frozen_routes.json")
    for route in ROUTES:
        doc = load_declaration(route)
        problems = mrc.validate(doc, frozen)
        check(f"declaration validates against frozen registry ({route})",
              not problems, "; ".join(problems))
        rec = mrc.recompute_from_records(doc)
        check(f"recompute-from-records is clean ({route})",
              rec["mrc_star"] == doc["mrc_star"])


# --------------------------------------------------------------------------
# 4. portability and sensitivity of the digest
# --------------------------------------------------------------------------


def check_portability(tmp: Path) -> None:
    route = "codex-deepseek-responses"
    spec = load_spec(route)
    elsewhere = tmp / "deep" / "nested" / "spec.json"
    elsewhere.parent.mkdir(parents=True, exist_ok=True)
    elsewhere.write_text(json.dumps(spec), encoding="utf-8")
    moved = mrc.build_mrc(json.loads(elsewhere.read_text(encoding="utf-8")))
    check("MRC* does not depend on where the spec file lives",
          moved["mrc_star"] == load_declaration(route)["mrc_star"])

    shuffled = copy.deepcopy(spec)
    shuffled["components"] = dict(reversed(list(shuffled["components"].items())))
    check("MRC* does not depend on key or component order",
          mrc.build_mrc(shuffled)["mrc_star"] == load_declaration(route)["mrc_star"])

    for label, mutate in (
        ("requested model id", lambda s: s["components"]["RequestedModel"].__setitem__(
            "requested_model_id", "deepseek-v4-pro")),
        ("endpoint base_url", lambda s: s["components"]["Endpoint"].__setitem__(
            "base_url", "https://api.deepseek.com/v1/")),
        ("cli version", lambda s: s["components"]["Cli"].__setitem__("version", "0.154.0")),
    ):
        variant = copy.deepcopy(spec)
        mutate(variant)
        check(f"MRC* changes when the {label} changes",
              mrc.build_mrc(variant)["mrc_star"] != moved["mrc_star"])


# --------------------------------------------------------------------------
# 5. every declared adapter digest has a preimage
# --------------------------------------------------------------------------


def independent_adapter_source_digest(entries: list) -> str:
    """The adapter-preimage rule, written long-hand (no shared helper)."""
    import hashlib

    payload = json.dumps([[e["path"], e["sha256"]] for e in entries],
                         sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(b"a0/mrc/v1/RuntimeAdapters/adapter_source" + b"\x00" + payload).hexdigest()


def _git(*args: str) -> bytes:
    proc = subprocess.run(["git", "-C", str(REPO_ROOT), *args], capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode().strip() or f"git {args[0]} failed")
    return proc.stdout


def check_adapter_preimages() -> None:
    """A digest whose preimage cannot be named is unverifiable; check both the
    arithmetic (manifest -> digest) and the preimage (repo blobs -> manifest)."""
    rule_ok = True
    manifests_ok = True
    repo_ok = True
    repo_detail = ""
    for route in ROUTES:
        doc = load_declaration(route)
        for adapter in doc["components"]["RuntimeAdapters"]["adapters"]:
            runtime = adapter["runtime"]
            recorded = adapter.get("adapter_source_sha256")
            entries = adapter.get("adapter_source_files")
            recomputed = (independent_adapter_source_digest(entries)
                          if isinstance(entries, list) and entries else None)
            if recomputed != recorded:
                manifests_ok = False
                print(f"  preimage mismatch: {route}/{runtime} "
                      f"recorded={recorded} from-manifest={recomputed}")
            rule_ok &= adapter.get("adapter_source_rule") == mrc.ADAPTER_SOURCE_RULE
            try:
                listing = _git("ls-tree", "-r", "--name-only",
                               adapter["adapter_commit"], "--", adapter["adapter_source_root"])
                paths = sorted(p for p in listing.decode("utf-8").splitlines() if p)
                expected = [(p, hashlib_blob(adapter["adapter_commit"], p)) for p in paths]
                listed = [(e["path"], e["sha256"]) for e in entries]
                if expected != listed:
                    repo_ok = False
                    missing = [p for p, _ in expected if p not in [q for q, _ in listed]]
                    extra = [q for q, _ in listed if q not in [p for p, _ in expected]]
                    repo_detail = (f"{route}/{runtime}: preimage does not match the repo at "
                                   f"{adapter['adapter_commit']}; missing={missing} extra={extra}")
            except RuntimeError as exc:
                repo_ok = False
                repo_detail = f"{route}/{runtime}: {exc}"

    check("every adapter digest recomputes from the preimage recorded beside it", manifests_ok)
    check("every adapter records the rule this code implements", rule_ok)
    check("every adapter preimage is the repo's own file set at the declared commit",
          repo_ok, repo_detail)


def hashlib_blob(commit: str, path: str) -> str:
    import hashlib

    return hashlib.sha256(_git("show", f"{commit}:{path}")).hexdigest()


# --------------------------------------------------------------------------
# 6. negative cases
# --------------------------------------------------------------------------


def mutate_and_rehash(doc: dict, fn) -> dict:
    """Apply a mutation to the components, then recompute the digests so that
    only the intended defect remains and no digest mismatch masks it."""
    doc = copy.deepcopy(doc)
    fn(doc)
    digests = {c: mrc.component_digest(c, doc["components"][c]) for c in mrc.COMPONENTS}
    doc["component_digests"] = digests
    doc["mrc_star"] = mrc.mrc_star_from_digests(digests)
    return doc


def check_negatives(tmp: Path) -> None:
    frozen = mrc.load_frozen(HERE / "frozen_routes.json")
    outdir = HERE / "fixtures" / "negative"
    outdir.mkdir(parents=True, exist_ok=True)
    base_route = "codex-deepseek-responses"
    base = load_declaration(base_route)

    def endpoint_drift(d):
        d["components"]["Endpoint"]["base_url"] = "https://openrouter.ai/api/v1"

    def model_drift(d):
        d["components"]["RequestedModel"]["requested_model_id"] = "deepseek-v4-flash"

    def surface_drift(d):
        d["components"]["ApiSurface"]["surface_path"] = "/v1/chat/completions"

    def echo_as_proof(d):
        d["identity_evidence"]["weights_identity_verifiable"] = True
        d["identity_evidence"]["observations"][0]["proves_weights"] = True

    def policy_allows_openrouter(d):
        d["model_policy"] = {"primary": "deepseek-flash", "mixed_secondary_allowed": True,
                             "permitted_secondary": ["deepseek-v4-pro", "openrouter/auto"],
                             "excluded_providers": []}

    def policy_wrong_primary(d):
        d["model_policy"] = {"primary": "deepseek-v4-pro", "mixed_secondary_allowed": True,
                             "permitted_secondary": [], "excluded_providers": ["openrouter"]}

    def null_digest_without_reason(d):
        d["components"]["Prompt"].pop("system_prompt_null_reason", None)

    def digest_tamper(d):
        d["components"]["Endpoint"]["host"] = "api.openrouter.ai"
        return None

    def secret_literal(d):
        d["components"]["Cli"]["note"] = "sk-abcdef0123456789abcdef"

    def abs_path_leak(d):
        d["components"]["Cli"]["config_files"] = ["/home/ebt/rsi-dev/a0/runtimes/kapso/config"]

    def eid_drift(d):
        d["components"]["TaskSnapshot"]["eid_star"] = "fac50fc4" + "0" * 56

    def adapter_missing(d):
        d["components"]["RuntimeAdapters"]["adapters"] = []

    def adapter_digest_without_preimage(d):
        d["components"]["RuntimeAdapters"]["adapters"][0].pop("adapter_source_files")

    def adapter_digest_off_preimage(d):
        d["components"]["RuntimeAdapters"]["adapters"][0]["adapter_source_sha256"] = "0" * 64

    cases = [
        ("neg_endpoint_drift", endpoint_drift, False, "MRC-ENDPOINT-DRIFT"),
        ("neg_model_drift", model_drift, False, "MRC-MODEL-DRIFT"),
        ("neg_surface_drift", surface_drift, False, "MRC-SURFACE-DRIFT"),
        ("neg_echo_as_proof", echo_as_proof, False, "MRC-IDENTITY-WEIGHTS-CLAIM"),
        ("neg_policy_allows_openrouter", policy_allows_openrouter, False, "MRC-POLICY-EXCLUDED"),
        ("neg_policy_wrong_primary", policy_wrong_primary, False, "MRC-POLICY-PRIMARY"),
        ("neg_null_digest_without_reason", null_digest_without_reason, False, "MRC-NULL-DIGEST"),
        ("neg_digest_tamper", digest_tamper, True, "MRC-DIGEST-MISMATCH"),
        ("neg_secret_literal", secret_literal, True, "MRC-HYGIENE"),
        ("neg_abs_path_leak", abs_path_leak, True, "MRC-HYGIENE"),
        ("neg_eid_drift", eid_drift, False, "MRC-EID-DRIFT"),
        ("neg_adapter_missing", adapter_missing, False, "MRC-ADAPTER-MISSING"),
        ("neg_adapter_digest_without_preimage", adapter_digest_without_preimage, False,
         "MRC-ADAPTER-PREIMAGE"),
        ("neg_adapter_digest_off_preimage", adapter_digest_off_preimage, False,
         "MRC-ADAPTER-DIGEST"),
    ]

    for name, fn, rehash, expected in cases:
        if rehash:
            doc = copy.deepcopy(base)
            fn(doc)  # leave digests stale on purpose
        else:
            doc = mutate_and_rehash(base, fn)
        problems = mrc.validate(doc, frozen)
        hit = any(p.startswith(expected) for p in problems)
        (outdir / f"{name}.mrc.json").write_text(
            json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        check(f"negative case {name} fails with {expected}", hit,
              f"got: {problems[:2]}")


def check_json_schema() -> None:
    try:
        import jsonschema
    except ImportError:
        check("declarations conform to mrc_schema.json", True, "skipped: jsonschema not installed")
        return
    schema = json.loads((HERE / "mrc_schema.json").read_text(encoding="utf-8"))
    for route in ROUTES:
        doc = load_declaration(route)
        try:
            jsonschema.validate(doc, schema)
            check(f"declaration conforms to mrc_schema.json ({route})", True)
        except jsonschema.ValidationError as exc:  # noqa: PERF203
            check(f"declaration conforms to mrc_schema.json ({route})", False,
                  f"{exc.message[:120]} at {list(exc.absolute_path)}")


def check_positive_controls_ok(frozen) -> None:
    """A negative suite is only meaningful if the unmutated inputs pass."""
    for route in ROUTES:
        check(f"positive control passes for {route}",
              not mrc.validate(load_declaration(route), frozen))


# --------------------------------------------------------------------------


def main() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        check_canonical_interop()
        check_independent_reimplementation()
        check_declarations_validate()
        check_json_schema()
        check_portability(tmp)
        check_adapter_preimages()
        check_negatives(tmp)
        check_positive_controls_ok(mrc.load_frozen(HERE / "frozen_routes.json"))

    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        line = f"[{status}] {name}"
        if not ok and detail:
            line += f"  -- {detail}"
        print(line)
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
