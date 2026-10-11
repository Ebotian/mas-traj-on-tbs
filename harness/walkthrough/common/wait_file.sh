#!/bin/bash
# wait_file.sh <name> [<peer-actor>]
# Waits for x/<name> to appear (non-empty) and prints its content.
# Working-aware hybrid wait when a <peer-actor> is given (same rules as
# wait_peer.sh); without it, a plain WT_MAX_WAIT_SEC-bounded event wait.
set -u
X="${WT_X:-/root/wt/x}"
SECS="${WT_WINDOW_SEC:-300}"
STALE="${WT_STALE_SEC:-360}"
MAXWAIT="${WT_MAX_WAIT_SEC:-13200}"
NAME="${1:?file name}"
PEER="${2:-}"
F="$X/$NAME"
START=$(date +%s)
peer_state() {
  local pid uu f age
  pid=$(cat "$X/pid-$PEER" 2>/dev/null || echo "")
  [ -n "$pid" ] || return 0
  kill -0 "$pid" 2>/dev/null || return 2
  uu=$(cat "$X/session-$PEER.uuid" 2>/dev/null || echo "")
  [ -n "$uu" ] || return 0
  f=$(ls /root/.qwen/projects/*/chats/"$uu".jsonl 2>/dev/null | head -1)
  [ -n "$f" ] || return 0
  age=$(( $(date +%s) - $(stat -c %Y "$f") ))
  [ "$age" -lt "$STALE" ] && return 0 || return 1
}
silent=0
while :; do
  [ -s "$F" ] && { cat "$F"; exit 0; }
  if [ $(( $(date +%s) - START )) -ge "$MAXWAIT" ]; then
    echo "wait_file: max wait ($MAXWAIT s) reached for $NAME" >&2
    exit 2
  fi
  inotifywait -q -t "$SECS" -e close_write -e moved_to -e create "$X" >/dev/null 2>&1 || true
  [ -s "$F" ] && { cat "$F"; exit 0; }
  [ -n "$PEER" ] || continue
  peer_state
  case $? in
    2) echo "wait_file: peer-$PEER dead, $NAME missing" >&2; exit 2 ;;
    0) silent=0 ;;
    1) silent=$((silent + 1))
       if [ "$silent" -ge 3 ]; then
         echo "wait_file: peer-$PEER silent for ~$((silent * SECS)) s (no transcript activity)" >&2
         exit 2
       fi ;;
  esac
done
