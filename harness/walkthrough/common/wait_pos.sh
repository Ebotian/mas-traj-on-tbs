#!/bin/bash
# wait_pos.sh <peer-actor> <round>
# Waits for the peer's round-end POSITION file x/pos-<peer>-r<round>
# (content: continue | stop) and prints it. Working-aware hybrid wait (same
# rules as wait_peer.sh: keep extending while the peer works; dead -> exit 2;
# 3 silent windows -> exit 2; WT_MAX_WAIT_SEC cap).
set -u
X="${WT_X:-/root/wt/x}"
SECS="${WT_WINDOW_SEC:-300}"
STALE="${WT_STALE_SEC:-360}"
MAXWAIT="${WT_MAX_WAIT_SEC:-13200}"
PEER="${1:?peer actor}"
N="${2:?round}"
F="$X/pos-$PEER-r$N"
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
    echo "wait_pos: max wait ($MAXWAIT s) reached for peer-$PEER position round $N" >&2
    exit 2
  fi
  inotifywait -q -t "$SECS" -e close_write -e moved_to -e create "$X" >/dev/null 2>&1 || true
  [ -s "$F" ] && { cat "$F"; exit 0; }
  peer_state
  case $? in
    2) echo "wait_pos: peer-$PEER dead, position for round $N missing" >&2; exit 2 ;;
    0) silent=0 ;;
    1) silent=$((silent + 1))
       if [ "$silent" -ge 3 ]; then
         echo "wait_pos: peer-$PEER silent for ~$((silent * SECS)) s (no transcript activity)" >&2
         exit 2
       fi ;;
  esac
done
