#!/bin/bash
# tasks/walkthrough/run.sh — dual-agent scripted walkthrough wrapper (runs IN the container).
# Prepares the workspace + per-side settings + gate, launches the two continuous
# sessions as equals (A = deepseek-flash effort max; B = qwen3.8-flash xhigh),
# waits, writes close-out state and the collection bundle, and exits 0 (normal)
# or 3 (abnormal). Normal = both sessions rc 0 AND both stop files AND
# consensus.md on main.
SRC=/root/wt-src
WT=/root/wt
X=$WT/x
C=$WT/collect
LOGS=/logs/agent
FRONT_PHASE="${WT_FRONT_PHASE:-1}"
export WT_EXPECT_TAGS="${WT_EXPECT_TAGS:-$([ "$FRONT_PHASE" = "1" ] && echo ckpt-m00,ckpt-m01,ckpt-m1,ckpt-m2 || echo ckpt-m1,ckpt-m2)}"
mkdir -p "$WT" "$X" "$C" "$LOGS"
# Credentials: --env-file reaches the harbor PROCESS, not this container, so
# source the mounted env file here (mode 600, read-only mount) and fail loud.
set -a; . "$SRC/walkthrough.env"; set +a
: "${A_KEY:?A_KEY missing from walkthrough.env}"
: "${B_KEY:?B_KEY missing from walkthrough.env}"
# Placeholders for the task's declared artifacts: the walkthrough solves no
# task, but harbor collects these paths - missing files would fail the trial
# collection and mask the wrapper's own verdict.
mkdir -p /root/results
for f in cluster_annotations tumor_interface_qc cell_signed_distances patient_distance_profiles interface_gradients; do
  [ -f "/root/results/$f.csv" ] || printf 'placeholder\n' > "/root/results/$f.csv"
done
cp "$SRC/common/gate.py" "$SRC/common/wait_peer.sh" "$SRC/common/post-commit.sh" "$SRC/common/traj.py" "$SRC/common/traj_index.py" "$SRC/common/refs.py" "$SRC/common/recover.py" "$SRC/common/git_structure.py" "$SRC/common/front_phase.py" "$SRC/common/traj_stats.py" "$WT/"
chmod +x "$WT/gate.py" "$WT/wait_peer.sh" "$WT/post-commit.sh"

# workspace
cd "$WT"
if [ ! -d repo ]; then
  mkdir repo; cd repo
  git init -q -b main
  git config user.name walkthrough; git config user.email wt@local
  printf '# walkthrough protocol scratch\n' > README.md
  printf '.qwen/\n' > .gitignore
  git add README.md .gitignore; git commit -qm "init"
fi
cd "$WT/repo"
cp "$SRC/common/post-commit.sh" .git/hooks/post-commit && chmod +x .git/hooks/post-commit
cp "$SRC/common/reference-transaction.sh" .git/hooks/reference-transaction && chmod +x .git/hooks/reference-transaction
git worktree add -q ../a -b a 2>/dev/null || true
git worktree add -q ../b -b b 2>/dev/null || true

