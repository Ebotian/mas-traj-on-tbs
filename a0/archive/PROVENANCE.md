# A0 archival provenance

Purpose: the audited A0 state must stop being *refetchable* and become
*archivally reproducible*. Commit SHAs are content addresses, but they are only
as durable as the repositories that hold them: this working repository has no
remote at all, and one of the pinned upstreams (EvE) lived in `/tmp` and was
already wiped once by a reboot.

* Store: `/home/ebt/rsi-archive` — **outside** this repository, so bundles never
  enter git history and a bundle can never contain itself.
* Machine-readable manifest: `a0/archive/provenance.json` (schema
  `a0-archive-provenance/1`). A copy of it, of both scripts and of the restore
  log is kept in the store itself (`/home/ebt/rsi-archive/meta/`), so the store
  is usable even if this repository is lost.
* Producer: `a0/archive/archive.sh` · Verifier: `a0/archive/restore_verify.sh`
  · Last verification log: `a0/archive/restore-verify.log`.

## Artifacts

Each named repo is stored twice: a `git bundle` of the whole repository
(`bundles/<name>.bundle.zst`) and a `git archive` of the pinned tree
(`trees/<name>.tar.zst`). Both are zstd-compressed. 12 artifacts, 114 MB
total; `sha256` below is the digest of the stored `.zst` file as recorded in
`provenance.json`.

| artifact | pinned commit | tree hash | license | stored | sha256 (first 16) |
|---|---|---|---|---|---|
| kapso.bundle.zst | `7d99b152` | `281ddc61…` | MIT | 49.0 MB | `b3051e10fc8bca02` |
| kapso.tar.zst | `7d99b152` | `281ddc61…` | MIT | 10.2 MB | `d33da4ae25411d00` |
| loreley.bundle.zst | `4c375920` | `27702aab…` | Apache-2.0 | 10.3 MB | `55121bb8a95af14e` |
| loreley.tar.zst | `4c375920` | `27702aab…` | Apache-2.0 | 5.0 MB | `d501a6e2f227ebc3` |
| eve.bundle.zst | `979065fd` | `5d42deab…` | Apache-2.0 | 19.8 MB | `2461b7f41ac44de3` |
| eve.tar.zst | `979065fd` | `5d42deab…` | Apache-2.0 | 10.9 MB | `0eb1f198bc9360c7` |
| circle-packing.bundle.zst | `b91c0906` | `83aff89b…` | NONE_FOUND | 23.7 kB | `9d7fc62aa00e8774` |
| circle-packing.tar.zst | `b91c0906` | `83aff89b…` | NONE_FOUND | 5.0 kB | `2e5814265f10c863` |
| rsi-dev-a0-audited.bundle.zst | `2a61c56b` (tag `a0-audited`) | `29302a13…` | NONE_FOUND | 4.0 MB | `05f486e44978dfa5` |
| rsi-dev-a0-audited.tar.zst | `2a61c56b` | `29302a13…` | NONE_FOUND | 2.1 MB | `66ab3060c6ab6a51` |
| rsi-dev-head.bundle.zst | `261f0c91` (HEAD) | `258705c9…` | NONE_FOUND | 4.8 MB | `159ecdd5d3f253f5` |
| rsi-dev-head.tar.zst | `261f0c91` | `258705c9…` | NONE_FOUND | 2.3 MB | `cc8221afbff6f75d` |

Full digests, byte sizes, the ref counts carried by each bundle, the
`git bundle list-heads` dump per bundle (`meta/<name>.refs.txt`), license file
digests and the producing tool versions are all in `provenance.json`.

### Sources

| artifact | URL | how obtained |
|---|---|---|
| kapso | `https://github.com/Leeroo-AI/kapso.git` | fresh `git clone --mirror` at archive time |
| loreley | `https://github.com/NeapolitanIcecream/loreley.git` | fresh `git clone --mirror` at archive time |
| eve | `https://github.com/scaling-group/eve.git` | fresh `git clone --mirror` at archive time |
| circle-packing | `https://github.com/NeapolitanIcecream/circle-packing.git` | fresh `git clone --mirror` at archive time |
| rsi-dev-a0-audited, rsi-dev-head | *(none — `git remote -v` is empty)* | bundled from the working repo at `/home/ebt/rsi-dev` |

The upstream checkouts used by the A0 lanes are gitignored
(`a0/tasks/circle-packing/upstream/`, `a0/runtimes/loreley/checkout/`), so the
bundles are the only durable copy of those trees; that is exactly why each of
them is archived here. Every pinned commit was re-checked against the recorded
tree hash before being written, and `archive.sh` aborts if they disagree.

### Licenses (read from each repository's own files, not assumed)

* KAPSO — **MIT**, `LICENSE`, sha256 `84fa98c0f044dbb0426c33ca4b346a276e2212472737585711e87da5a733f0a4`.
* EvE — **Apache-2.0**, `LICENSE` sha256 `59cde600d9ffa8bbb9929c151efed5ffcf2af1caf869acf4797a22b1314be538`; the commit also carries a `NOTICE` (NUS, arXiv 2605.09018).
* Loreley — **Apache-2.0**, `LICENSE` sha256 `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`.
* `circle-packing` @ `b91c0906` — **no LICENSE file, no `license` field in `pyproject.toml`** (`license_files` is empty in the manifest). Recorded as `NONE_FOUND`, not as "permissive".
* this repository — **no LICENSE file**. Same.

## Restoring

Third-party recipe for a single bundle (no network needed):

