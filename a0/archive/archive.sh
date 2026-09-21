#!/usr/bin/env bash
# Rebuild the A0 archival bundles for the audited state.
#
# Writes into the bundle store (default /home/ebt/rsi-archive, deliberately
# OUTSIDE this repository so bundles never enter git history):
#
#   bundles/<name>.bundle.zst   zstd-compressed `git bundle` of the whole repo
#   trees/<name>.tar.zst        zstd-compressed `git archive` of the pinned tree
#   meta/<name>.refs.txt        refs the bundle carries (`git bundle list-heads`)
#   SHA256SUMS                  digests of every stored artifact
#   provenance.json             copy of the tracked manifest (self-contained store)
#
# Upstream artifacts are re-fetched from their public URLs, so a third party can
# reproduce them; every pinned commit is re-checked against the recorded tree
# hash before it is archived, and the license is read from the repository's own
# LICENSE file rather than assumed.
#
# Usage: a0/archive/archive.sh [store_dir]
#   Needs egress (http_proxy/https_proxy are honoured, as for `git ls-remote`).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STORE="${1:-/home/ebt/rsi-archive}"
WORK="$(mktemp -d /tmp/a0-archive-work-XXXXXX)"
LOCAL_REPO="$(git -C "$HERE" rev-parse --show-toplevel)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$STORE/bundles" "$STORE/trees" "$STORE/meta"
: > "$WORK/manifest.tsv"

# name|url|pinned commit|pinned tree hash   (re-fetched from the network)
UPSTREAMS=(
  "kapso|https://github.com/Leeroo-AI/kapso.git|7d99b1527921d3f09ebd47a8d375d05e9fee2488|281ddc61fe8dae95aae1b738e90a81ca70c5de23"
  "loreley|https://github.com/NeapolitanIcecream/loreley.git|4c3759208e6b908f90716488ac3eec3dceaaf397|27702aab867fab41290edbb3036e0e600e3f19f6"
  "eve|https://github.com/scaling-group/eve.git|979065fd2cf1b3be9caf70596478fe27df7815ad|5d42deab4317273eb528800d34ffd69ce4964c05"
  "circle-packing|https://github.com/NeapolitanIcecream/circle-packing.git|b91c0906c9f676eb661990d881144909d99f2d72|83aff89b3bb7dc4c8724ec366f474de3515ef2dc"
)

# name|bundle-create-args|rev-to-record
LOCAL_BUNDLES=(
  "rsi-dev-a0-audited|a0-audited|a0-audited"
  "rsi-dev-head|--all|HEAD"
)

sha_of() { sha256sum "$1" | cut -d' ' -f1; }

# egress through the local proxy is occasionally dropped; git reports it as a
# TLS connect error, so retry the network steps a few times before giving up
retry() {
  local n=1 rc=0
  while [ "$n" -le 5 ]; do
    "$@" && return 0
    rc=$?
    echo "   (attempt $n failed, rc=$rc; retrying in $((n * 3))s)" >&2
    sleep $((n * 3)); n=$((n + 1))
  done
  return "$rc"
}

license_spdx() { # $1 repo  $2 commit
  local text
  text="$(git -C "$1" show "$2:LICENSE" 2>/dev/null || true)"
  if [ -z "$text" ]; then echo "NONE_FOUND"; return; fi
  if grep -qi 'MIT License' <<<"$text"; then echo "MIT"; return; fi
  if grep -qi 'Apache License' <<<"$text" && grep -qi 'Version 2.0' <<<"$text"; then echo "Apache-2.0"; return; fi
  echo "UNKNOWN"
}

# emit name kind file url commit tree
emit() { # $1 name  $2 kind  $3 dest-path  $4 raw-path  $5 url  $6 commit  $7 tree  $8 repo  $9 note
  local name="$1" kind="$2" dest="$3" raw="$4" url="$5" commit="$6" tree="$7" repo="$8" note="$9"
  local rel="${dest#"$STORE"/}" bundle_sha="" refs=""
  zstd -19 -T0 -q -f "$raw" -o "$dest"
  if [ "$kind" = "bundle" ]; then
    bundle_sha="$(sha_of "$raw")"
    refs="$(git bundle list-heads "$raw" | wc -l)"
    git bundle list-heads "$raw" > "$STORE/meta/$name.refs.txt"
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$name" "$kind" "$rel" "$url" "$commit" "$tree" \
    "$(license_spdx "$repo" "$commit")" \
    "$(git -C "$repo" ls-tree "$commit" -- LICENSE NOTICE | awk '{print $4}' | paste -sd, -)" \
    "$(git -C "$repo" show "$commit:LICENSE" 2>/dev/null | sha256sum | cut -d' ' -f1)" \
    "$(sha_of "$dest")" "$(stat -c%s "$dest")" "$(stat -c%s "$raw")" "$bundle_sha" "${refs:-0}" \
    "$(date -u -r "$dest" +%Y-%m-%dT%H:%M:%SZ)" "$note" >> "$WORK/manifest.tsv"
  printf '  %-34s %-6s %10s B stored, %9s B raw  sha256=%s\n' \
    "$name" "$kind" "$(stat -c%s "$dest")" "$(stat -c%s "$raw")" "$(sha_of "$dest")"
}