# per-side WORKSPACE settings (the two sessions share HOME; the worktree scope
# is what separates them): effort pin + the PreToolUse round gate.
mkdir -p "$WT/a/.qwen" "$WT/b/.qwen"
cat > "$WT/a/.qwen/settings.json" <<'EOF'
{"model": {"reasoningEffort": "max"}, "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "python3 /root/wt/gate.py", "timeout": 940, "name": "round-gate"}]}]}}
EOF
cat > "$WT/b/.qwen/settings.json" <<'EOF'
{"model": {"reasoningEffort": "xhigh"}, "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "python3 /root/wt/gate.py", "timeout": 940, "name": "round-gate"}]}]}}
EOF
# effort evidence (flows into the collection via x/)
cp "$WT/a/.qwen/settings.json" "$X/effort-a.json"
cp "$WT/b/.qwen/settings.json" "$X/effort-b.json"

# prompts (WT_PROMPT selects the variant inside this task dir; default prompt.md)
PROMPT="${WT_PROMPT:-prompt.md}"
echo "$PROMPT" > "$X/prompt-variant"
{ if [ "${FRONT_PHASE:-1}" = "1" ]; then sed -e "s/@@ACTOR@@/a/g" -e "s/@@PEER@@/b/g" "$SRC/common/front-phase.md"; printf '\n\n---\n\n'; fi; \
  sed -e "s/@@ACTOR@@/a/g" -e "s/@@PEER@@/b/g" "$SRC/tasks/walkthrough/$PROMPT"; } > "$WT/prompt-a.txt"
{ if [ "${FRONT_PHASE:-1}" = "1" ]; then sed -e "s/@@ACTOR@@/b/g" -e "s/@@PEER@@/a/g" "$SRC/common/front-phase.md"; printf '\n\n---\n\n'; fi; \
  sed -e "s/@@ACTOR@@/b/g" -e "s/@@PEER@@/a/g" "$SRC/tasks/walkthrough/$PROMPT"; } > "$WT/prompt-b.txt"

UA=$(python3 -c 'import uuid;print(uuid.uuid4())')
UB=$(python3 -c 'import uuid;print(uuid.uuid4())')
echo "$UA" > "$X/session-a.uuid"; echo "$UB" > "$X/session-b.uuid"
# stable handles for the sealed share surface (targets appear post-M1)
ln -sfn "traj-a.upto-cut.jsonl" "$X/traj-a.jsonl"
ln -sfn "traj-b.upto-cut.jsonl" "$X/traj-b.jsonl"

( cd "$WT/a" && qwen -p "$(cat "$WT/prompt-a.txt")" \
    --auth-type openai --openai-api-key "$A_KEY" --openai-base-url "$A_BASE" \
    -m deepseek-flash --approval-mode yolo --chat-recording --session-id "$UA" \
    --telemetry --telemetry-outfile "$LOGS/otel-a.json" \
    > "$LOGS/wa-a.out" 2>&1 ) &
PA=$!; echo "$PA" > "$X/pid-a"
( cd "$WT/b" && qwen -p "$(cat "$WT/prompt-b.txt")" \
    --auth-type openai --openai-api-key "$B_KEY" --openai-base-url "$B_BASE" \
    -m qwen3.8-flash --approval-mode yolo --chat-recording --session-id "$UB" \
    --telemetry --telemetry-outfile "$LOGS/otel-b.json" \
    > "$LOGS/wa-b.out" 2>&1 ) &
PB=$!; echo "$PB" > "$X/pid-b"

# —— v3 前段:m00 落签后系统下发 SOP(看门件;≤60s 迟滞;WT_FRONT_PHASE=0 关) ——
if [ "${FRONT_PHASE:-1}" = "1" ]; then
  ( while kill -0 "$PA" 2>/dev/null || kill -0 "$PB" 2>/dev/null; do
      python3 "$WT/front_phase.py" dispatch "$WT/repo" "$X" "$LOGS" >/dev/null 2>&1 || true
      python3 "$WT/traj_stats.py" auto "$WT/repo" "$X" >/dev/null 2>&1 || true
      sleep 60
    done ) &
  SOPW=$!
fi

wait "$PA"; RA=$?
wait "$PB"; RB=$?
if [ -n "${SOPW:-}" ]; then kill "$SOPW" 2>/dev/null || true; fi
echo "$RA $RB" > "$X/rcs"

# —— 收口机制补充(2026-10-12,用户裁定「只做机制补充」):git duty/结构判定 + 受限唤醒(≤1/侧) ——
# 关断:WT_RECOVER=0;时限:WT_WAKE_TIMEOUT(秒,默认 900)。只新增提交/删残引,不改写历史。
if [ "${WT_RECOVER:-1}" = "1" ]; then
  python3 "$WT/recover.py" "$WT/repo" "$X" "$LOGS" "$UA" "$UB" >> "$LOGS/recover.log" 2>&1 || true
fi

# —— 正常退出 git 结构门(任务无关;v3 前段后终签集=WT_EXPECT_TAGS)——
# 检查器 = common/git_structure.py(纯读);不通过 → state.structure_ok=false → 按 ABNORMAL 退出
python3 "$WT/git_structure.py" "$WT/repo" "$X/git-structure.json" --mode final --expect-tags "${WT_EXPECT_TAGS:-ckpt-m00,ckpt-m01,ckpt-m1,ckpt-m2}" > "$LOGS/git-structure.log" 2>&1 || true

# collection (before we exit; the bundle makes the workspace reconstructible)
git -C "$WT/repo" bundle create "$C/protocol.bundle" --all >/dev/null 2>&1 || true
git -C "$WT/repo" log --graph --decorate --all --date=iso > "$C/git-log.txt" 2>&1 || true
mkdir -p "$C/boards" "$C/chats"
cp -r /root/.qwen/boards/walkthrough/. "$C/boards/" 2>/dev/null || true
cp /root/.qwen/projects/*/chats/*.jsonl "$C/chats/" 2>/dev/null || true
cp -r "$WT/a/.qwen/settings.json" "$C/ws-settings-a.json" 2>/dev/null || true
cp -r "$WT/b/.qwen/settings.json" "$C/ws-settings-b.json" 2>/dev/null || true
cp -r "$X" "$C/x" 2>/dev/null || true
# new-infra records: full indexes, evidence bibliographies, seal audits
for side in a b; do
  UU=$(cat "$X/session-$side.uuid" 2>/dev/null || echo "")
  T="/root/.qwen/projects/-root-wt-$side/chats/$UU.jsonl"
  if [ -f "$T" ]; then
    python3 "$WT/traj_index.py" build "$T" "$C/traj-$side.full-index.jsonl" >/dev/null 2>&1 || true
  fi
  python3 "$WT/refs.py" --actor "$side" --refs "$WT/$side/refs-$side.jsonl" \
    --xdir "$X" --repo "$WT/repo" --round 7 biblio > "$C/refs-$side.biblio.txt" 2>&1 || true
done
for pair in "a b" "b a"; do
  set -- $pair
  UU=$(cat "$X/session-$1.uuid" 2>/dev/null || echo "")
  T="/root/.qwen/projects/-root-wt-$1/chats/$UU.jsonl"
  if [ -f "$T" ]; then
    python3 "$WT/traj.py" audit-seal --actor "$1" --peer "$2" --transcript "$T" \
      > "$C/seal-$1-vs-$2.txt" 2>&1 || true
  fi
done

CONSENSUS=0
git -C "$WT/repo" show main:consensus.md >/dev/null 2>&1 && CONSENSUS=1

python3 - "$X" "$C" "$RA" "$RB" "$CONSENSUS" <<'PY'
import json, pathlib, sys, time
x = pathlib.Path(sys.argv[1]); c = pathlib.Path(sys.argv[2])
def rd(p, d="0"):
    try: return p.read_text().strip()
    except Exception: return d
def rdj(p):
    try: return json.loads(p.read_text())
    except Exception: return None
rec = rdj(x / "recover.json")
gs = rdj(x / "git-structure.json")
structure_ok = (gs is None) or bool(gs.get("ok"))
state = {
    "rc_a": int(sys.argv[3]), "rc_b": int(sys.argv[4]),
    "consensus_on_main": bool(int(sys.argv[5])),
    "stop_a": (x / "stop-a").exists(), "stop_b": (x / "stop-b").exists(),
    "abort_a": (x / "abort-a").exists(), "abort_b": (x / "abort-b").exists(),
    "rounds": {"a": rd(x / "ready-a.round"), "b": rd(x / "ready-b.round")},
    "effort": {"a": rd(x / "effort-a.json")[:200], "b": rd(x / "effort-b.json")[:200]},
    "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "recover": rec, "recovered_run": bool(rec and rec.get("wakes")),
    "git_structure": gs, "structure_ok": structure_ok,
}
normal = (state["rc_a"] == 0 and state["rc_b"] == 0 and
          state["stop_a"] and state["stop_b"] and state["consensus_on_main"] and
          structure_ok)
state["normal"] = normal
(c / "state.json").write_text(json.dumps(state, indent=1))
print("WALKTHROUGH", "NORMAL" if normal else "ABNORMAL", json.dumps(state), flush=True)
sys.exit(0 if normal else 3)
PY
exit $?
