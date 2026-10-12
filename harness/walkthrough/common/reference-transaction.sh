#!/bin/bash
# git reference-transaction hook — milestone stats trigger (installed by run.sh).
# 触发:committed 状态的 refs/tags/ckpt-m*;无联网;幂等(traj_stats auto 自跳过已生成项)。
# 环境覆盖(宿主干跑):WT_STATS_PY / WT_REPO / WT_X。
[ "$1" = "committed" ] || exit 0
HIT=0
while read -r _old _new ref; do
  case "$ref" in refs/tags/ckpt-m*) HIT=1 ;; esac
done
[ "$HIT" = "1" ] || exit 0
python3 "${WT_STATS_PY:-/root/wt/traj_stats.py}" auto \
  "${WT_REPO:-/root/wt/repo}" "${WT_X:-/root/wt/x}" >/dev/null 2>&1 || true
exit 0
