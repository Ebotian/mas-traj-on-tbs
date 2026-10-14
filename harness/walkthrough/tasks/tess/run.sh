#!/bin/bash
# tasks/tess/run.sh — dual-agent TESS transit-vetting run wrapper (runs IN the container).
# Same machinery as the tumor wrapper (two continuous equal sessions; git commits
# demarcate rounds; PreToolUse gate barrier; board exchange; collection), with the
# real task:
#   prompt = task instruction (canary-free) + tasks/tess/protocol.md
#   deliverable = the single artifact /app/vetter/vet.py (<= 5,000,000 bytes; graded by the verifier)
# Normal exit = both sessions rc 0 AND both stop files AND consensus.md on main
# AND the deliverable present at /app/vetter/vet.py within the size bound.
SRC=/root/wt-src
WT=/root/wt
X=$WT/x
C=$WT/collect
LOGS=/logs/agent
SESSION_WALL="${WT_SESSION_WALL:-13500}"   # < tasks/tess/agent.py exec cap 14100 < harbor rail 14400
FRONT_PHASE="${WT_FRONT_PHASE:-1}"
export WT_EXPECT_TAGS="${WT_EXPECT_TAGS:-$([ "$FRONT_PHASE" = "1" ] && echo ckpt-m00,ckpt-m01,ckpt-m1,ckpt-m2 || echo ckpt-m1,ckpt-m2)}"
mkdir -p "$WT" "$X" "$C" "$LOGS"
set -a; . "$SRC/walkthrough.env"; set +a
: "${A_KEY:?A_KEY missing from walkthrough.env}"
: "${B_KEY:?B_KEY missing from walkthrough.env}"
cp "$SRC/common/gate.py" "$SRC/common/wait_peer.sh" "$SRC/common/wait_pos.sh" "$SRC/common/wait_file.sh" "$SRC/common/post-commit.sh" "$SRC/common/traj.py" "$SRC/common/traj_index.py" "$SRC/common/refs.py" "$SRC/common/recover.py" "$SRC/common/git_structure.py" "$SRC/common/front_phase.py" "$SRC/common/traj_stats.py" "$WT/"
chmod +x "$WT/gate.py" "$WT/wait_peer.sh" "$WT/wait_pos.sh" "$WT/wait_file.sh" "$WT/post-commit.sh"

# workspace
cd "$WT"
if [ ! -d repo ]; then
  mkdir repo; cd repo
  git init -q -b main
  git config user.name walkthrough; git config user.email wt@local
  printf '# dual-agent tess run scratch\n' > README.md
  printf '.qwen/\n.traj/\n' > .gitignore
  git add README.md .gitignore; git commit -qm "init"
fi
cd "$WT/repo"
cp "$SRC/common/post-commit.sh" .git/hooks/post-commit && chmod +x .git/hooks/post-commit
cp "$SRC/common/reference-transaction.sh" .git/hooks/reference-transaction && chmod +x .git/hooks/reference-transaction
git worktree add -q ../a -b a 2>/dev/null || true
git worktree add -q ../b -b b 2>/dev/null || true

