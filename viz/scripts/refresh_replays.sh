#!/bin/bash
# refresh_replays.sh — 一键重生成全部 replay bundle(轨迹文件自动处理流程的复用入口)。
# 用法: bash viz/scripts/refresh_replays.sh [exp ...]  (缺省=全族;单个 exp = 只重建该 exp)
set -e
cd "$(dirname "$0")/.."

declare -A SRC=(
  [a2afusion]="/home/ebt/harbor-runs/spike-evidence/a2a-chats/wt-a /home/ebt/harbor-runs/spike-evidence/a2a-chats/wt-b"
  [a2aspike]="/home/ebt/harbor-runs/spike-evidence/a2a-chats/spike"
  [bump0251]="/home/ebt/harbor-runs/jobs/agent/bump-0251-flow"
  [microarch1]="/home/ebt/harbor-runs/jobs/agent/microarch-1"
  [microarch2]="/home/ebt/harbor-runs/jobs/agent/microarch-2"
  [tumor1]="/home/ebt/harbor-runs/jobs/agent/tumor-1"
  [tumor2]="/home/ebt/harbor-runs/jobs/agent/tumor-2"
  [w4]="/home/ebt/harbor-runs/jobs/agent/walkthrough-4"
  [w5]="/home/ebt/harbor-runs/jobs/agent/walkthrough-5"
  [w6]="/home/ebt/harbor-runs/jobs/agent/walkthrough-6"
  [w6n1]="/home/ebt/harbor-runs/jobs/agent/w6n1"
  [w6n2]="/home/ebt/harbor-runs/jobs/agent/w6n2"
  [w6n3]="/home/ebt/harbor-runs/jobs/agent/w6n3"
  [w6n4]="/home/ebt/harbor-runs/jobs/agent/w6n4"
  [w6np]="/home/ebt/harbor-runs/jobs/agent/w6n-pilot"
  [w6r1]="/home/ebt/harbor-runs/jobs/agent/w6r1"
  [w6r2]="/home/ebt/harbor-runs/jobs/agent/w6r2"
  [w6r3]="/home/ebt/harbor-runs/jobs/agent/w6r3"
  [w6r4]="/home/ebt/harbor-runs/jobs/agent/w6r4"
  [w6rp]="/home/ebt/harbor-runs/jobs/agent/w6r-pilot"
)
declare -A LABEL=(
  [a2afusion]="A2A 融合(双 daemon·互寻址)"
  [a2aspike]="A2A spike(单 daemon·五检)"
  [bump0251]="bump-0251-flow 走查(0.25.1 全流程验证)"
  [microarch1]="microarch-modeling · microarch-1"
  [microarch2]="microarch-modeling · microarch-2"
  [tumor1]="tumor-immune-interface · tumor-1"
  [tumor2]="tumor-immune-interface · tumor-2"
  [w4]="walkthrough-4(首份 NORMAL 走查)"
  [w5]="walkthrough-5(干净重跑,no-ff)"
  [w6]="walkthrough-6(机制排练"
  [w6n1]="w6-4×2·N#1"
  [w6n2]="w6-4×2·N#2"
  [w6n3]="w6-4×2·N#3"
  [w6n4]="w6-4×2·N#4"
  [w6np]="w6-4×2·N冒烟"
  [w6r1]="w6-4×2·R#1"
  [w6r2]="w6-4×2·R#2"
  [w6r3]="w6-4×2·R#3"
  [w6r4]="w6-4×2·R#4"
  [w6rp]="w6-4×2·R冒烟"
)

EXPS=("$@")
if [ ${#EXPS[@]} -eq 0 ]; then EXPS=(a2afusion a2aspike bump0251 microarch1 microarch2 tumor1 tumor2 w4 w5 w6 w6n1 w6n2 w6n3 w6n4 w6np w6r1 w6r2 w6r3 w6r4 w6rp); fi
for exp in "${EXPS[@]}"; do
  node scripts/build_replay.mjs ${SRC[$exp]} --exp "$exp" --label "${LABEL[$exp]}"
done
echo "refresh done: ${EXPS[*]}"
