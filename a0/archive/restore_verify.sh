#!/usr/bin/env bash
# Offline restore test for the A0 archival artifacts.
#
# For every artifact listed in provenance.json this script:
#   * re-checks the stored file against the recorded SHA256,
#   * for `bundle` artifacts: fetches the bundle into a fresh temporary repo,
#     runs `git fsck --full --strict` (re-hashes every object from its stored
#     bytes), checks the pinned commit out, and rebuilds the tree from the
#     files on disk with an empty index (`git add -A -f` + `git write-tree`),
#     so every blob is re-hashed from restored content,
#   * for `tree` artifacts (the `git archive` complement): extracts the tar and
#     rebuilds the tree from the extracted files the same way,
# and compares the rebuilt tree hash with the recorded value.
#
# No network and no access to the original clones is needed.
#
# Usage: a0/archive/restore_verify.sh [store_dir]
#   store_dir defaults to /home/ebt/rsi-archive
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="$HERE/provenance.json"
STORE="${1:-/home/ebt/rsi-archive}"
WORK="$(mktemp -d /tmp/a0-restore-verify-XXXXXX)"
trap 'rm -rf "$WORK"' EXIT

fail=0
note() { printf '%s\n' "$*"; }
verdict() { # $1 OK|FAIL, $2 id, $3 detail
  [ "$1" = "OK" ] || fail=1
  printf '  [%-4s] %s: %s\n' "$1" "$2" "$3"
}

note "store:    $STORE"
note "manifest: $MANIFEST"
note "workdir:  $WORK"
note

# id<TAB>kind<TAB>file<TAB>commit<TAB>tree<TAB>sha256
mapfile -t ROWS < <(python3 - "$MANIFEST" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
for a in m["artifacts"]:
    print("\t".join([a["id"], a["kind"], a["file"], a["commit"],
                     a["tree"], a["archive_sha256"]]))
PY
)

declare -A RESTORED_REPO=()

# Rebuild the tree of the working tree at $1 (with submodule/gitlink entries
# supplied from $2 = the independently restored sibling bundle repo, if any)
# and print the resulting tree hash.
rebuild_tree() {
  local wd="$1" sibling="${2:-}" commit="$3"
  local idx="$WORK/$(basename "$wd").index" gl=0
  rm -f "$idx"; : > "$WORK/gitlinks.txt"
  GIT_INDEX_FILE="$idx" git -C "$wd" --work-tree="$wd" add -A -f -- . 2>"$WORK/add.err" || {
    printf 'ADD_FAILED %s\n' "$(tail -1 "$WORK/add.err")" >&2; return 1; }
  if [ -n "$sibling" ] && [ -d "$sibling/.git" ]; then
    while IFS=$'\t' read -r sha path; do
      [ -n "${path:-}" ] || continue
      GIT_INDEX_FILE="$idx" git -C "$wd" --work-tree="$wd" update-index --add --cacheinfo "160000,$sha,$path" || return 1
      printf '%s\t%s\n' "$sha" "$path" >> "$WORK/gitlinks.txt"
      gl=$((gl + 1))
    done < <(git -C "$sibling" ls-tree -r "$commit" | awk '$2=="commit" {print $3"\t"$4}')
  fi
  GIT_INDEX_FILE="$idx" git -C "$wd" --work-tree="$wd" write-tree
}

