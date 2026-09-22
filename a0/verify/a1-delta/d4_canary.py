#!/usr/bin/env python3
"""Item 4 — my own canary test for the candidate lane's hidden roots.

The claim under test: `_hide` now mounts a fresh tmpfs over **every** hidden root
unconditionally, so on this host — which mounts `/tmp` as tmpfs — the lane's `/tmp` is
the lane's, not the host's. The pre-fix module skipped a root the mount table already
called tmpfs, so the lane's `/tmp` was the host's `/tmp`.

This probe does not read the authors' canary, their receipt or their hostile probe. It
writes its **own** files under `/tmp`, `/var/tmp`, `/home/<user>` and `/run/user/<uid>`,
adds a positive control that *is* allowed (so a negative result cannot come from a broken
reader), and runs a trivial command inside the lane through `candidate_sandbox.prefix`.
It then runs the *pre-fix* module on the same canaries to show the fix is a real change
and not a description of what was already true.

    python3 a0/verify/a1-delta/d4_canary.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PRE_FIX_REVISION = "7a1c0c16^"  # the module that read "tmpfs" as "already hidden"
RECEIPT = Path("/dev/shm/a1delta-canary-receipt.json")
sys.path.insert(0, str(REPO))
from a0.a1 import candidate_sandbox  # noqa: E402

NONCE = "A1DELTA-CANARY-0f3a91"
USER = os.environ.get("USER", "ebt")
UID = os.getuid()
#: canary path -> the hidden root it lives under
CANARIES = {
    "/tmp": f"/tmp/a1delta-canary.txt",
    "/var/tmp": f"/var/tmp/a1delta-canary.txt",
    "/home": f"/home/{USER}/.a1delta-canary.txt",
    "/run/user": f"/run/user/{UID}/a1delta-canary.txt",
}
#: positive controls: files under a hidden root that ARE handed to the lane, and so must
#: be readable inside it (proves the lane can read a file under the root it is testing)
CONTROLS = {
    "/tmp": f"/tmp/a1delta-control.txt",
    "/var/tmp": f"/var/tmp/a1delta-control.txt",
}

LANE_SCRIPT = r"""
import json, os, sys
payload = json.loads(sys.argv[1])
out = {"pid": os.getpid(), "uid": os.getuid(), "roots": {}}
def mount_fstype(root):
    try:
        for line in open("/proc/self/mountinfo"):
            fields = line.split(" - ")
            left = fields[0].split()
            if len(left) > 4 and left[4] == root:
                return fields[1].split()[0]
    except OSError as exc:
        return "unreadable:" + type(exc).__name__
    return None
for root in payload["roots"]:
    entry = {}
    try:
        entry["dev"] = os.stat(root).st_dev
        entry["entries"] = sorted(os.listdir(root))[:6]
        entry["entry_count"] = len(os.listdir(root))
    except OSError as exc:
        entry["stat_error"] = type(exc).__name__
    entry["mount_fstype"] = mount_fstype(root)
    out["roots"][root] = entry
def read(path):
    try:
        with open(path, "rb") as handle:
            return handle.read().decode("utf-8", "replace")
    except OSError as exc:
        return "ERR:" + type(exc).__name__
for root, path in payload["canaries"].items():
    got = read(path)
    out["roots"].setdefault(root, {})["canary"] = {
        "readable": not got.startswith("ERR:"), "value_matches": got == payload["nonce"],
        "result": got if got.startswith("ERR:") else "bytes=%d" % len(got)}
for root, path in payload["controls"].items():
    got = read(path)
    out["roots"].setdefault(root, {})["control"] = {
        "readable": not got.startswith("ERR:"), "value_matches": got == payload["nonce"],
        "result": got if got.startswith("ERR:") else "bytes=%d" % len(got)}
