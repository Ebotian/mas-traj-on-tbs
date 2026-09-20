# evolve-testbed

Circle packing testbed for the `simple_evolve` tmux Codex demo in `scaling-evolve-core`.

**Problem:** Place 26 circles in a unit square [0, 1]^2 to maximize the sum of their radii. Circles must not overlap each other or extend outside the square. The AlphaEvolve benchmark target is 2.635.

## Files

- `candidate.py` — mutation target. Defines `construct_packing()` which returns `(centers, radii)`.
- `evaluate.py` — local evaluator. Loads `candidate.py`, accepts only builtin numeric values, requires exactly 26 finite circles, validates the packing, recomputes `sum(radii)`, and uses that calculated total as the score.

## Manual evaluation

```bash
python3 evaluate.py
```

## How the demo uses this repo

The demo coordinator (`scaling-evolve-core`) creates git worktrees from this repository, asks Codex to mutate `candidate.py` in each worktree, and then asks a separate Codex pane to run `evaluate.py` and write the result back.
