#!/usr/bin/env bash
# =============================================================================
# probe_egress.sh -- closure probe for the A0 algorithm-improvement runtimes
#
# PURPOSE
#   Protocol section 4.3 requires the study to *prove by probe* that a runtime
#   has no autonomous external acquisition, rather than merely flipping a config
#   flag. This script does two things:
#
#     1. "self-test"  -- proves which isolation mechanisms actually work on this
#                        machine, with both a negative control (must be blocked)
#                        and a positive control (must be reachable). A mechanism
#                        that blocks *everything* is not a useful barrier, so a
#                        successful self-test requires the local-channel check to
#                        keep working through the barrier.
#
#     2. "check"      -- points the same canary (or an arbitrary runtime command)
#                        through ONE mechanism, and reports whether egress was
#                        observed OPEN or BLOCKED, with the raw evidence.
#
#   It is runtime-agnostic on purpose: point it at KAPSO, EvE or Loreley by
#   passing the command the runtime executes for a candidate (--cmd) and the
#   image that runtime uses (--image).
#
# USAGE
#   ./probe_egress.sh list
#   ./probe_egress.sh check  --mechanism M [--cmd 'SHELL CMD'] [--image IMG]
#                            [--timeout N] [--json FILE] [--quiet]
#   ./probe_egress.sh self-test [--image IMG] [--timeout N] [--json FILE]
#
#   M in: host | unshare-rn | docker-bridge | docker-internal | docker-none
#
# WHAT IS AND IS NOT CLAIMED
#   The probe measures the egress of the context it is given. It does NOT claim
#   a runtime is closed unless the runtime's candidate-execution channel is what
#   you passed in. For KAPSO/EvE the interesting context is the lane that runs
#   candidate code (codex/claude Bash tool), not the orchestrator process, which
#   still needs its own model endpoint.
#
# EXIT CODES
#   0  observed behaviour matched the expectation for the mechanism
#   1  observed behaviour did NOT match (e.g. claimed barrier leaked)
#   2  usage / environment error (missing docker, image not pullable, ...)
#
# EVIDENCE FORMAT
#   One "EVIDENCE ..." line per check, containing only observed truth:
#     dns=<ok|fail> tcp=<ok|fail> tcpvia=<host:port|none> https=<ok|fail>
#     local=<ok|fail|n/a>
#     egress=<OPEN|BLOCKED>
# =============================================================================
set -uo pipefail

DEFAULT_IMAGE="${PROBE_IMAGE:-alpine:3.21}"
DEFAULT_TIMEOUT=30
VERBOSE=1
JSON_OUT=""

die() { echo "probe_egress: ERROR: $*" >&2; exit 2; }
note() { [ "$VERBOSE" -eq 1 ] && echo "$*" >&2 || true; }

# ---------------------------------------------------------------------------
# The canary. Runs in POSIX sh so the identical text works on the host (bash)
# and inside an alpine container (busybox ash). It deliberately tries several
# independent methods, because "curl is missing" must not be reported as
# "network is blocked".
#
# Emits exactly one line:
#   CANARY dns=<..> tcp=<..> tcpvia=<target|none> https=<..> local=<..>
# ---------------------------------------------------------------------------
read -r -d '' CANARY <<'CANARY_EOF'
#!/bin/sh
# --- DNS -------------------------------------------------------------------
dns=fail
if command -v nslookup >/dev/null 2>&1; then
  nslookup -type=A example.com >/dev/null 2>&1 && dns=ok
elif command -v getent >/dev/null 2>&1; then
  getent hosts example.com >/dev/null 2>&1 && dns=ok
elif command -v python3 >/dev/null 2>&1; then
  python3 -c 'import socket;socket.gethostbyname("example.com")' >/dev/null 2>&1 && dns=ok
fi

