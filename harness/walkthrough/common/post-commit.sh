#!/bin/bash
# git post-commit hook (installed by run.sh into the shared repo).
# Publishes this side's round readiness: the event source the gate waits on.
# Once M1 exists it also advances the peer-visible trajectory snapshot:
#   x/traj-<actor>.upto-cut.jsonl = a growing PREFIX of this actor's transcript,
#   appended only at commits -> cut content by construction (nothing beyond the
#   actor's last commit ever enters it; committed-line prefixes are line-stable).
# WT_CHATS_ROOT exists so this hook can be dry-run outside the container.
X="${WT_X:-/root/wt/x}"
CHATS="${WT_CHATS_ROOT:-/root/.qwen/projects}"
TOP=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
ACTOR=$(basename "$TOP")
case "$ACTOR" in a|b) ;; *) exit 0 ;; esac
MSG=$(git log -1 --format=%B)
N=$(printf '%s\n' "$MSG" | grep -oE 'Round: *[0-9]+' | head -1 | grep -oE '[0-9]+')
if [ -n "${N:-}" ]; then
  echo "$N" > "$X/ready-$ACTOR.round"
  git rev-parse HEAD > "$X/sha-$ACTOR-r$N.txt"
fi
if git tag -l ckpt-m1 | grep -qx ckpt-m1; then
  UU=$(cat "$X/session-$ACTOR.uuid" 2>/dev/null || true)
  T="$CHATS/-root-wt-$ACTOR/chats/$UU.jsonl"
  SNAP="$X/traj-$ACTOR.upto-cut.jsonl"
  if [ -n "$UU" ] && [ -f "$T" ]; then
    NT=$(wc -l < "$T")
    NS=0
    [ -f "$SNAP" ] && NS=$(wc -l < "$SNAP")
    if [ "$NT" -lt "$NS" ]; then
      head -n "$NT" "$T" > "$SNAP.tmp" && mv "$SNAP.tmp" "$SNAP"
    elif [ "$NT" -gt "$NS" ]; then
      sed -n "$((NS + 1)),${NT}p" "$T" >> "$SNAP"
    fi
  fi
fi
exit 0
