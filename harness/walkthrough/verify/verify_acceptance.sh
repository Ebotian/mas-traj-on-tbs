#!/bin/bash
# verify_acceptance.sh <job-dir>
# Host-side acceptance check for a walkthrough trial:
#   1 normal exit (state.json NORMAL), 2 collection complete, 3 git-reconstructible.
set -u
J="${1:?usage: verify_acceptance.sh <job-dir>}"
T=$(find "$J" -maxdepth 2 -type d -name 'task-restricted__*' | head -1)
echo "trial dir: $T"
FAIL=0
say() { echo "  $1"; }
[ -n "$T" ] || { echo "FAIL: no trial dir under $J"; exit 1; }

echo "== 1) normal exit"
STATE=$(find "$T" -name state.json -path '*collect*' | head -1)
if [ -z "$STATE" ]; then say "FAIL: collect/state.json not found"; FAIL=1; else
  NORMAL=$(python3 -c "import json,sys;d=json.load(open('$STATE'));print('NORMAL' if (d['rc_a']==0 and d['rc_b']==0 and d['stop_a'] and d['stop_b'] and d['consensus_on_main']) else 'ABNORMAL')")
  say "state.json -> $NORMAL"
  python3 -m json.tool "$STATE" | sed 's/^/    /'
  [ "$NORMAL" = "NORMAL" ] || FAIL=1
fi

echo "== 2) collection manifest"
BUNDLE=$(find "$T" -name protocol.bundle | head -1)
for pat in protocol.bundle git-log.txt state.json; do
  f=$(find "$T" -name "$pat" | head -1)
  if [ -z "$f" ]; then say "FAIL: $pat missing"; FAIL=1; else say "ok: $pat ($(stat -c%s "$f") B)"; fi
done
BOARDS=$(find "$T" -path '*boards*' -name '*.json' | wc -l)
CHATS=$(find "$T" -path '*chats*' -name '*.jsonl' | wc -l)
say "board items: $BOARDS | session chats: $CHATS"
[ "$BOARDS" -ge 2 ] || { say "WARN: fewer than 2 board items"; }
[ "$CHATS" -ge 2 ] || { say "WARN: fewer than 2 session transcripts"; }
GATELOG=$(find "$T" -name 'gate.log' | head -1)
[ -n "$GATELOG" ] && { say "gate.log lines: $(wc -l < "$GATELOG")"; sed 's/^/    /' "$GATELOG" | head -12; }

echo "== 3) git reconstructibility"
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
  )
  rm -rf "$S"
else
  say "FAIL: no bundle to reconstruct from"; FAIL=1
fi

echo
[ "$FAIL" = 0 ] && echo "VERDICT: ACCEPTED" || echo "VERDICT: NOT ACCEPTED (see FAIL lines)"
exit $FAIL
