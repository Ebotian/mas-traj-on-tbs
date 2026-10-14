#!/bin/bash
# verify_acceptance.sh — 统一验收入口(2026-10-14 按用户指令合并原 walkthrough/tumor 两份分跑核验,全族一条命令)。
#
# 用法:
#   bash verify_acceptance.sh <job-dir> [--family auto|microarch|tumor|walkthrough] [--expect-tags t1,t2,...]
#   bash verify_acceptance.sh --all <jobs-dir>    # 批量:每个含 task-* 的 job 跑一遍,末尾出汇总
#
# 家族(默认 auto):
#   task-microarch__* → microarch;task-restricted__* 且 collect/results 或 state.deliverables* → tumor;
#   其余 restricted → walkthrough;可用 --family 显式覆盖。
#
# 检查节:
#   0) 识别/家族/时长(来自 job result.json)
#   1) 正常退出:state.json 判 NORMAL(rc 0/0、双 stop、consensus 在 main、structure_ok、无有效 abort;
#      tumor/microarch 另加 deliverables_present)
#   2) 采集清单:protocol.bundle/git-log/state + boards/chats 计数 + gate.log 摘要;tumor 另查 results/sub-a/sub-b/x(sub-a/b 允许 snapshot/ 回退〔收口唤醒先清 worktree〕),microarch 另查 model.onnx
#   3) git 可重建:克隆【collect 顶层】protocol.bundle(勿用 snapshot/,那是周期性中途快照,含未清理的 origin/a|b)
#      + consensus.md/submission 在 main + git_structure.py --mode final(四签终态)
#   4) 判分记录:reward.txt + ctrf.json 摘要 + metrics.json 摘要 + test-stdout 尾部
#   5) 轨迹工具:traj-<a|b>.full-index.jsonl 行数 + traj.py audit-seal 双向
#   6) 里程碑统计:x/stats 四签 ×(json+md)存在可解析、schema=traj-stats/*、0444、pin/ 计数
#
# 年代:有 x/stats 或克隆含 ckpt-m00 = modern(全部严格);否则 legacy(结构/统计/索引/封签类降为 WARN)。
# 退出码:0=ACCEPTED 1=NOT ACCEPTED(见 FAIL 行) 2=用法错。
set -u
SELF=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SELF/.." && pwd)
TRAJ="$ROOT/common/traj.py"
GST="$ROOT/common/git_structure.py"

say()  { echo "  $1"; }
fail() { echo "  FAIL: $1"; FAIL=1; }
warn() { echo "  WARN: $1"; }
FAIL=0; MODERN=""

