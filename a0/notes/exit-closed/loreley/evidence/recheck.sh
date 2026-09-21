#!/usr/bin/env bash
# Re-runnable evidence for a0/notes/exit-closed/loreley. Read-only; no model calls, no installs.
# Usage: bash recheck.sh > recheck.out 2>&1
set -u
LORELEY=/home/ebt/rsi-dev/a0/tasks/circle-packing/upstream/loreley
echo "## date"; date -Is
echo
echo "## pinned checkouts (expect 4c375920)"
git -C "$LORELEY" log -1 --format='%H %d'
git -C /home/ebt/rsi-dev/a0/runtimes/loreley/checkout log -1 --format='%H'
echo
echo "## the two copies are identical (modulo __pycache__)"
DIFF_OUT=$(diff -rq "$LORELEY/loreley" /home/ebt/rsi-dev/a0/runtimes/loreley/checkout/loreley | grep -v __pycache__)
if [ -z "$DIFF_OUT" ]; then echo "no differences"; else echo "$DIFF_OUT"; fi
echo
echo "## backend package contents"
ls -1 "$LORELEY/loreley/core/worker/agent/backends/"
echo
echo "## binaries on this host"
python3 - <<'PY'
import shutil
for b in ("kilo", "codex", "claude", "cursor-agent"):
    print(f"{b:14s} -> {shutil.which(b)}")
PY
echo
echo "## default backend refs (Settings)"
grep -n "worker_planning_backend\|worker_coding_backend\|worker_seed_portfolio_backend" "$LORELEY/loreley/config.py" | head -6
echo
echo "## open-source status, upstream metadata (fetched, not from memory)"
for spec in "repos/openai/codex" "repos/anthropics/claude-code" "repos/Kilo-Org/kilocode"; do
  printf '%-28s ' "$spec"
  curl -s --noproxy '*' "https://api.github.com/$spec" \
    | python3 -c "import sys,json;d=json.load(sys.stdin);print((d.get('license') or {}).get('spdx_id'), '|', d.get('description'))"
done
for p in "@openai/codex" "@anthropic-ai/claude-code" "@kilocode/cli"; do
  printf 'npm %-26s ' "$p"
  curl -s --noproxy '*' "https://registry.npmjs.org/${p//\//%2f}" \
    | python3 -c "import sys,json;d=json.load(sys.stdin);print('latest', (d.get('dist-tags') or {}).get('latest'), '| license', d.get('license'))"
done
echo
echo "## the npm package named 'cursor-agent' is NOT Cursor's CLI"
curl -s --noproxy '*' https://registry.npmjs.org/cursor-agent \
  | python3 -c "import sys,json;d=json.load(sys.stdin);v=(d.get('versions') or {}).get((d.get('dist-tags') or {}).get('latest')) or {};print(v.get('repository'), '|', d.get('description'))"
echo
echo "## kilocode LICENSE grant (MIT, and it is an opencode fork)"
curl -s --noproxy '*' https://api.github.com/repos/Kilo-Org/kilocode/license \
  | python3 -c "
import sys,json,base64
d=json.load(sys.stdin); c=d.get('content') or ''
print('spdx', (d.get('license') or {}).get('spdx_id'))
print(base64.b64decode(c).decode()[:180])"
echo
echo "## Apache/MIT notices embedded in the installed codex binary"
strings -n 6 /usr/bin/codex 2>/dev/null | grep -m2 -i "Licensed under the Apache License" || echo "(none found)"
echo
echo "## codex knows an OSS/local provider (so the CLI is not the closed part)"
strings -n 6 /usr/bin/codex 2>/dev/null | grep -o -m1 "oss provider must have a base_url" || echo "(not found)"
strings -n 6 /usr/bin/codex 2>/dev/null | grep -o -m1 "No running Ollama server detected" || echo "(not found)"
echo
echo "## Loreley has no claude backend at all"
grep -rin "claude" "$LORELEY/loreley/" | head -5 || true
echo "(lines above, if any, are the only 'claude' references in the package)"
echo
echo "## only the coding lane enforces a worktree diff (post_check)"
grep -n "post_check=\|retryable_exceptions=(" "$LORELEY/loreley/core/worker/coding.py" "$LORELEY/loreley/core/worker/planning.py" "$LORELEY/loreley/core/seed_portfolio.py"
echo
echo "## the CODEX_HOME clobbering and its escape hatch"
grep -n "if \"CODEX_HOME\" in\|env\[\"CODEX_HOME\"\]\|trust_level" "$LORELEY/loreley/core/worker/agent/backends/codex_cli.py"
grep -n "CODEX_HOME" /home/ebt/rsi-dev/a0/runtimes/loreley/VERIFICATION.md
