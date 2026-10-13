#!/usr/bin/env python3
"""Validate the layered egress policy manifests (fail-closed defaults).

Checks: parse; host syntax (lowercase FQDN; wildcards only as leading "*.");
no duplicates across layers; cutoff ISO-8601; unknown-date/revision default
deny; forbidden_sources non-empty when a temporal_policy is present; task_id
matches the filename.

Run: python3 /home/ebt/harbor-runs/egress/validate.py --task tumor-immune-interface
"""
import argparse
import datetime
import pathlib
import re
import sys

import yaml

POLICIES = pathlib.Path("/home/ebt/harbor-runs/egress/policies")
HOST_RE = re.compile(r"^(\*\.)?[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    args = ap.parse_args()
    errors = []

    base = yaml.safe_load((POLICIES / "base.yml").read_text())
    overlay = yaml.safe_load((POLICIES / f"{args.task}.yml").read_text())

    for h in base.get("hosts", []):
        if not isinstance(h, str) or not HOST_RE.match(h):
            errors.append(f"base.yml: invalid host {h!r}")
    for h in overlay.get("restricted_hosts", []):
        if not isinstance(h, str) or not HOST_RE.match(h):
            errors.append(f"{args.task}.yml: invalid host {h!r}")
    base_set = set(base.get("hosts", []))
    for h in overlay.get("restricted_hosts", []):
        if h in base_set:
            errors.append(f"duplicate across layers: {h}")

    tp = overlay.get("temporal_policy", {})
    if tp:
        try:
            datetime.datetime.fromisoformat(str(tp.get("cutoff", "")).replace("Z", "+00:00"))
        except Exception:
            errors.append(f"temporal_policy.cutoff not ISO-8601: {tp.get('cutoff')!r}")
        if overlay.get("unknown_publication_date") != "deny":
            errors.append("unknown_publication_date must be deny")
        if overlay.get("unverified_content_revision") != "deny":
            errors.append("unverified_content_revision must be deny")
        if not overlay.get("forbidden_sources"):
            errors.append("forbidden_sources empty while temporal_policy present")

    if overlay.get("task_id") != args.task:
        errors.append(f"task_id {overlay.get('task_id')!r} != requested {args.task!r}")

    if errors:
        print("FAIL:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print(
        f"ok: {args.task} (base {len(base.get('hosts', []))} hosts "
        f"+ overlay {len(overlay.get('restricted_hosts', []))} hosts)"
    )


if __name__ == "__main__":
    main()
