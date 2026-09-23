#!/usr/bin/env bash
# =============================================================================
# Mechanism C -- can the AGENT lane run inside a container that sees only the
# session workspace?  This script builds the topology and measures it.
#
#   ./run.sh all      env -> up -> probe -> call -> tool -> verify
#   ./run.sh env      the image/binary inventory (what the CLI needs)
#   ./run.sh up       network + metering proxy + both agent containers
#   ./run.sh probe    the in-container probe, both variants
#   ./run.sh call     one real metered model call per variant (needs DS_KEY)
#   ./run.sh tool     the tool loop: the agent writes and runs a file (needs DS_KEY)
#   ./run.sh verify   host-side checks: ledger, containers, postgres untouched
#   ./run.sh down     remove everything this script created
#   ./probe_bwrap.sh  is codex's OWN sandbox usable inside a container? (no model spend)
#
# The model key is never read here.  The caller puts it in DS_KEY for one
# command and it is handed to the container with `docker exec -e DS_KEY` (the
# no-value form copies it from the calling shell's environment), so it never
# enters argv, a config file, or the run directory:
#
#   DS_KEY=$(awk -F: '/^deepseek:/{sub(/^deepseek:[ ]*/,""); print; exit}' ~/gptapi.md) \
#     ./run.sh call
#
# Names created: a0ec-* containers and networks only.  Nothing pre-existing is
# touched; `verify` re-checks that explicitly.
# =============================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
RUN_DIR="${A0EC_RUN_DIR:-/tmp/a0ec}"
EVID="$HERE/evidence"
export A0EC_RUN_DIR="$RUN_DIR"

COMPOSE=(docker compose -f "$HERE/compose.yaml")
C2_CTR=a0ec-cli-c2
PG_CTR=adapdc-catalog-postgres-1
CANARY_VISIBLE="a0ec-canary-visible.txt"
CANARY_HOST_ONLY="a0ec-canary-host-only.txt"
CANARY_BODY="a0ec canary -- visible means the visibility control works"
PSFMT='{{.Names}}\t{{.Image}}\t{{.Status}}'

mkdir -p "$EVID"

say() { printf '%s %s\n' "$(date -Is)" "$*"; }
log() { say "$*" | tee -a "$EVID/run.log"; }

# The pre-existing containers, as a fingerprint that can be diffed later.
fingerprint_other_containers() {
  docker ps -a --format "$PSFMT" | grep -v '^a0ec-' | sort || true
}

# ---------------------------------------------------------------------------
phase_env() {
  {
    echo "== host / docker / image inventory ($(date -Is))"
    docker version --format 'docker server {{.Server.Version}}'
    docker compose version
    uname -srmo
    echo
    echo "== images already present locally (this script pulls nothing)"
    docker images --format '{{.Repository}}:{{.Tag}}  {{.Size}}  {{.ID}}'
    echo
    echo "== the image this mechanism uses"
    python3 -c "
import subprocess
size = int(subprocess.run(['docker','image','inspect','python:3.12-slim',
    '--format','{{.Size}}'], capture_output=True, text=True).stdout.strip())
print('python:3.12-slim uncompressed=%d bytes (%.1f MiB)' % (size, size/1048576))"
    echo
    echo "== what the CLI binary needs that the image does not carry"
    echo "-- host ldd (the binary the campaign runs, as installed):"
    ldd /usr/bin/codex | sed 's/^/   /'
    echo "-- container ldd for the same bytes, bind-mounted read-only:"
    docker run --rm -v /usr/bin/codex:/usr/local/bin/codex:ro python:3.12-slim \
      sh -c 'ldd /usr/local/bin/codex; echo "   glibc: $(ldd --version | head -1)"'
    echo "-- the authoritative DT_NEEDED list (direct requirements, not the closure):"
    readelf -d /usr/bin/codex 2>/dev/null | grep NEEDED | sed 's/^/   /' || true
    echo "-- with the ONE missing object bind-mounted, does the CLI start?"
    docker run --rm -v /usr/bin/codex:/usr/local/bin/codex:ro \
      -v /usr/lib/libonig.so.5.5.0:/usr/lib/x86_64-linux-gnu/libonig.so.5:ro \
      python:3.12-slim sh -c 'codex --version; echo "   exit=$?"'
    echo
    echo "== alternatives considered and why they are NOT used"
    echo "   alpine:3.21 (12.2MB): musl -- cannot load a glibc-linked ELF without"
    echo "     gcompat, and gcompat would be a new package install.  Rejected."
    echo "   building an image with the CLI installed: needs a network pull and"
    echo "     would fork the CLI version away from the campaign's /usr/bin/codex."
    echo "     Rejected: a bind mount keeps the exact bytes under test."
  } > "$EVID/00_environment.txt" 2>&1
  say "wrote $EVID/00_environment.txt"
}