print("LANE_JSON " + json.dumps(out))
"""


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_lane(module, receipt: Path) -> tuple[dict | None, subprocess.CompletedProcess]:
    payload = json.dumps({"nonce": NONCE, "roots": sorted(CANARIES),
                          "canaries": CANARIES, "controls": CONTROLS})
    argv = module.prefix([sys.executable, "-c", LANE_SCRIPT, payload],
                         allow=[Path(sys.executable), *(Path(p) for p in CONTROLS.values())],
                         receipt=receipt)
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=240)
    lane = None
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith("LANE_JSON "):
            lane = json.loads(line[len("LANE_JSON "):])
            break
    return lane, proc


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))
        print(f"[{'ok ' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))

    print("== the canaries and the controls, on the host ==")
    written = []
    for path in [*CANARIES.values(), *CONTROLS.values()]:
        target = Path(path)
        if not target.parent.is_dir():
            print(f"  (skipped {path}: parent does not exist)")
            continue
        target.write_text(NONCE)
        written.append(path)
    check("the host can read back every file this probe wrote",
          all(Path(p).read_text() == NONCE for p in written), f"{len(written)} file(s)")

    print("\n== the same probe inside the lane (the committed module) ==")
    RECEIPT.unlink(missing_ok=True)
    lane, proc = run_lane(candidate_sandbox, RECEIPT)
    if lane is None:
        print(f"  the lane produced no JSON (rc={proc.returncode}): {proc.stderr[-300:]}")
        return 1
    print(f"  lane pid={lane['pid']} uid={lane['uid']} (unshared: pid 1 / uid 0 expected)")
    for root in sorted(lane["roots"]):
        entry = lane["roots"][root]
        canary = entry.get("canary", {})
        control = entry.get("control", {})
        print(f"  {root}: mount={entry.get('mount_fstype')} dev={entry.get('dev')} "
              f"entries={entry.get('entry_count')} {entry.get('entries')}")
        print(f"      canary  {canary.get('result')}  readable={canary.get('readable')}")
        if control:
            print(f"      control {control.get('result')}  readable={control.get('readable')} "
                  f"matches={control.get('value_matches')}")
    check("no host canary is readable from inside the lane",
          all(lane["roots"][r].get("canary", {}).get("readable") is False for r in CANARIES),
          str({r: lane["roots"][r].get("canary", {}).get("readable") for r in CANARIES}))
    check("the positive control IS readable inside the lane (the reader works)",
          all(lane["roots"][r].get("control", {}).get("value_matches") is True for r in CONTROLS),
          str({r: lane["roots"][r].get("control", {}).get("result") for r in CONTROLS}))
    check("every hidden root is covered by a tmpfs inside the lane",
          all(lane["roots"][r].get("mount_fstype") == "tmpfs" for r in CANARIES),
          str({r: lane["roots"][r].get("mount_fstype") for r in CANARIES}))
    check("the lane's /tmp holds only the one file it was handed",
          lane["roots"]["/tmp"].get("entry_count") == 1
          and lane["roots"]["/tmp"]["entries"] == [Path(CONTROLS["/tmp"]).name],
          f"{lane['roots']['/tmp'].get('entry_count')} entries: "
          f"{lane['roots']['/tmp'].get('entries')}")

    receipt = json.loads(RECEIPT.read_text())
    print(f"\n  receipt pass={receipt['pass']} egress={receipt['self_check']['egress']} "
          f"visible_pids={receipt['self_check']['pid_namespace']['visible_pid_count']}")
    for entry in receipt.get("hiding", []):
        before = entry["before"]["mount"]
        print(f"    {entry['root']}: host_mounted={entry['the_host_already_mounted_something_here']}"
              f" before={before['fstype'] if before else None}"
              f"(id {before['mount_id'] if before else '-'})"
              f" after={entry['after']['mount']['fstype']}"
              f"(id {entry['after']['mount']['mount_id']})"
              f" dev {entry['before']['device']}->{entry['after']['device']}"
              f" entries {entry['before']['entries']}->{entry['after']['entries']}")
    check("/tmp was a host tmpfs and was still replaced by this lane's own tmpfs",
          any(e["root"] == "/tmp" and e["the_host_already_mounted_something_here"]
              and e["before"]["mount"]["mount_id"] != e["after"]["mount"]["mount_id"]
              for e in receipt.get("hiding", [])))
    check("the receipt is written before E* ran and records a pass",
          receipt["pass"] is True and receipt["self_check"]["egress_is_blocked"] is True,
          receipt["self_check"]["egress"])

    print("\n== the same canaries against the PRE-FIX module (the fix is a real change) ==")
    with tempfile.TemporaryDirectory(prefix="a1delta-prefix-sandbox-") as tmp:
        old_path = Path(tmp) / "candidate_sandbox_prefix.py"
        blob = subprocess.run(["git", "-C", str(REPO), "show",
                               f"{PRE_FIX_REVISION}:a0/a1/candidate_sandbox.py"],
                              capture_output=True, check=True).stdout
        old_path.write_bytes(blob)
        old_module = load_module(old_path, "candidate_sandbox_prefix")
        old_receipt = Path("/dev/shm/a1delta-canary-receipt-prefix.json")
        old_receipt.unlink(missing_ok=True)
        old_lane, old_proc = run_lane(old_module, old_receipt)
        if old_lane is None:
            print(f"  the pre-fix lane produced no JSON (rc={old_proc.returncode}): "
                  f"{old_proc.stderr[-300:]}")
            check("the pre-fix module runs", False, f"rc={old_proc.returncode}")
        else:
            for root in sorted(old_lane["roots"]):
                canary = old_lane["roots"][root].get("canary", {})
                print(f"  {root}: canary readable={canary.get('readable')} "
                      f"mount={old_lane['roots'][root].get('mount_fstype')} "
                      f"entries={old_lane['roots'][root].get('entry_count')}")
            check("the pre-fix module exposes the host's /tmp to the lane (the regression)",
                  old_lane["roots"]["/tmp"].get("canary", {}).get("readable") is True,
                  str(old_lane["roots"]["/tmp"].get("canary", {})))
            check("...while its receipt still lists /tmp as hidden",
                  "/tmp" in json.loads(old_receipt.read_text()).get("hidden_roots", []))
        old_receipt.unlink(missing_ok=True)

    print("\n== the fail-closed branch: no mount topology -> refuse to measure ==")
    # Triggered through the module's own entry point: with `/proc` as a hidden root, the
    # fresh tmpfs replaces the namespace's mount table, so the next read of it fails —
    # which is exactly the "no topology, no measurement" branch. Expect exit 3, a receipt,
    # and no command run.
    refusal_receipt = Path("/dev/shm/a1delta-refusal-receipt.json")
    refusal_receipt.unlink(missing_ok=True)
    refusal_argv = candidate_sandbox.prefix(["/bin/true"], allow=[Path("/bin/true")],
                                            receipt=refusal_receipt, hidden_roots=("/proc",))
    refusal = subprocess.run(refusal_argv, capture_output=True, text=True, timeout=180)
    reason = refusal.stderr.strip().splitlines()[-1] if refusal.stderr.strip() else ""
    print(f"  exit {refusal.returncode}: {reason[:200]}")
    check("the lane refuses with exit 3 when its mount table cannot be read",
          refusal.returncode == candidate_sandbox.EXIT_SANDBOX_REFUSED == 3,
          f"rc={refusal.returncode}")
    if refusal_receipt.exists():
        doc = json.loads(refusal_receipt.read_text())
        print(f"  receipt pass={doc['pass']} error={doc.get('error', '')[:180]}")
        check("the refusal is written down as a receipt, not asserted",
              doc["pass"] is False and "mount table" in doc.get("error", ""))
    else:
        check("a refusal receipt was written", False, "no receipt")

    print("\n== cleanup ==")
    for path in written:
        Path(path).unlink(missing_ok=True)
    RECEIPT.unlink(missing_ok=True)
    refusal_receipt.unlink(missing_ok=True)
    print(f"  removed {len(written)} canary/control file(s) and the receipts")

    failed = [name for name, ok, _ in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks ok"
          + (f"; FAILED: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
