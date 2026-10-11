#!/bin/bash
# Host-side robust fetch of the tumor-immune-interface payload (161 files,
# revision-pinned). Routes alternate on retry:
#   A = huggingface.co  /resolve/... via local proxy
#   B = hf-mirror.com   /resolve/... via local proxy
# Each file: curl with resume (-C -) + transient retries; outer loop up to 20
# attempts with --max-time cap so a hang cannot eat the whole run.
set -u
REV=7343cfce483a6efa58977d0c8494a1cefb301ccf
R_A="https://huggingface.co/datasets/harborframework/terminal-bench-science-lfs/resolve/$REV/tumor-immune-interface/input"
R_B="https://hf-mirror.com/datasets/harborframework/terminal-bench-science-lfs/resolve/$REV/tumor-immune-interface/input"
PROXY="${PROXY:-http://127.0.0.1:7890}"   # 本机本地代理；直连环境可 `export PROXY=` 置空
DEST="${DEST:-$(cd "$(dirname "$0")/.." && pwd)/build/task-restricted/environment/payload}"
MANIFEST="${MANIFEST:-$(cd "$(dirname "$0")/.." && pwd)/data/payload_manifest.tsv}"

mkdir -p "$DEST/masks"

if [ ! -s "$MANIFEST" ]; then
  echo "building manifest..."
  curl -s --max-time 40 -x "$PROXY" \
    "https://huggingface.co/api/datasets/harborframework/terminal-bench-science-lfs/tree/$REV/tumor-immune-interface/input/masks" \
    | python3 -c "import sys,json;[print('masks/'+e['path'].split('/')[-1], e.get('size',0)) for e in json.load(sys.stdin)]" > "$MANIFEST"
  printf 'clinical.csv 2005\nroi_meta.csv 2813\nsc_data.csv 179758136\n' >> "$MANIFEST"
fi
echo "manifest: $(wc -l < "$MANIFEST") files"

fetch_one() {
  local rel="$1" want="$2" out="$DEST/$1" url got i
  for i in $(seq 1 20); do
    if [ $((i % 2)) -eq 1 ]; then url="$R_A/$rel"; else url="$R_B/$rel"; fi
    curl -sS -fL --connect-timeout 15 --max-time 420 \
      --retry 2 --retry-delay 1 --retry-all-errors \
      -C - -x "$PROXY" -o "$out" "$url" || true
    got=$(stat -c%s "$out" 2>/dev/null || echo 0)
    if [ "$got" -gt "$want" ]; then rm -f "$out"; got=0; fi
    if [ "$got" = "$want" ]; then echo "[OK]    $rel ($got)"; return 0; fi
    echo "[retry $i] $rel: $got / $want"
  done
  echo "[FAIL]  $rel"
  return 1
}

FAILED=0
n=0
while read -r rel want; do
  [ -z "${rel:-}" ] && continue
  n=$((n + 1))
  fetch_one "$rel" "$want" || FAILED=1
done < "$MANIFEST"

echo "----"
echo "files listed: $n"
if [ "$FAILED" = "0" ]; then echo "ALL_OK"; else echo "SOME_FAILED"; fi
