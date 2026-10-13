#!/usr/bin/env python3
"""Mechanical guard after reorganizations / patch edits:
every /home/ebt/harbor-runs path referenced by LIVE config scripts and the
three PATCHED harbor files (trial.py = verifier overlay path; qwen_code.py =
ATIF v1.8; node_install.py = install.sh URL -> jsdelivr) must exist on disk.
Legacy files are excluded by design (data/legacy/* keep historical paths).

Run:  python3 /home/ebt/harbor-runs/config/check_paths.py
Exit: 0 all references resolve; 1 lists failing references.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path("/home/ebt/harbor-runs")
HARBOR = pathlib.Path(
    "/home/ebt/.local/share/uv/tools/harbor/lib/python3.14/site-packages/harbor"
)
PATTERN = re.compile(r"/home/ebt/harbor-runs/[A-Za-z0-9_./-]+")

TARGETS = (
    sorted((ROOT / "config").glob("*.sh"))
    + sorted((ROOT / "config").glob("*.yaml"))
    + sorted((ROOT / "egress").glob("*.py"))
    + sorted((ROOT / "egress" / "policies").glob("*.yml"))
    + sorted((ROOT / "egress" / "tests").rglob("*.py"))
    + sorted((ROOT / "egress" / "gateway").glob("*.py"))
    + [ROOT / "egress" / "gateway" / "run.sh",
       ROOT / "run_agent_arm.sh",
       ROOT / "data" / "fetch_payload_curl.sh",
       HARBOR / "trial" / "trial.py",
       HARBOR / "agents" / "installed" / "qwen_code.py",
       HARBOR / "agents" / "installed" / "node_install.py"]
)

bad = []
for target in TARGETS:
    if not target.exists():
        bad.append((target, "<file missing>"))
        continue
    for m in PATTERN.finditer(target.read_text()):
        ref = pathlib.Path(m.group(0).rstrip(".,)"))
        if not ref.exists():
            bad.append((target, m.group(0)))

print(f"checked files: {len(TARGETS)}")
if bad:
    print("BROKEN REFERENCES:")
    for target, ref in bad:
        print(f"  {target.name}  ->  {ref}")
    sys.exit(1)
print("all referenced paths exist OK")