echo "== upstream bundles =="
for row in "${UPSTREAMS[@]}"; do
  IFS='|' read -r name url commit tree <<<"$row"
  echo "-- $name ($url @ $commit)"
  retry git clone --quiet --mirror "$url" "$WORK/$name.git"
  got="$(git -C "$WORK/$name.git" rev-parse "$commit^{tree}")"
  [ "$got" = "$tree" ] || { echo "FATAL: $name tree mismatch: expected $tree got $got" >&2; exit 1; }
  echo "   tree hash re-checked against the recorded pin: $got"
  git -C "$WORK/$name.git" bundle create "$WORK/$name.bundle" --all >/dev/null
  ( cd "$WORK/$name.git" && git archive --format=tar --prefix="$name/" "$commit" ) > "$WORK/$name.tar"
  emit "$name" bundle "$STORE/bundles/$name.bundle.zst" "$WORK/$name.bundle" "$url" "$commit" "$tree" "$WORK/$name.git" \
       "full mirror of $url as observed at archive time; contains refs/heads/*, refs/tags/* and (GitHub) refs/pull/*"
  emit "$name" tree   "$STORE/trees/$name.tar.zst"       "$WORK/$name.tar"       "$url" "$commit" "$tree" "$WORK/$name.git" \
       "git archive of the pinned tree, no git needed to inspect"
done

echo "== this repository (no remote) =="
for row in "${LOCAL_BUNDLES[@]}"; do
  IFS='|' read -r name bundle_args rev <<<"$row"
  commit="$(git -C "$LOCAL_REPO" rev-parse "${rev}^{commit}")"
  tree="$(git -C "$LOCAL_REPO" rev-parse "${rev}^{tree}")"
  echo "-- $name (git bundle create ... $bundle_args, resolved from $rev -> commit $commit, tree $tree)"
  git -C "$LOCAL_REPO" bundle create "$WORK/$name.bundle" $bundle_args >/dev/null
  ( cd "$LOCAL_REPO" && git archive --format=tar --prefix="$name/" "$commit" ) > "$WORK/$name.tar"
  emit "$name" bundle "$STORE/bundles/$name.bundle.zst" "$WORK/$name.bundle" "" "$commit" "$tree" "$LOCAL_REPO" \
       "working repository at rev $rev; repository has no remote (git remote -v is empty)"
  emit "$name" tree   "$STORE/trees/$name.tar.zst"       "$WORK/$name.tar"       "" "$commit" "$tree" "$LOCAL_REPO" \
       "git archive of the pinned tree, no git needed to inspect"
done

echo "== manifests =="
( cd "$STORE" && sha256sum bundles/*.zst trees/*.zst > SHA256SUMS )

python3 - "$WORK/manifest.tsv" "$HERE/provenance.json" <<'PY'
import json, sys, datetime
cols = ["name","kind","file","url","commit","tree","license","license_files",
        "license_sha256","archive_sha256","size_bytes","uncompressed_bytes",
        "bundle_sha256","refs","produced_at","note"]
import subprocess
def tool(*args):
    return subprocess.run(args, capture_output=True, text=True).stdout.strip().splitlines()[0]
TOOLING = {"git": tool("git", "--version"), "zstd": tool("zstd", "--version")}
rows = []
for line in open(sys.argv[1]):
    line = line.rstrip("\n")
    if not line:
        continue
    parts = line.split("\t")
    rows.append(dict(zip(cols, parts)))
for r in rows:
    r["size_bytes"] = int(r["size_bytes"])
    r["uncompressed_bytes"] = int(r["uncompressed_bytes"])
    r["refs"] = int(r["refs"])
    r["url"] = r["url"] or None
    if not r["bundle_sha256"]:
        del r["bundle_sha256"]
    if not r["license_files"]:
        del r["license_files"]
    if r["license_sha256"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":
        r["license_sha256"] = None
    r["id"] = f"{r['name']}-{r['kind']}"
rows = [dict([("id", r.pop("id"))] + list(r.items())) for r in rows]
manifest = {
    "schema": "a0-archive-provenance/1",
    "store": "/home/ebt/rsi-archive",
    "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "generator": "a0/archive/archive.sh",
    "verifier": "a0/archive/restore_verify.sh",
    "hash_algorithm": "sha256",
    "tooling": {"git": TOOLING["git"], "zstd": TOOLING["zstd"]},
    "field_notes": {
        "uncompressed_bytes": "bundles: the uncompressed .bundle bytes; trees: the uncompressed tar bytes",
        "archive_sha256": "sha256 of the stored .zst artifact as written into the store",
        "bundle_sha256": "sha256 of the uncompressed .bundle (bundles only); re-check with `zstd -d -c FILE | sha256sum`",
        "tree": "git tree hash of `commit`; restore_verify.sh recomputes it from the restored files",
        "license": "SPDX id read from the repository's own LICENSE file at `commit`; NONE_FOUND means the tree has no LICENSE file",
    },
    "artifacts": rows,
}
with open(sys.argv[2], "w") as fh:
    json.dump(manifest, fh, indent=2, sort_keys=False)
    fh.write("\n")
print(f"wrote {sys.argv[2]} with {len(rows)} artifacts")
PY
cp "$HERE/provenance.json" "$STORE/provenance.json"
echo "store: $STORE"
du -sh "$STORE"