# ---------- 批量模式 ----------
if [ "${1:-}" = "--all" ]; then
  JOBSDIR="${2:-}"; [ -n "$JOBSDIR" ] || { echo "usage: verify_acceptance.sh --all <jobs-dir>"; exit 2; }
  OKC=0; BADC=0
  for J in "$JOBSDIR"/*/; do
    [ -d "$J" ] || continue
    find "$J" -maxdepth 2 -type d -name 'task-*__*' | grep -q . || continue
    OUT=$(bash "$SELF/verify_acceptance.sh" "$J" 2>&1); RC=$?
    V=$(printf '%s\n' "$OUT" | grep '^VERDICT:' | tail -1)
    if [ "$RC" -eq 0 ]; then OKC=$((OKC+1)); echo "$(basename "$J"): $V"
    else BADC=$((BADC+1)); echo "$(basename "$J"): $V"; printf '%s\n' "$OUT" | grep -E '^  FAIL:' | sed 's/^/      /'; fi
  done
  echo; echo "summary: $OKC accepted, $BADC not accepted"
  [ "$BADC" -eq 0 ]; exit $?
fi

J="${1:-}"; [ -n "$J" ] || { echo "usage: verify_acceptance.sh <job-dir> [--family ...] [--expect-tags ...] | --all <jobs-dir>"; exit 2; }
shift
FAMILY_OVERRIDE="auto"; EXP_TAGS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --family) FAMILY_OVERRIDE="${2:-auto}"; shift 2;;
    --expect-tags) EXP_TAGS="${2:-}"; shift 2;;
    *) echo "unknown arg: $1"; exit 2;;
  esac
done

T=$(find "$J" -maxdepth 2 -type d -name 'task-*__*' | head -1)
echo "job: $J"
echo "trial: ${T:-<none>}"
[ -n "$T" ] || { echo "FAIL: no trial dir under $J"; echo "VERDICT: NOT ACCEPTED"; exit 1; }
C="$T/artifacts/root/wt/collect"
STATE="$C/state.json"; [ -f "$STATE" ] || STATE=$(find "$T" -name state.json -path '*collect*' ! -path '*snapshot*' | head -1)

# ---------- 0) family / runtime ----------
HAS_DELIV=""
if [ -d "$C/results" ]; then HAS_DELIV=1; elif [ -n "$STATE" ]; then
  HAS_DELIV=$(python3 - "$STATE" <<'PY'
import json, sys
try: d = json.load(open(sys.argv[1]))
except Exception: raise SystemExit(0)
print("1" if ("deliverables" in d or "deliverables_present" in d) else "")
PY
)
fi
case "$(basename "$T")" in
  task-microarch*) FAMILY="microarch";;
  task-restricted*) [ "$HAS_DELIV" = "1" ] && FAMILY="tumor" || FAMILY="walkthrough";;
  *) FAMILY="walkthrough";;
esac
[ "$FAMILY_OVERRIDE" != "auto" ] && FAMILY="$FAMILY_OVERRIDE"
echo "family: $FAMILY"
[ -d "$C/x/stats" ] && MODERN=1
python3 - "$J" <<'PY'
import datetime, json, sys
try:
    d = json.load(open(sys.argv[1] + "/result.json"))
    s = datetime.datetime.fromisoformat(str(d["started_at"]).replace("Z", "+00:00"))
    f = datetime.datetime.fromisoformat(str(d["finished_at"]).replace("Z", "+00:00"))
    t = int((f - s).total_seconds()); st = d.get("stats", {})
    print(f"  runtime: {t//3600}h{(t%3600)//60:02d}m{t%60:02d}s | completed {st.get('n_completed_trials')} / errored {st.get('n_errored_trials')} / retries {st.get('n_retries')}")
except Exception as e:
    print("  WARN: job result.json unreadable:", e)
PY

# ---------- 1) normal exit ----------
echo "== 1) normal exit"
if [ -z "$STATE" ]; then fail "collect/state.json not found"; else
  python3 - "$STATE" "$FAMILY" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); fam = sys.argv[2]
ab = d.get("abort_effective")
if ab is None: ab = {"a": bool(d.get("abort_a")), "b": bool(d.get("abort_b"))}
crit = {
  "rc_a==0": d.get("rc_a") == 0, "rc_b==0": d.get("rc_b") == 0,
  "stop_a": bool(d.get("stop_a")), "stop_b": bool(d.get("stop_b")),
  "consensus_on_main": bool(d.get("consensus_on_main")),
  "no_effective_abort_a": not ab.get("a"), "no_effective_abort_b": not ab.get("b"),
}
if "structure_ok" in d:
    crit["structure_ok"] = d.get("structure_ok") is True
else:
    print("  WARN: structure_ok absent (pre-gate legacy); skipped")
if fam in ("tumor", "microarch") and "deliverables_present" in d:
    crit["deliverables_present"] = d.get("deliverables_present") is True
bad = [k for k, v in crit.items() if not v]
for k, v in crit.items(): print(f"  {'ok' if v else 'FAIL'}: {k}")
print("  state.json -> NORMAL" if not bad else "  state.json -> ABNORMAL")
rec = d.get("recover") or {}; wakes = rec.get("wakes") or []
print(f"  recovered_run: {d.get('recovered_run')} | wakes: {len(wakes)} | rounds: {d.get('rounds')}")
for w in wakes: print(f"    wake side={w.get('side')} rc={w.get('rc')} dur_s={w.get('dur_s')} mode={w.get('mode')}")
sys.exit(0 if not bad else 1)
PY
  RC=$?; [ "$RC" -eq 0 ] || FAIL=1
  echo "  --- state.json (raw, head 70) ---"
  python3 -m json.tool "$STATE" 2>/dev/null | sed 's/^/    /' | head -70
fi

# ---------- 2) collection manifest ----------
echo "== 2) collection manifest"
for pat in protocol.bundle git-log.txt state.json; do
  f=$(find "$T" -path '*/collect/*' -name "$pat" ! -path '*snapshot*' | head -1)
  if [ -z "$f" ]; then fail "$pat missing"; else say "ok: $pat ($(stat -c%s "$f") B)"; fi
done
BOARDS=$(find "$T" -path '*boards*' -name '*.json' ! -path '*snapshot*' | wc -l)
CHATS=$(find "$T" -path '*chats*' -name '*.jsonl' ! -path '*snapshot*' | wc -l)
say "board items: $BOARDS | session chats: $CHATS"
[ "$BOARDS" -ge 2 ] || warn "fewer than 2 board items"
[ "$CHATS" -ge 2 ] || warn "fewer than 2 session transcripts"
if [ "$FAMILY" = "tumor" ]; then
  for d in results sub-a sub-b x; do
    f=$(find "$T" -type d -name "$d" ! -path '*snapshot*' | head -1)
    if [ -z "$f" ]; then
      f=$(find "$T" -type d -name "$d" -path '*snapshot*' | head -1)
      if [ -n "$f" ]; then say "ok: collect/$d (via snapshot/ 回退〔收口唤醒先清 worktree〕; $(du -sh "$f" 2>/dev/null | cut -f1), $(find "$f" -type f | wc -l) files)"
      else fail "collect/$d missing (collect/ 与 snapshot/ 均无)"; fi
    else say "ok: collect/$d ($(du -sh "$f" 2>/dev/null | cut -f1), $(find "$f" -type f | wc -l) files)"; fi
  done
fi
if [ "$FAMILY" = "microarch" ]; then
  if [ -f "$C/model.onnx" ]; then say "ok: collect/model.onnx ($(stat -c%s "$C/model.onnx") B)"; else fail "collect/model.onnx missing"; fi
fi
GATELOG="$C/x/gate.log"; [ -f "$GATELOG" ] || GATELOG=$(find "$T" -name gate.log ! -path '*snapshot*' | head -1)
if [ -n "$GATELOG" ]; then
  say "gate.log lines: $(wc -l < "$GATELOG")"
  echo "    kinds: $(awk '{print $2}' "$GATELOG" | sort | uniq -c | tr '\n' ' ')"
  echo "    last: $(tail -n 1 "$GATELOG")"
else warn "gate.log missing"; fi

# ---------- 3) git reconstructibility ----------
echo "== 3) git reconstructibility"
BUNDLE="$C/protocol.bundle"
if [ ! -f "$BUNDLE" ]; then BUNDLE=$(find "$T" -name protocol.bundle ! -path '*snapshot*' | head -1); [ -n "$BUNDLE" ] && warn "top-level collect/protocol.bundle missing; using $BUNDLE"; fi
if [ -n "$BUNDLE" ]; then
  S=$(mktemp -d /tmp/wt-verify-XXXX)
  if git clone -q "$BUNDLE" "$S/repo" 2>/dev/null; then say "clone ok: ${BUNDLE#"$T"/}"; else fail "clone failed: $BUNDLE"; fi
  if [ -d "$S/repo/.git" ]; then
    TAGS=$(git -C "$S/repo" tag | tr '\n' ' ')
    say "tags: $TAGS"
    case " $TAGS " in *" ckpt-m00 "*) MODERN=1;; esac
    ROUNDN=$(git -C "$S/repo" log --all --format=%B | grep -cE 'Round: [0-9]')
    say "commits carrying Round markers: $ROUNDN"
    echo "  branches: $(git -C "$S/repo" branch -a | tr '\n' ' ')"
    git -C "$S/repo" show main:consensus.md >/dev/null 2>&1 && say "consensus.md on main: yes" || fail "consensus.md on main: NO"
    case "$FAMILY" in
      tumor)
        if git -C "$S/repo" show main:submission/tumor_interface_qc.csv >/dev/null 2>&1; then say "submission/ on main: yes (tumor_interface_qc.csv)"
        else [ "$MODERN" = 1 ] && fail "submission/ on main: NO" || warn "submission/ on main: NO (legacy, not enforced)"; fi;;
      microarch)
        if git -C "$S/repo" show main:submission/model.onnx >/dev/null 2>&1; then say "submission/model.onnx on main: yes"
        else [ "$MODERN" = 1 ] && fail "submission/model.onnx on main: NO" || warn "submission/ on main: NO (legacy, not enforced)"; fi;;
    esac
    echo "  graph head:"; git -C "$S/repo" log --graph --oneline --decorate --all | head -12 | sed 's/^/    /'
    if [ -n "$EXP_TAGS" ]; then ET="$EXP_TAGS"; elif [ "$MODERN" = 1 ]; then ET="ckpt-m00,ckpt-m01,ckpt-m1,ckpt-m2"; else ET="ckpt-m1,ckpt-m2"; fi
    python3 "$GST" "$S/repo" --mode final --expect-tags "$ET" > "$S/gst.json" 2>/dev/null
    python3 - "$S/gst.json" "$MODERN" <<'PY'
import json, sys
try: d = json.load(open(sys.argv[1]))
except Exception as e: print("  WARN: git_structure output unreadable:", e); raise SystemExit(0)
mod = sys.argv[2] == "1"
if d.get("skip"): print("  WARN: git_structure skip=true (enumeration failed)")
if d.get("ok"): print(f"  structure: ok | heads={d['heads']} remotes={d['remotes']} tags={d['tags']}"); raise SystemExit(0)
v = json.dumps(d.get("violations", {}), ensure_ascii=False)
if mod: print("  FAIL: structure violations:", v); raise SystemExit(1)
print("  WARN: structure violations (legacy era, not enforced):", v); raise SystemExit(0)
PY
    RC=$?; [ "$RC" -eq 0 ] || FAIL=1
  fi
  rm -rf "$S"
else fail "no protocol.bundle to reconstruct from"; fi

# ---------- 4) verifier record ----------
echo "== 4) verifier record"
V="$T/verifier"
if [ ! -d "$V" ]; then warn "verifier/ dir missing"; else
  if [ -f "$V/reward.txt" ]; then say "reward: $(cat "$V/reward.txt")"
  else [ "$MODERN" = 1 ] && fail "verifier/reward.txt missing" || warn "verifier/reward.txt missing (legacy, not enforced)"; fi
  if [ -f "$V/ctrf.json" ]; then
    python3 - "$V/ctrf.json" <<'PY'
import json, sys
try: r = json.load(open(sys.argv[1]))["results"]
except Exception as e: print("  WARN: ctrf.json unreadable:", e); raise SystemExit(0)
s = r.get("summary", {})
print(f"  ctrf: tests={s.get('tests')} passed={s.get('passed')} failed={s.get('failed')}")
for t in r.get("tests", []):
    if t.get("status") == "failed": print("    failed:", t.get("name"))
PY
  fi
  if [ -f "$V/metrics.json" ]; then
    python3 - "$V/metrics.json" <<'PY'
import json, sys
try: d = json.load(open(sys.argv[1]))
except Exception as e: print("  WARN: metrics.json unreadable:", e); raise SystemExit(0)
keys = ("annotation_score", "annotation_threshold", "composite_score", "error")
head = {k: d[k] for k in keys if k in d}
print("  metrics:", head if head else "(no headline keys)")
PY
  fi
  if [ -f "$V/test-stdout.txt" ]; then
    echo "  test-stdout tail:"
    if grep -q 'short test summary info' "$V/test-stdout.txt"; then
      awk '/short test summary info/{p=1} p' "$V/test-stdout.txt" | head -14 | sed 's/^/    /'
    else
      tail -n 6 "$V/test-stdout.txt" | sed 's/^/    /'
    fi
  fi
fi

# ---------- 5) trajectory tooling ----------
echo "== 5) trajectory tooling"
XD="$C/x"
for side in a b; do
  idx="$C/traj-$side.full-index.jsonl"
  [ -f "$idx" ] || idx=$(find "$T" -name "traj-$side.full-index.jsonl" ! -path '*snapshot*' | head -1)
  if [ -n "$idx" ] && [ -f "$idx" ]; then say "ok: traj-$side.full-index.jsonl ($(wc -l < "$idx") rows)"
  else [ "$MODERN" = 1 ] && fail "traj-$side.full-index.jsonl missing" || warn "traj-$side.full-index.jsonl missing (legacy, not enforced)"; fi
done
if [ -f "$TRAJ" ]; then
  for pair in "a b" "b a"; do
    S1=${pair%% *}; S2=${pair##* }
    UUID=$(cat "$XD/session-$S1.uuid" 2>/dev/null | tr -d '[:space:]')
    CHAT=""; [ -n "$UUID" ] && CHAT=$(find "$T" -name "$UUID.jsonl" | head -1)
    if [ -n "$CHAT" ]; then
      OUT=$(python3 "$TRAJ" audit-seal --actor "$S1" --peer "$S2" --transcript "$CHAT" 2>&1); RC=$?
      LINE=$(printf '%s\n' "$OUT" | grep 'audit-seal' | head -1)
      say "${LINE:-audit-seal side $S1: (no audit line)} (rc=$RC)"
      [ "$RC" -eq 0 ] || fail "seal audit found violations for actor $S1"
    else
      [ "$MODERN" = 1 ] && fail "cannot locate transcript for side $S1 (uuid/chat)" || warn "transcript for side $S1 not located (legacy, not enforced)"
    fi
  done
else
  warn "traj.py not found at $TRAJ — audit skipped"
fi

# ---------- 6) milestone stats ----------
echo "== 6) milestone stats (x/stats)"
ST="$C/x/stats"
if [ -d "$ST" ]; then
  python3 - "$ST" "$MODERN" <<'PY'
import json, os, sys
st, mod = sys.argv[1], sys.argv[2] == "1"
tags = ["ckpt-m00", "ckpt-m01", "ckpt-m1", "ckpt-m2"]
missing, bad, perm, notes = [], [], [], []
for t in tags:
    jf, mf = os.path.join(st, t + ".json"), os.path.join(st, t + ".md")
    if not (os.path.isfile(jf) and os.path.isfile(mf)):
        missing.append(t); continue
    try:
        d = json.load(open(jf))
        miss_k = sorted({"volume", "pacing", "ledger"} - set(d.keys())) if isinstance(d, dict) else ["<not-a-dict>"]
        if miss_k:
            bad.append((t, f"missing sections: {miss_k}")); continue
        sch = d.get("schema")
        if sch is None and isinstance(d.get("meta"), dict):
            sch = d["meta"].get("schema")
        if sch is None:
            notes.append((t, "schema absent (v1-era file?)"))
        elif not str(sch).startswith("traj-stats/"):
            bad.append((t, f"schema={sch!r}"))
    except Exception as e:
        bad.append((t, f"parse: {e}"))
    for f in (jf, mf):
        try:
            m = oct(os.stat(f).st_mode)[-3:]
            if m != "444": perm.append((t, os.path.basename(f), m))
        except Exception: pass
files = sorted(os.listdir(st))
print("  files:", ", ".join(files[:12]) + (" ..." if len(files) > 12 else ""))
vers = set()
for t in tags:
    jf = os.path.join(st, t + ".json")
    if not os.path.isfile(jf): continue
    try:
        d = json.load(open(jf))
        v = d.get("schema")
        if v is None and isinstance(d.get("meta"), dict): v = d["meta"].get("schema")
        vers.add(str(v))
    except Exception: pass
print("  schemas:", ", ".join(sorted(vers)))
if os.path.isdir(os.path.join(st, "pin")): print("  pin/:", len(os.listdir(os.path.join(st, "pin"))), "files")
rc = 0
if missing:
    if mod: print("  FAIL: stats files missing:", missing); rc = 1
    else: print("  NOTE: stats files missing (legacy era):", missing)
if bad:
    for t, why in bad: print("  FAIL: stats bad:", t, why)
    rc = 1
if perm:
    for t, f, m in perm:
        print("  FAIL: stats perm≠444:" if mod else "  NOTE: stats perm≠444 (legacy):", t, f, m)
    if mod: rc = 1
if notes:
    print("  NOTE:", "; ".join(f"{t}: {why}" for t, why in notes))
raise SystemExit(rc)
PY
  RC=$?; [ "$RC" -eq 0 ] || FAIL=1
else
  [ "$MODERN" = 1 ] && fail "x/stats missing on a modern-era run" || warn "x/stats missing (legacy era)"
fi

echo
if [ "$FAIL" = 0 ]; then echo "VERDICT: ACCEPTED"; exit 0; else echo "VERDICT: NOT ACCEPTED (see FAIL lines)"; exit 1; fi