```bash
zstd -d -c /home/ebt/rsi-archive/bundles/loreley.bundle.zst > /tmp/loreley.bundle
git init /tmp/loreley && cd /tmp/loreley
git fetch /tmp/loreley.bundle '+refs/*:refs/archived/*'   # 130 refs + the pinned commit
git checkout --detach 4c3759208e6b908f90716488ac3eec3dceaaf397
git rev-parse HEAD^{tree}   # must print 27702aab867fab41290edbb3036e0e600e3f19f6
```

`git clone <bundle>` also works for the mirrored upstreams (their bundle carries
a HEAD). The tag-only bundle `rsi-dev-a0-audited` has no HEAD ref, so
`git clone` prints `warning: remote HEAD refers to nonexistent ref`; use the
`git fetch` form above, which is what the verifier does for every artifact.

Reproduce the whole store from scratch (needs egress; ~10 min):

```bash
a0/archive/archive.sh [store_dir]     # default /home/ebt/rsi-archive
```

## Verification

```bash
a0/archive/restore_verify.sh          # offline; defaults to /home/ebt/rsi-archive
```

For each artifact it re-checks the stored SHA256, then for bundles fetches the
bundle into a fresh temporary repo, runs `git fsck --full --strict` (re-hashing
every object from its stored bytes), checks the pinned commit out, and rebuilds
the tree hash from the files on disk with an empty index (`git add -A -f` +
`git write-tree`) so every blob is re-hashed from restored content; for the tar
complement it extracts and rebuilds the tree the same way. Result of the run
recorded in `a0/archive/restore-verify.log` (store artifacts produced
2026-09-21T07:47–07:49Z, verification completed 2026-09-21T08:06Z, git 2.55.0,
zstd 1.5.7): **54 checks OK, 0 FAIL — "all artifacts restored and verified"**,
in particular every recomputed tree hash equalled the recorded one.

Two honest limitations of that test:

* Gitlinks (submodule pointers) carry no content. `kapso` has 5 such paths and
  `loreley` one (`examples/circle-packing`), so the tree-hash rebuild re-adds
  those entries from the restored object DB (bundle) or from the sibling
  restored bundle (tar) instead of from file content. Everything else in the
  tree is re-hashed from disk.
* `git bundle` bytes are not stable across regenerations. `rsi-dev-a0-audited`
  reproduced byte-identically over two runs, but `rsi-dev-head` and the
  `loreley` mirror bundle did not, with the same ref list both times (upstream
  `refs/pull/*` movement and/or pack-objects non-determinism — not isolated).
  Verification therefore rests on the pinned commit and tree hash, which
  reproduced identically in every run, not on bundle bytes.

## Residual risk — what this archival does **not** protect

1. **Same physical disk.** Store and sources both live on `/dev/nvme0n1p3`. A
   disk failure, filesystem corruption, or a wipe of `/home` destroys the
   original and the backup together. There is no second copy, no offline copy,
   and no off-machine copy.
2. **Ongoing work is still unprotected.** The bundles are point-in-time
   snapshots. Every commit made after the archive (HEAD `261f0c91`) exists only
   in the working repo, which still has no remote. The archive is a ritual, not
   a background process — nothing re-runs `archive.sh`.
3. **The manifest itself is not in the bundle.** `a0/archive/**` is new and
   uncommitted, so `rsi-dev-head.bundle.zst` (HEAD `261f0c91`) does not contain
   it. It is duplicated into the store's `meta/` to compensate, but the two
   copies can drift.
4. **Uncommitted state is not archived.** Only committed trees are bundled, at
   `a0-audited` and at HEAD. The run outputs, probe records, venvs and
   materialised workspaces under `a0/**/out/`, `a0/runtimes/**/out/` are
   gitignored or untracked; several lanes had uncommitted modifications while
   this archive was taken. A restore gives the committed state, not the state of
   the working tree on the day.
5. **Secret material.** The DeepSeek API key in `~/gptapi.md` is plaintext and
   deliberately *not* archived: it is not recoverable from anything here, and
   losing or leaking it is outside this archive's reach. Nothing in the store
   holds the key (checked: no file under `/home/ebt/rsi-archive` contains it).
6. **Unarchived submodule content.** `kapso`'s pinned commit carries 5 gitlink
   entries but has **no `.gitmodules`**, so the upstream URLs of
   `examples/{agentic_scaffold, cuda_optimization, ml_model_development,
   prompt_engineering, pytorch_optimization}/*_optimized` are unknown, and their
   commits (`3828e27a`, `db33cd71`, `8a118944`, `7509cd50`, `51b65265`) are not
   in the kapso repo. Their content is not archived anywhere. `loreley`'s single
   gitlink (`b91c0906`) *is* covered, by the `circle-packing` bundle.
7. **`/tmp` snapshots in active use.** The EvE checkout the lanes use is still
   `/tmp/eve`; the bundle preserves its commit, but a reboot still breaks the
   live lanes until someone re-clones from the bundle or the upstream.
8. **Live upstreams can move.** The bundles were taken from live mirrors: if an
   upstream force-pushes or disappears, the archive is the only copy, and the
   only assurance of what the audited lanes ran is the tree hash recorded here.
9. **SHA-1 content addressing and hash downgrade.** The git objects are SHA-1;
   the archive digests are SHA-256 but cover the stored artifact, not the
   internal object graph. A collision attack against a tree hash is not
   detected by this test.
10. **License/redistribution status of `circle-packing` and of this repository
    is undefined** (no LICENSE file). Archiving is fine; redistributing these
    bundles externally is not clearly permitted.

## Decisions left to the coordinator

* Whether to commit `a0/archive/**` (and thereby get it into the next bundle).
* Whether to take a second copy off this disk (external drive, host, or a
  private remote) — this is the single biggest remaining gap.
* Whether to add a remote for ongoing work, or to make `archive.sh` part of the
  lane-closing ritual.
* Whether to widen the archive to uncommitted outputs and to the five kapso
  gitlink targets.