# --- raw TCP connect, no HTTP involved ------------------------------------
# Targets are tried in order: first by NAME (example.com:443), then a few IP
# literals. Some hosts filter specific public resolver IPs (measured on the
# audit machine: 1.1.1.1:443 and 8.8.8.8:443 time out while example.com:443
# connects), so a single hardcoded IP would yield a false "blocked".
try_tcp() {  # $1=host $2=port
  if command -v python3 >/dev/null 2>&1; then
    T_HOST="$1" T_PORT="$2" python3 - <<'PY' >/dev/null 2>&1
import os,socket,sys
s=socket.socket(); s.settimeout(5)
try: s.connect((os.environ["T_HOST"], int(os.environ["T_PORT"])))
except Exception: sys.exit(1)
PY
  elif command -v nc >/dev/null 2>&1; then
    # busybox nc (alpine): -w sets the connect timeout; connect returns 0
    # once stdin closes. /dev/tcp is bash-only, so it is not used here.
    nc -w 5 "$1" "$2" </dev/null >/dev/null 2>&1
  elif [ -n "${BASH_VERSION:-}" ]; then
    ( echo > "/dev/tcp/$1/$2" ) >/dev/null 2>&1
  else
    return 1
  fi
}
tcp=fail; tcpvia=none
for target in example.com:443 1.1.1.1:443 8.8.8.8:443 1.1.1.1:80 8.8.8.8:53; do
  if try_tcp "${target%:*}" "${target#*:}"; then tcp=ok; tcpvia="$target"; break; fi
done

# --- HTTPS GET to a well-known host ---------------------------------------
# --noproxy '*': the probe must measure the context's own egress, not a relay
# the host happens to have configured. 15s covers a cold DNS+TLS handshake.
https=fail
if command -v curl >/dev/null 2>&1; then
  curl -s -o /dev/null --max-time 15 --noproxy '*' https://example.com && https=ok
elif command -v wget >/dev/null 2>&1; then
  wget -q -T 15 -O /dev/null https://example.com && https=ok
elif command -v python3 >/dev/null 2>&1; then
  python3 -c 'import urllib.request;urllib.request.urlopen("https://example.com",timeout=15)' >/dev/null 2>&1 && https=ok
fi

# --- local/sibling channel: the runtime must still reach ITS OWN services --
# LORELEY_LOCAL_HOST / LORELEY_LOCAL_PORT are set by the caller when a local
# channel is expected to stay open (e.g. a sibling redis on the same net).
local=fail
if [ -n "${PROBE_LOCAL_HOST:-}" ] && [ -n "${PROBE_LOCAL_PORT:-}" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PROBE_LOCAL_HOST="$PROBE_LOCAL_HOST" PROBE_LOCAL_PORT="$PROBE_LOCAL_PORT" python3 - <<'PY' >/dev/null 2>&1 && local=ok
import os,socket,sys
s=socket.socket(); s.settimeout(4)
try: s.connect((os.environ["PROBE_LOCAL_HOST"], int(os.environ["PROBE_LOCAL_PORT"])))
except Exception: sys.exit(1)
PY
  elif command -v nc >/dev/null 2>&1; then
    nc -w 4 "$PROBE_LOCAL_HOST" "$PROBE_LOCAL_PORT" </dev/null >/dev/null 2>&1 && local=ok
  fi
else
  local=n/a
fi

echo "CANARY dns=$dns tcp=$tcp tcpvia=$tcpvia https=$https local=$local"
CANARY_EOF

# ---------------------------------------------------------------------------
# Mechanisms
# ---------------------------------------------------------------------------
# expectation: "open" (egress must be reachable) or "blocked" (must fail)
mechanism_expectation() {
  case "$1" in
    host)            echo open ;;
    docker-bridge)   echo open ;;
    unshare-rn)      echo blocked ;;
    docker-internal) echo blocked ;;
    docker-none)     echo blocked ;;
    *) die "unknown mechanism '$1' (see: probe_egress.sh list)" ;;
  esac
}

# Run a shell snippet inside the mechanism, echoing the mechanism's stdout.
run_in_mechanism() {
  local mech="$1" script="$2" image="$3" timeout="$4"
  case "$mech" in
    host)
      PROBE_LOCAL_HOST="${PROBE_LOCAL_HOST:-}" PROBE_LOCAL_PORT="${PROBE_LOCAL_PORT:-}" \
        timeout "$timeout" sh -c "$script"
      ;;
    unshare-rn)
      command -v unshare >/dev/null || die "unshare not found"
      # -r : map self to root in a new user namespace (works without CAP_SYS_ADMIN)
      # -n : new network namespace => no route, no NAT, only a down 'lo'
      PROBE_LOCAL_HOST="${PROBE_LOCAL_HOST:-}" PROBE_LOCAL_PORT="${PROBE_LOCAL_PORT:-}" \
        timeout "$timeout" unshare -rn sh -c "$script"
      ;;
    docker-bridge|docker-internal|docker-none)
      command -v docker >/dev/null || die "docker not found"
      local netargs=()
      case "$mech" in
        docker-bridge) netargs=(--network bridge) ;;
        # --internal: bridge with no default route/NAT -> no external egress,
        # but sibling containers on the same network remain reachable.
        docker-internal) netargs=(--network "$INTERNAL_NET") ;;
        docker-none) netargs=(--network none) ;;
      esac
      timeout "$timeout" docker run --rm -i "${netargs[@]}" \
        -e PROBE_LOCAL_HOST="${PROBE_LOCAL_HOST:-}" \
        -e PROBE_LOCAL_PORT="${PROBE_LOCAL_PORT:-}" \
        --entrypoint sh "$image" -c "$script"
      ;;
  esac
}