# per-side WORKSPACE settings: effort pin + the PreToolUse round gate.
mkdir -p "$WT/a/.qwen" "$WT/b/.qwen"
cat > "$WT/a/.qwen/settings.json" <<'EOF'
{"model": {"reasoningEffort": "max"}, "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "python3 /root/wt/gate.py", "timeout": 940, "name": "round-gate"}]}]}}
EOF
cat > "$WT/b/.qwen/settings.json" <<'EOF'
{"model": {"reasoningEffort": "xhigh"}, "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "python3 /root/wt/gate.py", "timeout": 940, "name": "round-gate"}]}]}}
EOF
cp "$WT/a/.qwen/settings.json" "$X/effort-a.json"
cp "$WT/b/.qwen/settings.json" "$X/effort-b.json"

# prompts: instruction verbatim + the tess protocol, actor-substituted
for side in a b; do
  if [ "$side" = a ]; then peer=b; else peer=a; fi
  { cat "$SRC/tasks/tess/instruction.md"; printf '\n\n---\n\n'; \
    if [ "${FRONT_PHASE:-1}" = "1" ]; then \
      sed -e "s/@@ACTOR@@/$side/g" -e "s/@@PEER@@/$peer/g" "$SRC/common/front-phase.md"; \
      printf '\n\n---\n\n'; \
    fi; \
    sed -e "s/@@ACTOR@@/$side/g" -e "s/@@PEER@@/$peer/g" "$SRC/tasks/tess/protocol.md"; \
  } > "$WT/prompt-$side.txt"
done

UA=$(python3 -c 'import uuid;print(uuid.uuid4())')
UB=$(python3 -c 'import uuid;print(uuid.uuid4())')
echo "$UA" > "$X/session-a.uuid"; echo "$UB" > "$X/session-b.uuid"
# stable handles for the sealed share surface (targets appear post-M1)
ln -sfn "traj-a.upto-cut.jsonl" "$X/traj-a.jsonl"
ln -sfn "traj-b.upto-cut.jsonl" "$X/traj-b.jsonl"

( cd "$WT/a" && timeout "$SESSION_WALL" qwen -p "$(cat "$WT/prompt-a.txt")" \
    --auth-type openai --openai-api-key "$A_KEY" --openai-base-url "$A_BASE" \
    -m deepseek-flash --approval-mode yolo --chat-recording --session-id "$UA" \
    --telemetry --telemetry-outfile "$LOGS/otel-a.json" \
    > "$LOGS/wa-a.out" 2>&1 ) &
PA=$!; echo "$PA" > "$X/pid-a"
( cd "$WT/b" && timeout "$SESSION_WALL" qwen -p "$(cat "$WT/prompt-b.txt")" \
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

# Rail-kill insurance: harbor removes the container at trial end even with
# --no-delete, so a run killed mid-flight would otherwise lose the workspace.
# Snapshot the recovery material into the collected dir every 10 minutes.
snapshot() {
  local part="$C/.snap"
  rm -rf "$part"; mkdir -p "$part"
  git -C "$WT/repo" bundle create "$part/protocol.bundle" --all >/dev/null 2>&1 || true
  git -C "$WT/repo" log --graph --decorate --all --date=iso > "$part/git-log.txt" 2>&1 || true
  cp -r "$X" "$part/x" 2>/dev/null || true
  mkdir -p "$part/boards"; cp -r /root/.qwen/boards/. "$part/boards/" 2>/dev/null || true
  cp /app/vetter/vet.py "$part/vet.py" 2>/dev/null || true
  cp -r "$WT/a/sub-a" "$part/sub-a" 2>/dev/null || true
  cp -r "$WT/b/sub-b" "$part/sub-b" 2>/dev/null || true
  python3 - "$X" "$part" <<'PY2'
import json, pathlib, sys, time
x = pathlib.Path(sys.argv[1]); p = pathlib.Path(sys.argv[2])
def rd(f, d="0"):
    try: return (x / f).read_text().strip()
    except Exception: return d
(p / "snapshot-state.json").write_text(json.dumps({
    "snapshot_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "rounds": {"a": rd("ready-a.round"), "b": rd("ready-b.round")},
    "stop": {"a": (x / "stop-a").exists(), "b": (x / "stop-b").exists()},
    "abort": {"a": (x / "abort-a").exists(), "b": (x / "abort-b").exists()},
}, indent=1))
PY2
  rm -rf "$C/snapshot"; mv "$part" "$C/snapshot"
}
( while kill -0 "$PA" 2>/dev/null || kill -0 "$PB" 2>/dev/null; do
    sleep 600
    kill -0 "$PA" 2>/dev/null || kill -0 "$PB" 2>/dev/null || break
    snapshot
  done ) &
WATCH=$!

wait "$PA"; RA=$?
wait "$PB"; RB=$?
if [ -n "${SOPW:-}" ]; then kill "$SOPW" 2>/dev/null || true; fi
kill "$WATCH" 2>/dev/null || true
rm -rf "$C/.snap"
echo "$RA $RB" > "$X/rcs"

# —— 收口机制补充(2026-10-12,用户裁定「只做机制补充」):git duty/结构判定 + 受限唤醒(≤1/侧) ——
# 关断:WT_RECOVER=0;时限:WT_WAKE_TIMEOUT(秒,默认 900)。只新增提交/删残引,不改写历史。
if [ "${WT_RECOVER:-1}" = "1" ]; then
  snapshot 2>/dev/null || true
  python3 "$WT/recover.py" "$WT/repo" "$X" "$LOGS" "$UA" "$UB" >> "$LOGS/recover.log" 2>&1 || true
fi

# —— 正常退出 git 结构门(任务无关;v3 前段后终签集=WT_EXPECT_TAGS)——
# 检查器 = common/git_structure.py(纯读);不通过 → structure_ok=false;结果缺失=unknown;未撤回 abort 有效 → 均按 ABNORMAL 退出
python3 "$WT/git_structure.py" "$WT/repo" "$X/git-structure.json" --mode final --expect-tags "${WT_EXPECT_TAGS:-ckpt-m00,ckpt-m01,ckpt-m1,ckpt-m2}" > "$LOGS/git-structure.log" 2>&1 || true

# collection (before we exit; the bundle makes the workspace reconstructible)
git -C "$WT/repo" bundle create "$C/protocol.bundle" --all >/dev/null 2>&1 || true
git -C "$WT/repo" log --graph --decorate --all --date=iso > "$C/git-log.txt" 2>&1 || true
mkdir -p "$C/boards" "$C/chats"
cp -r /root/.qwen/boards/. "$C/boards/" 2>/dev/null || true
cp /root/.qwen/projects/*/chats/*.jsonl "$C/chats/" 2>/dev/null || true
cp "$WT/a/.qwen/settings.json" "$C/ws-settings-a.json" 2>/dev/null || true
cp "$WT/b/.qwen/settings.json" "$C/ws-settings-b.json" 2>/dev/null || true
cp -r "$X" "$C/x" 2>/dev/null || true
cp /app/vetter/vet.py "$C/vet.py" 2>/dev/null || true
cp -r "$WT/a/sub-a" "$C/sub-a" 2>/dev/null || true
cp -r "$WT/b/sub-b" "$C/sub-b" 2>/dev/null || true
# 收口唤醒为删分支会先清 worktree(2026-10-14 发现),staging 目录可能已不在:以唤醒前 snapshot 回退补全
[ -e "$C/sub-a" ] || cp -r "$C/snapshot/sub-a" "$C/sub-a" 2>/dev/null || true
[ -e "$C/sub-b" ] || cp -r "$C/snapshot/sub-b" "$C/sub-b" 2>/dev/null || true
for side in a b; do
  UU=$(cat "$X/session-$side.uuid" 2>/dev/null || echo "")
  T="/root/.qwen/projects/-root-wt-$side/chats/$UU.jsonl"
  if [ -f "$T" ]; then
    python3 "$WT/traj_index.py" build "$T" "$C/traj-$side.full-index.jsonl" >/dev/null 2>&1 || true
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
p = pathlib.Path("/app/vetter/vet.py")
size = p.stat().st_size if p.exists() else 0
deliv = {"vet.py": size}
deliv_present = 0 < size <= 5000000
def rdj(p):
    try: return json.loads(p.read_text())
    except Exception: return None
rec = rdj(x / "recover.json")
gs = rdj(x / "git-structure.json")
# 结构结果三态:缺结果=unknown(≠通过);有效 abort(未撤回)不计正常退出
structure_ok = None if gs is None else bool(gs.get("ok"))
structure_state = "unknown" if structure_ok is None else ("pass" if structure_ok else "fail")
abort_withdrawn = {s: (x / ("abort-" + s + ".withdrawn")).exists() for s in ("a", "b")}
abort_effective = {s: (x / ("abort-" + s)).exists() and not abort_withdrawn[s] for s in ("a", "b")}
state = {
    "rc_a": int(sys.argv[3]), "rc_b": int(sys.argv[4]),
    "consensus_on_main": bool(int(sys.argv[5])),
    "stop_a": (x / "stop-a").exists(), "stop_b": (x / "stop-b").exists(),
    "abort_a": (x / "abort-a").exists(), "abort_b": (x / "abort-b").exists(),
    "abort_withdrawn": abort_withdrawn, "abort_effective": abort_effective,
    "rounds": {"a": rd(x / "ready-a.round"), "b": rd(x / "ready-b.round")},
    "deliverables": deliv, "deliverables_present": deliv_present,
    "effort": {"a": rd(x / "effort-a.json")[:200], "b": rd(x / "effort-b.json")[:200]},
    "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "recover": rec, "recovered_run": bool(rec and rec.get("wakes")),
    "git_structure": gs, "structure_ok": structure_ok, "structure_state": structure_state,
}
normal = (state["rc_a"] == 0 and state["rc_b"] == 0 and
          state["stop_a"] and state["stop_b"] and state["consensus_on_main"] and
          deliv_present and structure_ok is True and
          not abort_effective["a"] and not abort_effective["b"])
state["normal"] = normal
(c / "state.json").write_text(json.dumps(state, indent=1))
print("TESS", "NORMAL" if normal else "ABNORMAL", json.dumps(state), flush=True)
sys.exit(0 if normal else 3)
PY
exit $?
