# egress — layered network policy for the harbor sandboxes

Enforcement stays harbor's sidecar (domain level, SNI allowlist, fail-closed);
the explicit gateway adds the time gate and the forbidden-answer layer.
Design ledger: `related_files/2026-10-10-temporal-firewall-design-note.md` (rsi-dev), sections 7–9.

## Component map

| piece | role |
|---|---|
| `policies/base.yml` | LAYER 1 — fixed infrastructure (model endpoints, install chain, apt/pip, example.com, gateway IP) |
| `policies/<task>.yml` | LAYER 2 — per-task overlay (direct knowledge hosts, gateway surfaces, cutoff, forbidden sources) |
| `policies/_template.yml` | the full overlay template — NOT an instance (the contract suite skips `_`-prefixed stems) |
| `rulelib.py` | pure rules (compose / date window) shared by the tools, tests and the gateway |
| `validate.py` | manifest checks (host syntax, cross-layer dupes, cutoff ISO, fail-closed defaults) |
| `render.py` | compose base+overlay → the task copy's `allowed_hosts` (check by default; `--write`; `--toml` selects the copy) |
| `sync.py` | re-apply the FULL composed list to a live sidecar (dry by default; `network-policy allow` replaces the whole list) |
| `tests/` | task-independent contract tests + per-task pair suites (+ `task_template/` for isomorphic migration) |
| `gateway/` | explicit gateway: github+nature surfaces, forbidden layer, audit JSONL, sha256 cache |

## Instantiation SOP (fixed 2026-10-10)

1. `cp policies/_template.yml policies/<task-slug>.yml`  (filename stem == task_id)
2. fill every REPLACE-ME; keep both `unknown_*: deny`; keep `forbidden_sources` non-empty
3. `python3 validate.py --task <slug>`
4. `python3 render.py --task <slug> --write`  (add `--toml` for a sandbox copy other than the default active one)
5. `python3 ../config/check_paths.py` ; `python3 -m unittest discover -s tests`
6. only for the ACTIVE task: `python3 sync.py --task <slug>` (re-applies the FULL list to the live sidecar)
7. pair suites: copy `tests/task_template/` to `tests/<task_underscored>/` and fill ONLY `fixtures.py`

## Instances

| instance | copy | status | notes |
|---|---|---|---|
| `tumor-immune-interface` v6 | `build/task-restricted` | hosts **live** · temporal candidate · gateway **live** | 17 hosts rendered; live sidecar list verified; gateway v1 (github+nature) incl. the v3 deny-reason hint |
| dual-agent sandbox (H2 / walkthrough) | `build/task-restricted` | inherits the row above **unchanged** | the two-agent additions (git, board, wrapper) are container-local; no new network opens are needed |

Engines: banned project-wide (`tests/common.py ENGINES`); nothing engine-shaped may appear in `restricted_hosts`.
Verifier side: `no-network`, unrelated to this component.
