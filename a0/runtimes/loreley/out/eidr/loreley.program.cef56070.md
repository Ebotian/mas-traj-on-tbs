# Circle-packing campaign program (rendered from EID*)

Rendered by the A0 Loreley adapter from plumbing.EID.json (EID* = cef56070e076e35335155793a770c3ffec766d8ac0176d9facebde4d0ef07ae6).

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

## Provenance

EID* component digests (a0/evalcontract/v1). Rendered from the frozen document so
that loreley.program.md - and therefore campaign_program_hash, and therefore EID_r -
is a function of all five EID* inputs and not only of the ones the prose sections
happen to quote:

- EID*: cef56070e076e35335155793a770c3ffec766d8ac0176d9facebde4d0ef07ae6
- EvaluatorSource: a3d6534b4e3bc78f06587bf0281d44b5ddde6de938eb84d87b646dda995edc29
- DependencyLock: 7b02f1a71288335ff92fe68da8804349e416ba4ae9e95f8cd0c6a3b5bc372a75
- DataManifest: b21c975a51ef24cdfb2078957f0e0e4b2fb194e7c55b3a8058febb019d214a21
- Config: 550ca3cdd8af04ec0895a2515bbee40a9627b805d5477611995f4cef0f4043ac
- MetricDefinition: 420ab0acf24e1c7325b089e2ec4bc6c3d074119c4f3ac8aac8ed3cfa1c45bfc0

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
