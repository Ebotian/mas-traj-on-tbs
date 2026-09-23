# `a0/a1/epistemic-container/` — Mechanism C: the agent lane inside a container

The containment alternative to `a0/a1/epistemic-ns/` (Mechanism A, namespace-based). Here the CLI
session runs in a container whose only read-write mount is the session workspace, so the
repository, its git objects, the answer stores and `~/gptapi.md` are not merely unreadable — they
do not exist in that filesystem view.

**Verdict and the full argument: `REPORT.md`.** This file is only how to run it.

## Run it

```bash
cd /home/ebt/rsi-dev
DS_KEY=$(awk -F: '/^deepseek:/{sub(/^deepseek:[ ]*/,""); print; exit}' ~/gptapi.md) \
  a0/a1/epistemic-container/run.sh all     # env up probe call tool verify  (~2 600 CEq)
a0/a1/epistemic-container/run.sh down      # remove every a0ec-* container and network

a0/a1/epistemic-container/probe_bwrap.sh   # no key, no model call, no spend
```

* `run.sh all` pulls nothing (every image it uses is already in the local store) and creates only
  `a0ec-*` names. `verify` re-checks that the pre-existing containers are byte-identical to their
  before-fingerprint.
* The key is never read by the script: it is put in `DS_KEY` by the caller and handed to the
  container with the valueless `docker exec -e DS_KEY` form, so it never reaches argv, a config
  file, or the run directory.
* Run directory: `/tmp/a0ec` (`A0EC_RUN_DIR` to move it). `down` leaves it in place on purpose —
  the ledger inside it is evidence.

## The two variants

| | C1 | C2 |
|---|---|---|
| network | `a0ec-internal` (`--internal`), one dual-homed metering proxy | `--network none`, no route at all |
| the lane's only exit | the meter at `a0ec-meter:8801` | a unix socket bind-mounted at `/run/a0ec/c2.sock` |
| `base_url` in the session | `http://a0ec-meter:8801/v1` | `http://127.0.0.1:8802/v1` (via `sock_forward.py`) |

Both containers: `--cap-drop ALL --security-opt no-new-privileges`, uid 1000, no docker socket.

## Files

| file | what it is |
|---|---|
| `compose.yaml` | C1's session shape: networks, the metering proxy container, the agent container |
| `registry.json` | the meter's campaign registry — one port per campaign, plus its attribution token |
| `codex/C1.config.toml`, `codex/C2.config.toml` | the session `CODEX_HOME` config, `base_url` aimed at the meter |
| `run.sh` | `env \| up \| probe \| call \| tool \| verify \| down \| all` |
| `probe_inside.py` | the in-container probe: what exists, what is reachable, with its controls |
| `sock_forward.py` | C2's in-container TCP → unix-socket pump (no repo in that container, so standalone) |
| `sock_relay.py` | C2's host-side relay; imports `a0.a1.topology.UnixRelay` rather than reimplementing it |
| `probe_bwrap.sh` | is codex's *own* sandbox usable inside a container? — the finding that needs no spend |
| `evidence/` | every transcript `REPORT.md` cites |

## The finding to read first

The container hides the repository, but it also removes **bubblewrap**, which is how codex 0.155.1
implements `read-only` and `workspace-write`. Under a strict container posture the CLI does not
degrade, it panics; `probe_bwrap.sh` walks the ladder and measures the point at which it starts
working (`--privileged`). T1's mode config gives two of its three roles `read-only`, so adopting
this mechanism requires a mode-config change — reported in `REPORT.md` §7, not applied.
