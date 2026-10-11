#!/bin/bash
# verify_acceptance_tumor.sh <job-dir>
# Host-side acceptance check for a dual-agent TUMOR trial:
#   1 normal exit (state.json NORMAL: rc 0/0, both stop files, consensus on main,
#     five deliverables present)
#   2 collection complete (bundle + git-log + state + boards + chats + x + results + subs)
#   3 git-reconstructible from protocol.bundle
#   4 verifier reward (the graded /root/results submission)
set -u
J="${1:?usage: verify_acceptance_tumor.sh <job-dir>}"
T=$(find "$J" -maxdepth 2 -type d -name 'task-restricted__*' | head -1)
echo "trial dir: $T"
FAIL=0
say() { echo "  $1"; }
[ -n "$T" ] || { echo "FAIL: no trial dir under $J"; exit 1; }

echo "== 1) normal exit"
STATE=$(find "$T" -name state.json -path '*collect*' | head -1)
if [ -z "$STATE" ]; then say "FAIL: collect/state.json not found"; FAIL=1; else
  NORMAL=$(python3 -c "import json;d=json.load(open('$STATE'));print('NORMAL' if (d['rc_a']==0 and d['rc_b']==0 and d['stop_a'] and d['stop_b'] and d['consensus_on_main'] and d.get('deliverables_present')) else 'ABNORMAL')")
  say "state.json -> $NORMAL"
  python3 -m json.tool "$STATE" | sed 's/^/    /'
  [ "$NORMAL" = "NORMAL" ] || FAIL=1
fi

echo "== 2) collection manifest"
for pat in protocol.bundle git-log.txt state.json; do
  f=$(find "$T" -name "$pat" | head -1)
  if [ -z "$f" ]; then say "FAIL: $pat missing"; FAIL=1; else say "ok: $pat ($(stat -c%s "$f") B)"; fi
done
for d in results sub-a sub-b x; do
  n=$(find "$T" -type d -name "$d" | head -1)
  if [ -z "$n" ]; then say "WARN: collect/$d missing"; else
    say "ok: collect/$d ($(du -sh "$n" 2>/dev/null | cut -f1), $(find "$n" -type f | wc -l) files)"
  fi
done
BOARDS=$(find "$T" -path '*boards*' -name '*.json' | wc -l)
CHATS=$(find "$T" -path '*chats*' -name '*.jsonl' | wc -l)
say "board items: $BOARDS | session chats: $CHATS"
GATELOG=$(find "$T" -name 'gate.log' | head -1)
[ -n "$GATELOG" ] && { say "gate.log lines: $(wc -l < "$GATELOG")"; sed 's/^/    /' "$GATELOG" | head -12; }

echo "== 3) git reconstructibility"
BUNDLE=$(find "$T" -name protocol.bundle | head -1)
if [ -n "$BUNDLE" ]; then
  S=$(mktemp -d /tmp/wt-verify-XXXX)
  git clone -q "$BUNDLE" "$S/repo" 2>&1 && say "clone ok"
  ( cd "$S/repo"
    echo "  branches: $(git branch -a | tr '\n' ' ')"
    echo "  tags: $(git tag | tr '\n' ' ')"
    n=$(git log --all --format=%B | grep -cE 'Round: [0-9]')
    echo "  commits carrying Round markers: $n"
    echo "  graph head:"; git log --graph --oneline --decorate --all | head -14 | sed 's/^/    /'
    git show main:consensus.md >/dev/null 2>&1 && echo "  consensus.md on main: yes" || echo "  consensus.md on main: NO"
    git show main:submission/tumor_interface_qc.csv >/dev/null 2>&1 && echo "  submission/ on main: yes" || echo "  submission/ on main: NO"
  )
  rm -rf "$S"
else
  say "FAIL: no bundle to reconstruct from"; FAIL=1
fi

echo "== 4) verifier reward"
R="$T/verifier/reward.txt"
[ -f "$R" ] && say "reward: $(cat "$R")" || say "FAIL: verifier reward.txt missing"
M="$T/verifier/metrics.json"
[ -f "$M" ] && python3 -c "import json;d=json.load(open('$M'));print('  metrics:',json.dumps(d)[:400])"

echo "== 5) trajectory tooling"
TRAJ="$(cd "$(dirname "$0")/.." && pwd)/common/traj.py"
XD=$(find "$T" -path '*collect/x' -type d | head -1)
for side in a b; do
  idx=$(find "$T" -name "traj-$side.full-index.jsonl" | head -1)
  if [ -z "$idx" ]; then say "FAIL: collect/traj-$side.full-index.jsonl missing"; FAIL=1; else
    say "ok: traj-$side.full-index.jsonl ($(wc -l < "$idx") rows)"
  fi
done
if [ -n "$XD" ] && [ -f "$TRAJ" ]; then
  for pair in "a b" "b a"; do
    set -- $pair
    CHAT=$(find "$T" -name "$(cat "$XD/session-$1.uuid" 2>/dev/null).jsonl" | head -1)
    if [ -n "$CHAT" ]; then
      OUT=$(python3 "$TRAJ" audit-seal --actor "$1" --peer "$2" --transcript "$CHAT" 2>&1); RC=$?
      LINE=$(printf '%s\n' "$OUT" | grep 'audit-seal' | head -1)
      say "$LINE (rc=$RC)"
      [ "$RC" -eq 0 ] || { say "FAIL: seal audit found violations for actor $1"; FAIL=1; }
    fi
  done
else
  say "WARN: x/ or traj.py missing — audit skipped"
fi

echo
[ "$FAIL" = 0 ] && echo "VERDICT: ACCEPTED" || echo "VERDICT: NOT ACCEPTED (see FAIL lines)"
exit $FAIL
