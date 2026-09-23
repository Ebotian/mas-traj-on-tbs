#!/usr/bin/env bash
# =============================================================================
# Is codex's OWN sandbox usable inside the container?  Measured, not asserted.
#
# This matters because T1's mode config gives two roles `sandbox: read-only`
# (feedback_generator, evaluation_maintainer) and one `danger-full-access`
# (coding_agent).  codex 0.155.1 implements read-only/workspace-write with
# bubblewrap (linux-sandbox/src/launcher.rs), so the question "does the CLI run
# in this container" is really "does bwrap run in this container".
#
# Every line below is one `docker run`; nothing here touches a pre-existing
# container.  Writes ./evidence/28_bwrap.txt.
# =============================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/evidence/28_bwrap.txt"
IMAGE=python:3.12-slim
BWRAP=/usr/bin/bwrap:/usr/bin/bwrap:ro

{
  echo "== bwrap inside the container, per posture ($(date -Is))"
  echo
  echo "-- the host's bwrap (what Mechanism A inherits, and what the container image lacks)"
  echo "   $(command -v bwrap)  $(bwrap --version)  (host; package 'bubblewrap')"
  ldd /usr/bin/bwrap | sed 's/^/   /'
  echo

  run() {  # run <label> <docker-run-flags...> -- <bwrap args...>
    local label="$1"; shift
    echo "--- $label"
    if docker run --rm "$@" $IMAGE sh -c \
        'command -v bwrap >/dev/null || { echo "   bwrap: ABSENT from the image"; exit 3; }
         bwrap --ro-bind / / --dev /dev --unshare-all --die-with-parent /bin/echo INSIDE_BWRAP_OK
         echo "   exit=$?"' 2>&1 | sed 's/^/   /'; then :; else echo "   (docker run exited nonzero)"; fi
    echo
  }

  run "A. container default caps (the shape run.sh does NOT use), bwrap mounted read-only" \
      -v "$BWRAP"
  run "B. cap_drop ALL + no-new-privileges (the shape run.sh uses), bwrap mounted read-only" \
      --cap-drop ALL --security-opt no-new-privileges -v "$BWRAP"
  run "C. cap_drop ALL + seccomp=unconfined" \
      --cap-drop ALL --security-opt no-new-privileges --security-opt seccomp=unconfined -v "$BWRAP"
  run "D. cap_drop ALL + seccomp=unconfined, bwrap without --unshare-all" \
      --cap-drop ALL --security-opt seccomp=unconfined -v "$BWRAP"
  run "E. --cap-add SYS_ADMIN (default seccomp)" \
      --cap-add SYS_ADMIN -v "$BWRAP"
  run "F. --cap-add SYS_ADMIN + seccomp=unconfined   <-- the first posture where it works" \
      --cap-add SYS_ADMIN --security-opt seccomp=unconfined -v "$BWRAP"
  run "G. POSITIVE CONTROL: --privileged  (proves the failure above is the container, not bwrap)" \
      --privileged -v "$BWRAP"

  echo "--- H. does posture F actually recover codex's own read-only semantics?"
  echo "      (model-free: 'codex sandbox' runs a command, no model call)"
  docker run --rm --cap-add SYS_ADMIN --security-opt seccomp=unconfined \
      -v "$BWRAP" -v /usr/bin/codex:/usr/local/bin/codex:ro \
      -v /usr/lib/libonig.so.5.5.0:/usr/lib/x86_64-linux-gnu/libonig.so.5:ro \
      -e HOME=/tmp -e CODEX_HOME=/tmp -w /tmp $IMAGE \
      sh -c 'codex sandbox -c sandbox_mode="\"read-only\"" -- bash -c "python3 -c \"import socket;socket.socket()\"" 2>&1 | tail -2' \
      2>&1 | sed 's/^/      /'
  echo "      (a PermissionError here means read-only applied; a successful socket() would not)"
  echo

  echo "== the same question under a plain user namespace, i.e. the shape Mechanism A"
  echo "== (a0/a1/epistemic-ns) launches with: 'unshare -rmpf --mount-proc'"
  unshare -rmpf --mount-proc sh -c \
    'echo "   uid inside: $(id -u)"; bwrap --ro-bind / / --dev /dev --unshare-all --die-with-parent /bin/echo "   INSIDE_BWRAP_OK (exit=$?)"' 2>&1
  echo
  echo "== and codex's read-only posture there, model-free (codex sandbox runs no model call)"
  unshare -rmpf --mount-proc sh -c \
    'codex sandbox -c sandbox_mode="\"read-only\"" -- bash -c "python3 -c \"import socket;socket.socket()\"" 2>&1 | tail -1 | sed "s/^/   /"' 2>&1
  echo "   (PermissionError = the sandbox applied; on the host the same command is measured"
  echo "    in a0/notes/exit-closed/codex-0.155.1/evidence/18_sandbox_retest.txt)"
} > "$OUT" 2>&1

cat "$OUT"