# ---------------------------------------------------------------------------
phase_up() {
  log "== up: run directory $RUN_DIR"
  mkdir -p "$RUN_DIR/ws" "$RUN_DIR/ws-c2" "$RUN_DIR/codex-home/c1" \
           "$RUN_DIR/codex-home/c2" "$RUN_DIR/meter" "$RUN_DIR/run" "$RUN_DIR/host-only"
  printf '%s\n' "$CANARY_BODY" > "$RUN_DIR/ws/$CANARY_VISIBLE"
  printf '%s\n' "$CANARY_BODY" > "$RUN_DIR/ws-c2/$CANARY_VISIBLE"
  # The control that must NOT be visible: same body, a path that is not mounted.
  printf '%s\n' "$CANARY_BODY" > "$RUN_DIR/host-only/$CANARY_HOST_ONLY"
  cp "$HERE/codex/C1.config.toml" "$RUN_DIR/codex-home/c1/config.toml"
  cp "$HERE/codex/C2.config.toml" "$RUN_DIR/codex-home/c2/config.toml"

  cat > "$RUN_DIR/ws/README.txt" <<'EOF'
Mechanism C session workspace (variant C1).  This directory is the session's
only read-write mount.  The repository, its git objects, the answer stores and
the provider key are not mounted anywhere in this container.
EOF
  cp "$RUN_DIR/ws/README.txt" "$RUN_DIR/ws-c2/README.txt"

  # ---- before-fingerprint, so "untouched" is measured rather than asserted
  fingerprint_other_containers > "$RUN_DIR/before.docker.txt"
  docker inspect "$PG_CTR" --format \
    'id={{.Id}} running={{.State.Running}} started={{.State.StartedAt}} restarts={{.RestartCount}}' \
    > "$RUN_DIR/before.pg.txt" 2>&1 || true
  {
    echo "== non-a0ec containers before"; cat "$RUN_DIR/before.docker.txt"
    echo "== $PG_CTR before"; cat "$RUN_DIR/before.pg.txt"
  } >> "$EVID/run.log"

  # ---- the topology
  local t0 t1 t2
  t0=$(date +%s.%N)
  "${COMPOSE[@]}" up -d 2>&1 | tee -a "$EVID/run.log"
  t1=$(date +%s.%N)

  # ---- variant C2: no network at all, one bind-mounted unix socket
  docker rm -f "$C2_CTR" >/dev/null 2>&1 || true
  docker run -d --name "$C2_CTR" --network none --user 1000:1000 --hostname a0ec-cli-c2 \
    -v "$RUN_DIR/ws-c2:/workspace" \
    -v "$RUN_DIR/codex-home/c2:/codex-home" \
    -v "$RUN_DIR/run:/run/a0ec" \
    -v /usr/bin/codex:/usr/local/bin/codex:ro \
    -v /usr/lib/libonig.so.5.5.0:/usr/lib/x86_64-linux-gnu/libonig.so.5:ro \
    -v "$HERE/probe_inside.py:/opt/a0ec/probe_inside.py:ro" \
    -v "$HERE/sock_forward.py:/opt/a0ec/sock_forward.py:ro" \
    -e HOME=/codex-home -e CODEX_HOME=/codex-home \
    -e A0EC_VARIANT=C2 -e A0EC_METER_URL=http://127.0.0.1:8802 \
    -e A0EC_METER_HOST=127.0.0.1:8802 -e A0EC_SCAN_SUBNET= -e A0EC_WORKSPACE=/workspace \
    --cap-drop ALL --security-opt no-new-privileges \
    python:3.12-slim sleep infinity >> "$EVID/run.log" 2>&1

  # ---- variant C2's host-side relay (UnixRelay from a0.a1.topology, reused)
  pkill -f 'sock_relay.py --sock' >/dev/null 2>&1 || true
  rm -f "$RUN_DIR/run/c2.sock" "$RUN_DIR/run/relay.ready"
  nohup python3 "$HERE/sock_relay.py" --sock "$RUN_DIR/run/c2.sock" \
    --target 127.0.0.1:8802 --ready-file "$RUN_DIR/run/relay.ready" \
    >> "$EVID/relay.log" 2>&1 &
  echo $! > "$RUN_DIR/run/relay.pid"
  for _ in $(seq 1 75); do
    if [ -S "$RUN_DIR/run/c2.sock" ]; then break; fi
    sleep 0.2
  done
  [ -S "$RUN_DIR/run/c2.sock" ] || { echo "relay socket never appeared" >&2; return 1; }

  # ---- C2's in-container forwarder: 127.0.0.1:8802 -> the mounted socket
  docker exec -d "$C2_CTR" python3 /opt/a0ec/sock_forward.py --port 8802 \
    --sock /run/a0ec/c2.sock --ready-file /tmp/fwd.ready
  for _ in $(seq 1 75); do
    if docker exec "$C2_CTR" test -f /tmp/fwd.ready >/dev/null 2>&1; then break; fi
    sleep 0.2
  done

  # ---- time to a listening metered endpoint
  for _ in $(seq 1 300); do
    if [ -f "$RUN_DIR/meter/ready" ]; then break; fi
    sleep 0.2
  done
  t2=$(date +%s.%N)
  [ -f "$RUN_DIR/meter/ready" ] || { echo "meter never became ready" >&2; return 1; }

  local t3
  t3=$(date +%s.%N)
  docker exec a0ec-cli codex --version >/dev/null 2>&1
  local t4
  t4=$(date +%s.%N)

  {
    echo "compose_up_seconds=$(python3 -c "print(f'{$t1-$t0:.2f}')")"
    echo "compose_up_to_meter_ready_seconds=$(python3 -c "print(f'{$t2-$t0:.2f}')")"
    echo "first_docker_exec_codex_version_seconds=$(python3 -c "print(f'{$t4-$t3:.2f}')")"
    echo "image_pull_seconds=0.00  # python:3.12-slim was already local"
  } | tee "$EVID/timings.txt" | tee -a "$EVID/run.log"

  docker ps --filter 'name=a0ec-' \
    --format '{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | tee -a "$EVID/run.log"
  docker network inspect a0ec-internal \
    --format 'a0ec-internal internal={{.Internal}} subnet={{range .IPAM.Config}}{{.Subnet}}{{end}}' \
    | tee -a "$EVID/run.log"
  log "== up complete"
}