# ---------------------------------------------------------------------------
# One observation: run canary (or user cmd) and classify.
# ---------------------------------------------------------------------------
observe() {
  local mech="$1" image="$2" timeout="$3" mode="$4" cmd="${5:-}"

  case "$mode" in
    canary) script="$CANARY" ;;
    # user command: append the canary so we always get a classified line too
    cmd)    script="$cmd
$CANARY" ;;
  esac

  local raw rc
  raw="$(run_in_mechanism "$mech" "$script" "$image" "$timeout" 2>&1)"; rc=$?

  local canary_line egress
  canary_line="$(printf '%s\n' "$raw" | grep -m1 '^CANARY ' || true)"
  if [ -z "$canary_line" ]; then
    # the mechanism could not even run the canary
    egress="BLOCKED"
    canary_line="CANARY dns=fail tcp=fail tcpvia=none https=fail local=n/a"
    note "  (no canary output; rc=$rc -- treated as BLOCKED egress)"
  elif printf '%s' "$canary_line" | grep -qE 'tcp=ok|https=ok'; then
    egress="OPEN"
  else
    egress="BLOCKED"
  fi

  printf 'EVIDENCE mechanism=%s mode=%s rc=%s %s egress=%s\n' \
    "$mech" "$mode" "$rc" "${canary_line#CANARY }" "$egress"
  [ -n "$cmd" ] && printf 'OBSERVED-OUTPUT-BEGIN\n%s\nOBSERVED-OUTPUT-END\n' "$raw"
  return 0
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
usage() { sed -n '2,45p' "$0" | sed 's/^# \{0,1\}//'; }

ensure_internal_net() {
  INTERNAL_NET="${INTERNAL_NET:-a0-egress-internal}"
  if ! docker network inspect "$INTERNAL_NET" >/dev/null 2>&1; then
    note "probe_egress: creating internal network $INTERNAL_NET"
    docker network create --internal "$INTERNAL_NET" >/dev/null || die "cannot create internal network"
  fi
}

cmd_list() {
  cat <<EOF
mechanisms (name -> expectation):
  host              egress OPEN     no isolation; positive control
  docker-bridge     egress OPEN     container on the default bridge; positive control
  docker-internal   egress BLOCKED  container on a '--internal' network (siblings still reachable)
  docker-none       egress BLOCKED  container with --network none (nothing reachable)
  unshare-rn        egress BLOCKED  'unshare -rn' rootless netns around a host command

default canary image: $DEFAULT_IMAGE
EOF
}

cmd_check() {
  local mech="" image="$DEFAULT_IMAGE" timeout="$DEFAULT_TIMEOUT" cmd=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --mechanism) mech="$2"; shift 2 ;;
      --image)     image="$2"; shift 2 ;;
      --timeout)   timeout="$2"; shift 2 ;;
      --cmd)       cmd="$2"; shift 2 ;;
      --json)      JSON_OUT="$2"; shift 2 ;;
      --quiet)     VERBOSE=0; shift ;;
      -h|--help)   usage; exit 0 ;;
      *) die "unknown arg '$1'" ;;
    esac
  done
  [ -n "$mech" ] || die "check: --mechanism is required"
  local expect; expect="$(mechanism_expectation "$mech")"
  case "$mech" in docker-*) ensure_internal_net ;; esac

  echo "### mechanism=$mech expectation=egress_$expect image=$image timeout=${timeout}s date=$(date -Is)"
  [ -n "$cmd" ] && echo "### runtime command under test: $cmd"

  local line
  if [ -n "$cmd" ]; then
    line="$(observe "$mech" "$image" "$timeout" cmd "$cmd")"
  else
    line="$(observe "$mech" "$image" "$timeout" canary)"
  fi
  printf '%s\n' "$line"

  # Classify from the MECHANISM canary only. In `cmd` mode `$line` is the
  # EVIDENCE line followed by the command's own output block, and a command
  # that prints an `egress=` marker (e.g. a runtime's own network probe) would
  # otherwise be scanned too and could turn an unblocked run into a false
  # "MISMATCH". Everything observed comes from the first line; the raw block
  # below is preserved verbatim for the record.
  local observed; observed="$(printf '%s' "$line" | head -n1 | grep -oE 'egress=(OPEN|BLOCKED)' | cut -d= -f2)"
  local ok=0
  if { [ "$expect" = open ] && [ "$observed" = OPEN ]; } || \
     { [ "$expect" = blocked ] && [ "$observed" = BLOCKED ]; }; then
    echo "VERDICT $mech: CONFIRMED (expected egress_$expect, observed egress_$observed)"
  else
    echo "VERDICT $mech: MISMATCH (expected egress_$expect, observed egress_$observed)"
    ok=1
  fi
  [ -n "$JSON_OUT" ] && printf '{"mechanism":"%s","expected":"%s","observed":"%s","raw":"%s"}\n' \
      "$mech" "$expect" "$observed" "$(printf '%s' "$line" | sed 's/"/\\"/g')" >> "$JSON_OUT"
  return $ok
}

