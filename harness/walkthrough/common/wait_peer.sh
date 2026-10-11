#!/bin/bash
# wait_peer.sh <peer-actor> <required-round>
# Working-aware hybrid wait (2026-10-10 fix): exit 0 the moment the peer's
# round >= required. While the peer process is alive AND its session
# transcript is fresh (< WT_STALE_SEC), the wait keeps extending — a busy
# peer must not trip a budget. A dead peer exits 2 at once; 3 consecutive
# windows of a live-but-silent peer exit 2 ("peer-stalled") — the
# "3 x window with no response" rule. WT_MAX_WAIT_SEC caps the whole wait
# (default 13200 s, under the wrapper's session wall).
set -u
X="${WT_X:-/root/wt/x}"
SECS="${WT_WINDOW_SEC:-300}"
STALE="${WT_STALE_SEC:-360}"
MAXWAIT="${WT_MAX_WAIT_SEC:-13200}"
PEER="${1:?peer actor}"
NEED="${2:?required round}"
START=$(date +%s)
get() { cat "$X/ready-$PEER.round" 2>/dev/null || echo 0; }
# 0 = working/unknown(assume ok), 1 = alive but silent, 2 = dead
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
  [ "$(get)" -ge "$NEED" ] 2>/dev/null && exit 0
  if [ $(( $(date +%s) - START )) -ge "$MAXWAIT" ]; then
    echo "wait_peer: max wait ($MAXWAIT s) reached for peer-$PEER round $NEED" >&2
    exit 2
  fi
  inotifywait -q -t "$SECS" -e close_write -e moved_to -e create "$X" >/dev/null 2>&1 || true
  [ "$(get)" -ge "$NEED" ] 2>/dev/null && exit 0
  peer_state
  case $? in
    2) echo "wait_peer: peer-$PEER dead, round < $NEED" >&2; exit 2 ;;
    0) silent=0 ;;
    1) silent=$((silent + 1))
       if [ "$silent" -ge 3 ]; then
         echo "wait_peer: peer-$PEER silent for ~$((silent * SECS)) s (no transcript activity)" >&2
         exit 2
       fi ;;
  esac
done