# ---------------------------------------------------------------------------
phase_probe() {
  log "== probe (inside each agent container)"
  docker exec a0ec-cli python3 /opt/a0ec/probe_inside.py --out /workspace/probe_C1.json \
    > "$EVID/20_probe_C1.summary.txt" 2>&1 || log "probe C1 returned nonzero"
  docker exec "$C2_CTR" python3 /opt/a0ec/probe_inside.py --out /workspace/probe_C2.json \
    > "$EVID/21_probe_C2.summary.txt" 2>&1 || log "probe C2 returned nonzero"
  cp "$RUN_DIR/ws/probe_C1.json" "$EVID/20_probe_C1.json"
  cp "$RUN_DIR/ws-c2/probe_C2.json" "$EVID/21_probe_C2.json"
  for pair in "20:C1" "21:C2"; do
    n="${pair%%:*}"; v="${pair##*:}"
    echo "--- variant $v ---" >> "$EVID/run.log"
    cat "$EVID/${n}_probe_${v}.summary.txt" >> "$EVID/run.log" 2>/dev/null || true
  done
  log "== probe complete"
}

# ---------------------------------------------------------------------------
phase_call() {
  if [ -z "${DS_KEY:-}" ]; then
    echo "DS_KEY is unset; refusing to make a call." >&2
    echo "  DS_KEY=\$(awk -F: '/^deepseek:/{sub(/^deepseek:[ ]*/,\"\"); print; exit}' ~/gptapi.md) ./run.sh call" >&2
    return 2
  fi
  local t0 t1 rc

  log "== metered call, variant C1 (posture: danger-full-access, the T1 coding_agent posture)"
  t0=$(date +%s.%N)
  set +e
  docker exec -e DS_KEY -w /workspace a0ec-cli \
    codex exec --skip-git-repo-check --sandbox danger-full-access \
    "Reply with exactly: A0EC-C1-OK" > "$EVID/30_call_C1.txt" 2>&1
  rc=$?
  set -e
  t1=$(date +%s.%N)
  echo "variant C1 exit=$rc" >> "$EVID/30_call_C1.txt"
  echo "call_C1_seconds=$(python3 -c "print(f'{$t1-$t0:.2f}')")" >> "$EVID/timings.txt"
  tail -14 "$EVID/30_call_C1.txt" | tee -a "$EVID/run.log"

  log "== metered call, variant C2 (same posture; no network namespace uplink at all)"
  t0=$(date +%s.%N)
  set +e
  docker exec -e DS_KEY -w /workspace "$C2_CTR" \
    codex exec --skip-git-repo-check --sandbox danger-full-access \
    "Reply with exactly: A0EC-C2-OK" > "$EVID/31_call_C2.txt" 2>&1
  rc=$?
  set -e
  t1=$(date +%s.%N)
  echo "variant C2 exit=$rc" >> "$EVID/31_call_C2.txt"
  echo "call_C2_seconds=$(python3 -c "print(f'{$t1-$t0:.2f}')")" >> "$EVID/timings.txt"
  tail -14 "$EVID/31_call_C2.txt" | tee -a "$EVID/run.log"
  log "== calls complete"
}