for row in "${ROWS[@]}"; do
  IFS=$'\t' read -r id kind file commit tree sha <<<"$row"
  name="${id%-*}"
  note "=== $id ($kind) ==="
  src="$STORE/$file"
  if [ ! -f "$src" ]; then verdict FAIL "$id" "missing artifact $src"; note; continue; fi

  actual_sha="$(sha256sum "$src" | cut -d' ' -f1)"
  if [ "$actual_sha" = "$sha" ]; then
    verdict OK "$id" "stored artifact sha256 matches manifest ($actual_sha)"
  else
    verdict FAIL "$id" "sha256 mismatch: manifest=$sha actual=$actual_sha"
  fi

  if [ "$kind" = "bundle" ]; then
    repo="$WORK/$id"
    zstd -d -q -c "$src" > "$repo.bundle"
    git init -q "$repo"
    if git -C "$repo" fetch -q "$repo.bundle" '+refs/*:refs/restored/*' 2>"$WORK/$id.fetch.err"; then
      verdict OK "$id" "bundle fetched ($(git -C "$repo" for-each-ref refs/restored | wc -l) refs restored)"
    else
      verdict FAIL "$id" "bundle fetch failed: $(tail -1 "$WORK/$id.fetch.err")"; note; continue
    fi
    if git -C "$repo" cat-file -e "$commit^{commit}" 2>/dev/null; then
      verdict OK "$id" "pinned commit $commit present in restored repo"
    else
      verdict FAIL "$id" "pinned commit $commit absent from bundle"; note; continue
    fi
    if git -C "$repo" fsck --full --strict --no-progress >"$WORK/$id.fsck.out" 2>&1; then
      verdict OK "$id" "git fsck --full --strict clean (output: $(wc -l < "$WORK/$id.fsck.out") lines)"
    else
      verdict FAIL "$id" "git fsck reported problems: $(head -3 "$WORK/$id.fsck.out" | tr '\n' ' ')"
    fi
    if git -C "$repo" checkout -q --detach "$commit" 2>"$WORK/$id.checkout.err"; then
      verdict OK "$id" "checked out $commit into a working tree ($(find "$repo" -path "$repo/.git" -prune -o -type f -print | wc -l) files)"
    else
      verdict FAIL "$id" "checkout of $commit failed: $(tail -1 "$WORK/$id.checkout.err")"; note; continue
    fi
  else
    mkdir -p "$WORK/trees"
    if zstd -d -q -c "$src" | tar -x -C "$WORK/trees" -f - 2>"$WORK/$id.tar.err"; then
      verdict OK "$id" "tar extracted ($(find "$WORK/trees/$name" -type f | wc -l) regular files, $(find "$WORK/trees/$name" -type l | wc -l) symlinks)"
    else
      verdict FAIL "$id" "tar extraction failed: $(tail -1 "$WORK/$id.tar.err")"; note; continue
    fi
    repo="$WORK/trees/$name"
    git init -q "$repo"
  fi

  # gitlink (submodule) entries carry no content, so they cannot be rebuilt
  # from a checkout or a tar; their SHAs are read back from the restored tree
  # (bundle: its own object DB; tar: the sibling bundle restored just above)
  sibling="${RESTORED_REPO[$name]:-}"
  glsrc="$sibling"
  [ "$kind" = "bundle" ] && glsrc="$repo"
  rebuilt="$(rebuild_tree "$repo" "$glsrc" "$commit" 2>"$WORK/$id.rebuild.err")"
  gl_note=""
  if [ -n "$glsrc" ]; then
    gl_src="the sibling bundle"
    [ "$kind" = "bundle" ] && gl_src="the restored tree itself"
    gl_note=" (gitlink entries re-added from $gl_src: $(wc -l < "$WORK/gitlinks.txt" 2>/dev/null || echo 0))"
  else
    gl_note=" (no sibling bundle restored: submodule/gitlink entries cannot be rebuilt from a tar)"
  fi
  if [ "$rebuilt" = "$tree" ]; then
    verdict OK "$id" "tree hash recomputed from restored files: $rebuilt == recorded$gl_note"
  else
    verdict FAIL "$id" "tree hash mismatch: recorded=$tree recomputed=$rebuilt$gl_note"
  fi
  [ "$kind" = "bundle" ] && RESTORED_REPO[$name]="$repo"
  note
done

if [ "$fail" -eq 0 ]; then note "RESULT: all artifacts restored and verified"; else note "RESULT: at least one check FAILED"; fi
exit "$fail"