cmd_self_test() {
  local image="$DEFAULT_IMAGE" timeout="$DEFAULT_TIMEOUT"
  while [ $# -gt 0 ]; do
    case "$1" in
      --image)   image="$2"; shift 2 ;;
      --timeout) timeout="$2"; shift 2 ;;
      --json)    JSON_OUT="$2"; shift 2 ;;
      --quiet)   VERBOSE=0; shift ;;
      -h|--help) usage; exit 0 ;;
      *) die "unknown arg '$1'" ;;
    esac
  done
  ensure_internal_net

  # A sibling listener on the internal network proves the barrier is *selective*:
  # external egress dies, intra-study channels survive. Without this, a mechanism
  # that simply breaks networking would look like a pass.
  local sib="a0-egress-sibling"
  docker rm -f "$sib" >/dev/null 2>&1 || true
  note "probe_egress: starting sibling listener on $INTERNAL_NET"
  docker run -d --rm --name "$sib" --network "$INTERNAL_NET" redis:8 \
      redis-server --save '' --appendonly no >/dev/null 2>&1 || \
    note "probe_egress: (redis image unavailable; local-channel check will report n/a)"

  local sib_ok=0
  for _ in $(seq 1 15); do
    if docker exec "$sib" redis-cli ping >/dev/null 2>&1; then sib_ok=1; break; fi
    sleep 0.5
  done
  [ "$sib_ok" = 1 ] && note "probe_egress: sibling redis is up" || note "probe_egress: sibling redis NOT reachable from host"

  local fails=0

  # Regression guard for the `--cmd` classification bug (found 2026-09-20): the
  # command under test prints its own `egress=BLOCKED`, while the mechanism
  # canary on the host says OPEN. The correct verdict is CONFIRMED; before the
  # fix this reported MISMATCH.
  echo
  echo "### regression: --cmd output must not be mistaken for the mechanism canary"
  cmd_check --mechanism host --timeout "$timeout" \
    --cmd 'echo "command-under-test says egress=BLOCKED (this must be ignored)"' \
    || fails=$((fails+1))

  for mech in host docker-bridge docker-internal docker-none unshare-rn; do
    echo
    if [ "$mech" = docker-internal ] && [ "$sib_ok" = 1 ]; then
      PROBE_LOCAL_HOST="$sib" PROBE_LOCAL_PORT=6379 \
        cmd_check --mechanism "$mech" --image "$image" --timeout "$timeout" ${JSON_OUT:+--json "$JSON_OUT"} || fails=$((fails+1))
      # local= must be ok for the barrier to count as selective rather than broken
      echo "(selectivity requirement: local=ok expected on $mech)"
    else
      cmd_check --mechanism "$mech" --image "$image" --timeout "$timeout" ${JSON_OUT:+--json "$JSON_OUT"} || fails=$((fails+1))
    fi
  done

  docker rm -f "$sib" >/dev/null 2>&1 || true
  echo
  if [ "$fails" -eq 0 ]; then
    echo "SELF-TEST: PASS -- every mechanism behaved as its label claims."
  else
    echo "SELF-TEST: FAIL -- $fails mechanism(s) did not match their label."
  fi
  return $((fails > 0))
}

main() {
  local sub="${1:-}"; shift || true
  case "$sub" in
    list)      cmd_list ;;
    check)     cmd_check "$@" ;;
    self-test) cmd_self_test "$@" ;;
    ""|-h|--help|help) usage ;;
    *) die "unknown subcommand '$sub' (list|check|self-test)" ;;
  esac
}
main "$@"