# ---------------------------------------------------------------------------
phase_tool() {
  # The session shape the campaign actually needs: the agent edits the workspace
  # and runs what it wrote.  Verified from the host filesystem, not from the
  # model's claim about what it did.
  if [ -z "${DS_KEY:-}" ]; then
    echo "DS_KEY is unset; refusing to make a call." >&2
    return 2
  fi
  log "== tool-loop call, variant C1: create a file in the workspace and execute it"
  set +e
  docker exec -e DS_KEY -w /workspace a0ec-cli \
    codex exec --skip-git-repo-check --sandbox danger-full-access \
    "Create a file named hello_a0ec.py in the current directory whose only line is print('A0EC_TOOL_OK'), then run it with python3 and tell me its stdout." \
    > "$EVID/32_call_C1_toolloop.txt" 2>&1
  echo "tool-loop exit=$?" >> "$EVID/32_call_C1_toolloop.txt"
  set -e
  tail -18 "$EVID/32_call_C1_toolloop.txt" | tee -a "$EVID/run.log"
  echo "== verified from the HOST, not from the transcript:"
  ls -l "$RUN_DIR/ws/" | tee -a "$EVID/run.log"
  if [ -f "$RUN_DIR/ws/hello_a0ec.py" ]; then
    echo "  hello_a0ec.py content: $(cat "$RUN_DIR/ws/hello_a0ec.py")"
    echo "  host-side execution:   $(python3 "$RUN_DIR/ws/hello_a0ec.py")"
  else
    echo "  hello_a0ec.py NOT created"
  fi
  log "== tool-loop complete"
}

