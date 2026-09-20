# Circle-packing campaign program (rendered from EID*)

Rendered by the A0 Loreley adapter from plumbing.EID.json (EID* = 664115e0d63ad2e1113559e1bc4d4a47042daf1131c9a9b2b9d6c868d75e9328).

## Goal

Evolve the circle-packing candidate so that pack_circles(26) returns 26 valid, non-overlapping circles inside the unit square, maximising the sum of radii.

## Primary metric

- name: sum_radii
- direction: maximize
- unit: radius_sum (length in the unit square, n=26)
- evaluator: E* (a3d6534b4e3b)

## Correctness gates

- count_equals_n
- radius_positive_check
- bounds_check
- overlap_check
- determinism_check
- runtime_budget_check

## Editable scope

- solution.py

## Protected scope

- loreley.program.md

## Evaluation budget

- seed: 1337
- fidelity: full
- fraction: 1.0
- n: 26
- runs: 5
- runtime_budget_ms: 250.0
- timeout_s: 120.0

## Complexity policy

- deterministic on repeated calls; no unbounded local search

## Failure policy

- a non-ok E* status is a candidate failure, never a score of 0.0

## Logging policy

- the adapter records traces outside every candidate worktree