# ---------------------------------------------------------------------------
phase_verify() {
  log "== verify (host side)"
  cp "$RUN_DIR/meter/ledger.jsonl" "$EVID/40_ledger.jsonl" 2>/dev/null || true
  cp "$RUN_DIR/meter/meter.aid.json" "$EVID/42_meter_aid.json" 2>/dev/null || true
  {
    echo "== the ledger, re-derived by a separate program (a0/meter/verify_ledger.py)"
    python3 "$REPO/a0/meter/verify_ledger.py" "$EVID/40_ledger.jsonl" || true
    echo
    echo "== every row, and CEq summed from the rows themselves"
    python3 - "$EVID/40_ledger.jsonl" <<'PY'
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1]) if line.strip()]
total = 0
for row in rows:
    print("  %-12s %-20s model=%-15s unmetered=%-5s ceq=%s"
          % (row["campaign_id"], row["arm_id"], row.get("model_requested"),
             row["unmetered"], row["ceq"]))
    if row.get("ceq"):
        total += row["ceq"]
print("  TOTAL CEq = %d over %d rows" % (total, len(rows)))
PY
    echo
    echo "== non-a0ec containers, after (diff against the before fingerprint)"
    fingerprint_other_containers > "$RUN_DIR/after.docker.txt"
    if diff "$RUN_DIR/before.docker.txt" "$RUN_DIR/after.docker.txt" >/dev/null; then
      echo "  IDENTICAL to the before fingerprint"
    else
      echo "  DIFFERS:"; diff "$RUN_DIR/before.docker.txt" "$RUN_DIR/after.docker.txt" || true
    fi
    cat "$RUN_DIR/before.docker.txt" | sed 's/^/    /'
    echo
    echo "== $PG_CTR, after"
    docker inspect "$PG_CTR" --format \
      'id={{.Id}} running={{.State.Running}} started={{.State.StartedAt}} restarts={{.RestartCount}}'
    echo "  before: $(cat "$RUN_DIR/before.pg.txt")"
    echo
    echo "== startup cost, measured"
    cat "$EVID/timings.txt"
    echo
    echo "== image sizes"
    docker image inspect python:3.12-slim --format 'python:3.12-slim {{.Size}} bytes (uncompressed)'
    echo
    echo "== the harness-supplied state, and what the container has of its own"
    ls -la "$RUN_DIR/codex-home/c1" "$RUN_DIR/codex-home/c2"
    echo "  auth:  none -- the CLI authenticates with DS_KEY, injected per exec"
    echo "  the host's ~/.codex was NOT mounted: no session, plugin or config reused"
    echo
    echo "== docker socket availability inside the lane (must be absent)"
    docker exec a0ec-cli sh -c 'ls -la /var/run/docker.sock 2>&1; true'
    docker exec "$C2_CTR" sh -c 'ls -la /var/run/docker.sock 2>&1; true'
  } > "$EVID/50_verify_host.txt" 2>&1
  cat "$EVID/50_verify_host.txt" | tee -a "$EVID/run.log"
  log "== verify complete"
}

# ---------------------------------------------------------------------------
phase_down() {
  log "== down"
  if [ -f "$RUN_DIR/run/relay.pid" ]; then kill "$(cat "$RUN_DIR/run/relay.pid")" 2>/dev/null || true; fi
  pkill -f 'sock_relay.py --sock' >/dev/null 2>&1 || true
  docker rm -f "$C2_CTR" >/dev/null 2>&1 || true
  "${COMPOSE[@]}" down -v 2>&1 | tee -a "$EVID/run.log"
  docker network rm a0ec-egress >/dev/null 2>&1 || true
  {
    echo "== after teardown: only the pre-existing containers/networks should remain"
    docker ps -a --format "$PSFMT"
    docker network ls --format '{{.Name}}  {{.Driver}}'
  } | tee "$EVID/60_down.txt" | tee -a "$EVID/run.log"
}

# ---------------------------------------------------------------------------
case "${1:-all}" in
  env)    phase_env ;;
  up)     phase_up ;;
  probe)  phase_probe ;;
  call)   phase_call ;;
  tool)   phase_tool ;;
  verify) phase_verify ;;
  down)   phase_down ;;
  all)    phase_env; phase_up; phase_probe; phase_call; phase_tool; phase_verify ;;
  *)      echo "usage: $0 {env|up|probe|call|tool|verify|down|all}" >&2; exit 2 ;;
esac
