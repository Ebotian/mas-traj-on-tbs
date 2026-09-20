"""Rebuild `C_STAR/` (the frozen candidate set) and `C_STAR/manifest.json`.

`C_STAR` is deliberately *not* a set of pointers into mutable worktrees: every
member is a directory holding the complete candidate source (`solution.py`) plus
a `candidate.json` record of its identity, version and purpose, and the manifest
freezes the sha256 of every candidate source.

The geometry of the good candidate comes from `tools/good_packing_26.json`,
which is the recorded output of `tools/make_good_packing.py`.  Everything else in
this file is a small, hand-written variation on that geometry, so the whole set
is reproducible with:

    .venv/bin/python tools/build_c_star.py --check      # verify the tree matches
    .venv/bin/python tools/build_c_star.py --write      # (re)write the tree
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
C_STAR = ROOT / "C_STAR"
GOOD_PACKING = HERE / "good_packing_26.json"
VERSION = "1.0.0"

UPSTREAM_BASELINE = ROOT / "upstream" / "circle-packing" / "solution.py"
UPSTREAM_BASELINE_COMMIT = "b91c0906c9f676eb661990d881144909d99f2d72"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_geometry() -> dict[str, Any]:
    payload = json.loads(GOOD_PACKING.read_text(encoding="utf-8"))
    centres = [(float(x), float(y)) for x, y in payload["centres"]]
    radius = float(payload["r_used"])
    assert len(centres) == 26, len(centres)
    return {"centres": centres, "radius": radius, "payload": payload}


def _format_table(circles: list[tuple[float, float, float]]) -> str:
    lines = []
    for x, y, r in circles:
        lines.append(f"    ({x!r}, {y!r}, {r!r}),")
    return "\n".join(lines)


def _solution_source(
    *,
    docstring: str,
    circles: list[tuple[float, float, float]] | None,
    body: str,
    extra_imports: str = "",
    table_note: str = "",
) -> str:
    parts = [
        '"""' + docstring + '"""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Iterable, List, Tuple",
    ]
    if extra_imports:
        parts.append(extra_imports.rstrip())
    parts.append("")
    if circles is not None:
        parts.append(table_note.rstrip())
        parts.append("TABLE_26: List[Tuple[float, float, float]] = [")
        parts.append(_format_table(circles))
        parts.append("]")
        parts.append("")
    parts.append(
        '''
def _fallback(n: int) -> List[Tuple[float, float, float]]:
    """Upstream's baseline construction, valid for any n (solution.py@b91c090)."""
    if n <= 0:
        raise ValueError("n must be a positive integer.")
    if n == 1:
        return [(0.5, 0.5, 0.5)]
    r = 1.0 / (4.0 * n)
    step = 1.0 - 2.0 * r
    return [(r + (i / (n - 1)) * step, r + (i / (n - 1)) * step, r) for i in range(n)]


def pack_circles(n: int = 26) -> Iterable[Tuple[float, float, float]]:
    """Return (x, y, r) triples for n circles in the unit square."""
'''.rstrip("\n")
    )
    parts.append(body.rstrip("\n"))
    parts.append("")
    return "\n".join(parts)


def build_candidates(geom: dict[str, Any]) -> dict[str, dict[str, Any]]:
    centres = geom["centres"]
    r = geom["radius"]
    base = [(x, y, r) for x, y in centres]
    table_note = (
        f"# 26 equal circles of radius {r!r}, centres frozen by\n"
        "# tools/make_good_packing.py (see tools/good_packing_26.json)."
    )

    default_body = """    if n != 26:
        return _fallback(n)
    return list(TABLE_26)"""

    mirror = [(y, x, rr) for x, y, rr in base]
    near_tie = list(base)
    near_tie[0] = (near_tie[0][0], near_tie[0][1], near_tie[0][2] - 1e-4)
    overlapping = list(base)
    overlapping[1] = (base[0][0], base[0][1], base[1][2])
    shifted = [(x - 0.05, y, rr) for x, y, rr in base]

    candidates: dict[str, dict[str, Any]] = {}

    candidates["c01_good_hex"] = {
        "kind": "valid",
        "summary": "clearly good valid packing (26 equal circles, r ~ 0.0943)",
        "purpose": (
            "The high end of the required ordered pair: the A0.2 tests need "
            "E(c1) > E(c2) with a decidable margin, and c01 is that c1."
        ),
        "source": _solution_source(
            docstring=(
                "Frozen good packing candidate for the plumbing task.\n\n"
                "26 equal-radius circles packed in the unit square, produced offline by\n"
                "tools/make_good_packing.py (jammed max-min packing, r* ~ 0.0943).\n"
                "Deterministic, no imports beyond typing, well under the 250 ms budget."
            ),
            circles=base,
            body=default_body,
            table_note=table_note,
        ),
        "expected_status": "ok",
    }

    candidates["c02_baseline_upstream"] = {
        "kind": "valid",
        "summary": "upstream baseline from circle-packing@b91c090 (sum_radii = 0.25)",
        "purpose": (
            "The clearly bad member of the required ordered pair, taken verbatim "
            "from upstream, so it is also the study's c_0 baseline for SimpleLoop "
            "(4.4: 'c_0 = baseline')."
        ),
        "source": UPSTREAM_BASELINE.read_text(encoding="utf-8"),
        "verbatim_from": {
            "repo": "https://github.com/NeapolitanIcecream/circle-packing.git",
            "commit": UPSTREAM_BASELINE_COMMIT,
            "path": "solution.py",
        },
        "expected_status": "ok",
    }

    candidates["c03_mirror"] = {
        "kind": "valid",
        "summary": "c01 reflected across the main diagonal: different content, identical score",
        "purpose": (
            "Required tied pair: (x, y) swapped is an exact isometry, so every "
            "metric equals c01's to the last bit while the file bytes differ. "
            "Downstream tie tests and the 'identical structure, different "
            "content' check both use it."
        ),
        "source": _solution_source(
            docstring=(
                "Mirror image of c01_good_hex: the same 26 circles with x and y swapped.\n\n"
                "Reflection is an exact isometry of the unit square, so sum_radii,\n"
                "packing_density, min_gap and min_boundary_margin are bit-identical to\n"
                "c01 while the source bytes differ."
            ),
            circles=mirror,
            body=default_body,
            table_note=table_note,
        ),
        "expected_status": "ok",
    }

    candidates["c04_near_tie"] = {
        "kind": "valid",
        "summary": "c01 with one radius reduced by 1e-4: near-tied, decidable margin",
        "purpose": (
            "Required near-tied pair: sum_radii differs from c01 by exactly 1e-4, "
            "which is decidable in binary64 yet small enough to stress adapters "
            "that compare scores with sloppy tolerances."
        ),
        "source": _solution_source(
            docstring=(
                "Near-tie variant of c01_good_hex: one radius shrunk by 1e-4.\n\n"
                "Shrinking a radius can neither break the square bounds nor create an\n"
                "overlap, so the configuration stays valid and only the objective moves."
            ),
            circles=near_tie,
            body=default_body,
            table_note=table_note,
        ),
        "expected_status": "ok",
    }

    candidates["c05_overlapping"] = {
        "kind": "invalid_geometry",
        "summary": "26 circles with one pair fully overlapping",
        "purpose": (
            "Degenerate geometry: upstream's overlap gate must reject it. Distinct "
            "from a zero score because E* returns status=invalid with objective=null "
            "and a nonzero overlap_count."
        ),
        "source": _solution_source(
            docstring=(
                "Degenerate candidate: circle #1 is placed on top of circle #0.\n\n"
                "Structurally complete (26 triples, positive radii, inside the square)\n"
                "but geometrically invalid: the pair exploits that upstream's overlap\n"
                "gate, not the count gate, is what rejects it."
            ),
            circles=overlapping,
            body=default_body,
            table_note=table_note,
        ),
        "expected_status": "invalid",
    }

    candidates["c06_empty"] = {
        "kind": "invalid_geometry",
        "summary": "returns no circles at all",
        "purpose": (
            "Empty-output degenerate case: count gate fails. An adapter that maps "
            "'no objective' to 0.0 would be indistinguishable from c14's genuine "
            "near-zero score, which is what this pair of candidates is for."
        ),
        "source": _solution_source(
            docstring="Degenerate candidate: pack_circles returns an empty iterable.",
            circles=None,
            body="    return []",
        ),
        "expected_status": "invalid",
    }

    candidates["c07_single"] = {
        "kind": "invalid_geometry",
        "summary": "returns exactly one circle",
        "purpose": (
            "One-circle degenerate case: the single circle is perfectly valid "
            "(r = 0.5 centred in the square), so only the count gate rejects it. "
            "Exercises the audit-scope fields (1 audited item, 0 audited pairs)."
        ),
        "source": _solution_source(
            docstring=(
                "Degenerate candidate: a single circle that fills the square.\n\n"
                "Valid geometry for n = 1, wrong for the requested n = 26."
            ),
            circles=None,
            body="    return [(0.5, 0.5, 0.5)]",
        ),
        "expected_status": "invalid",
    }

    candidates["c08_out_of_bounds"] = {
        "kind": "invalid_geometry",
        "summary": "c01 translated 0.05 to the left, so all 26 circles leave the square",
        "purpose": (
            "Isolated bounds-gate failure: translation preserves every pairwise "
            "distance, so overlap_count stays 0 and only the bounds check fails."
        ),
        "source": _solution_source(
            docstring=(
                "Degenerate candidate: the good packing translated by (-0.05, 0).\n\n"
                "Translation preserves pairwise distances (no new overlaps) but pushes\n"
                "every circle outside the unit square."
            ),
            circles=shifted,
            body=default_body,
            table_note=table_note,
        ),
        "expected_status": "invalid",
    }

    candidates["c09_malformed_import"] = {
        "kind": "not_measurable",
        "summary": "solution.py does not parse",
        "purpose": (
            "Malformed candidate: E* cannot import it, so it must report status=error "
            "(not invalid, not 0.0). A runtime whose adapter swallows import errors "
            "and substitutes a score is exactly the false green A0.1 looks for."
        ),
        "source": (
            '"""Malformed candidate: this file is deliberately not valid Python."""\n'
            "\n"
            "from typing import Iterable, Tuple\n"
            "\n"
            "\n"
            "def pack_circles(n: int = 26) -> Iterable[Tuple[float, float, float]:\n"
            "    return [(0.5, 0.5, 0.5\n"
        ),
        "expected_status": "error",
    }

    candidates["c10_raises"] = {
        "kind": "not_measurable",
        "summary": "pack_circles raises on every call",
        "purpose": (
            "Candidate that fails at call time: E* reports status=error with "
            "kind=candidate_call_raised. Covers the 'evaluation exception silently "
            "mapped to failure_score(0.0)' false green directly."
        ),
        "source": _solution_source(
            docstring="Degenerate candidate: pack_circles raises unconditionally.",
            circles=None,
            body=(
                '    raise RuntimeError("this candidate never returns a configuration")\n'
                "    # unreachable, kept so the module still parses as a solution\n"
                "    return []  # type: ignore[unreachable]"
            ),
        ),
        "expected_status": "error",
    }

    candidates["c11_non_deterministic"] = {
        "kind": "not_measurable",
        "summary": "valid geometry, but the returned radii differ between calls",
        "purpose": (
            "Non-determinism gate (upstream evaluate.py:256-259). Each call is "
            "individually valid, so only the cross-run comparison rejects it: "
            "status=error, objective=null, never 0.0."
        ),
        "source": _solution_source(
            docstring=(
                "Degenerate candidate: every call returns a valid configuration, but\n"
                "the radii alternate between two values, so repeated calls disagree."
            ),
            circles=base,
            extra_imports=(
                "\n_CALLS = [0]\n"
                "\n"
                "\n"
                "def _next_scale() -> float:\n"
                "    _CALLS[0] += 1\n"
                "    return 1.0 if _CALLS[0] % 2 else 1.0 - 1e-12\n"
            ),
            body=(
                "    scale = _next_scale()\n"
                "    if n != 26:\n"
                "        return _fallback(n)\n"
                "    return [(x, y, r * scale) for x, y, r in TABLE_26]"
            ),
            table_note=table_note,
        ),
        "expected_status": "error",
    }

    candidates["c12_exit_without_artifacts"] = {
        "kind": "not_measurable",
        "summary": "kills its own interpreter with os._exit(0) instead of returning",
        "purpose": (
            "False-green trap: the isolated runner exits with code 0 without writing "
            "any artifact. E* must detect the missing done marker and report "
            "status=error (kind=child_terminated_early); a runtime that reads only "
            "the subprocess exit code would score this as success/0.0."
        ),
        "source": _solution_source(
            docstring=(
                "Degenerate candidate: exits the interpreter immediately.\n\n"
                "os._exit(0) cannot be caught, so the isolated runner dies before it can\n"
                "record anything."
            ),
            circles=None,
            extra_imports="\nimport os",
            body=(
                "    os._exit(0)\n"
                "    # unreachable, kept so the module still parses as a solution\n"
                "    return []  # type: ignore[unreachable]"
            ),
        ),
        "expected_status": "error",
    }

    candidates["c13_slow"] = {
        "kind": "not_measurable",
        "summary": "returns c01's geometry, but sleeps 0.3 s per call",
        "purpose": (
            "Runtime-budget gate (upstream DEFAULT_RUNTIME_BUDGET_MS = 250 ms). The "
            "geometry is valid, so the only failure is the p50 budget: status=error, "
            "objective=null."
        ),
        "source": _solution_source(
            docstring=(
                "Degenerate candidate: c01's geometry behind a 0.3 s sleep.\n\n"
                "The returned configuration is valid, so the runtime budget is the only\n"
                "gate it violates."
            ),
            circles=base,
            extra_imports="\nimport time",
            body=(
                "    time.sleep(0.3)\n"
                "    if n != 26:\n"
                "        return _fallback(n)\n"
                "    return list(TABLE_26)"
            ),
            table_note=table_note,
        ),
        "expected_status": "error",
    }

    candidates["c14_near_zero"] = {
        "kind": "valid",
        "summary": "valid but nearly worthless: 26 circles of radius 1e-6",
        "purpose": (
            "A genuine near-zero objective. Required so that the degenerate "
            "candidates (c06 empty, c10 raising) are distinguishable from a real "
            "0-ish score: E*(c14) is a number ~2.6e-05, E*(c06) is null."
        ),
        "source": _solution_source(
            docstring=(
                "Valid but nearly worthless candidate: 26 circles of radius 1e-6 in a\n"
                "tight cluster at the centre of the square. sum_radii ~ 2.6e-05."
            ),
            circles=None,
            body=(
                "    if n <= 0:\n"
                '        raise ValueError("n must be a positive integer.")\n'
                "    radius = 1e-6\n"
                "    spacing = 1e-5\n"
                "    circles: List[Tuple[float, float, float]] = []\n"
                "    for index in range(n):\n"
                "        row, col = divmod(index, 13)\n"
                "        circles.append(\n"
                "            (\n"
                "                0.5 - 6.0 * spacing + col * spacing,\n"
                "                0.5 + (row - 0.5) * spacing,\n"
                "                radius,\n"
                "            )\n"
                "        )\n"
                "    return circles"
            ),
        ),
        "expected_status": "ok",
    }

    return candidates


ROLES = {
    "c01_good_hex": "good",
    "c02_baseline_upstream": "baseline",
    "c03_mirror": "tie",
    "c04_near_tie": "tie",
    "c05_overlapping": "bad",
    "c06_empty": "bad",
    "c07_single": "bad",
    "c08_out_of_bounds": "bad",
    "c09_malformed_import": "bad",
    "c10_raises": "bad",
    "c11_non_deterministic": "bad",
    "c12_exit_without_artifacts": "bad",
    "c13_slow": "bad",
    "c14_near_zero": "bad",
}


def build_manifest(candidates: dict[str, dict[str, Any]]) -> dict[str, Any]:
    entries = []
    for candidate_id in sorted(candidates):
        spec = candidates[candidate_id]
        source = spec["source"].encode("utf-8")
        entry = {
            # `a0.candidateset/v1` fields required by a0/contract/adapter_contract.md §2
            "candidate_id": candidate_id,
            "path": candidate_id,
            "solution_sha256": sha256_bytes(source),
            "role": ROLES[candidate_id],
            "note": spec["summary"],
            # circle-packing workstream provenance
            "dir": candidate_id,
            "version": VERSION,
            "kind": spec["kind"],
            "purpose": spec["purpose"],
            "expected_status_at_theta_e_star": spec["expected_status"],
            "source": {
                "path": f"{candidate_id}/solution.py",
                "bytes": len(source),
                "sha256": sha256_bytes(source),
            },
        }
        if "verbatim_from" in spec:
            entry["verbatim_from"] = spec["verbatim_from"]
        entries.append(entry)

    return {
        "schema": "a0.candidateset/v1",
        "candidate_set_id": "C*",
        "task": "circle-packing",
        "version": VERSION,
        "produced_by": "a0/tasks/circle-packing/tools/build_c_star.py",
        "e_star_table": "a0/tasks/circle-packing/E_STAR.json",
        "e_star_cli": (
            "a0/tasks/circle-packing/.venv/bin/python a0/tasks/circle-packing/e_star.py "
            "evaluate --candidate <path> --seed <S> --fidelity <full|fast> --out <json>"
        ),
        "candidate_count": len(entries),
        "candidates": entries,
        "role_legend": {
            "good": "clearly good valid candidate",
            "baseline": "the upstream baseline (c_0)",
            "tie": "member of a tied or near-tied pair",
            "bad": "degenerate, invalid or unmeasurable candidate",
        },
        "designed_relations": {
            "ordered_pair_decidable_margin": {
                "greater": "c01_good_hex",
                "less": "c02_baseline_upstream",
                "note": "A0.2 needs E(c1) > E(c2) with a margin that no reasonable "
                        "tolerance can absorb (about 2.2 vs 0.25).",
            },
            "exact_tie_different_content": {
                "pair": ["c01_good_hex", "c03_mirror"],
                "note": "Identical structure (mirrored geometry, bit-identical metrics), "
                        "different content (different source sha256).",
            },
            "near_tie": {
                "pair": ["c01_good_hex", "c04_near_tie"],
                "note": "objective differs by 1e-4 up to binary64 summation error "
                        "(measured 1.0000000000021e-04 at theta_E*).",
            },
            "genuine_near_zero": "c14_near_zero",
            "returns_instead_of_raising": [
                "c05_overlapping",
                "c06_empty",
                "c07_single",
                "c08_out_of_bounds",
            ],
            "expected_to_raise_not_return": [
                "c09_malformed_import",
                "c10_raises",
                "c11_non_deterministic",
                "c12_exit_without_artifacts",
                "c13_slow",
            ],
        },
        "notes": [
            "Candidate directories contain solution.py (the upstream entry point) plus "
            "candidate.json (identity, version, purpose); no pointer to a mutable worktree.",
            "The directory is C_STAR/ (this workstream's layout). adapter_contract.md §3 "
            "shows `candidates/manifest.json`; pass "
            "`--candidate-set a0/tasks/circle-packing/C_STAR/manifest.json` instead.",
        ],
    }


def write_tree(candidates: dict[str, dict[str, Any]], manifest: dict[str, Any]) -> None:
    C_STAR.mkdir(parents=True, exist_ok=True)
    for candidate_id, spec in candidates.items():
        directory = C_STAR / candidate_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "solution.py").write_text(spec["source"], encoding="utf-8")
        entry = next(
            item for item in manifest["candidates"] if item["candidate_id"] == candidate_id
        )
        record = {
            "candidate_id": candidate_id,
            "version": VERSION,
            "role": ROLES[candidate_id],
            "kind": spec["kind"],
            "summary": spec["summary"],
            "purpose": spec["purpose"],
            "expected_status_at_theta_e_star": spec["expected_status"],
            "source_sha256": entry["source"]["sha256"],
            "source_bytes": entry["source"]["bytes"],
        }
        if "verbatim_from" in spec:
            record["verbatim_from"] = spec["verbatim_from"]
        (directory / "candidate.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (C_STAR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write C_STAR/")
    parser.add_argument("--check", action="store_true", help="verify C_STAR/ matches")
    args = parser.parse_args()

    geom = load_geometry()
    candidates = build_candidates(geom)
    manifest = build_manifest(candidates)

    if args.write or not args.check:
        write_tree(candidates, manifest)
        print(json.dumps(manifest["designed_relations"], indent=2, sort_keys=True))
        print(f"wrote {len(candidates)} candidates to {C_STAR}")
        return 0

    problems: list[str] = []
    for candidate_id, spec in candidates.items():
        path = C_STAR / candidate_id / "solution.py"
        if not path.is_file():
            problems.append(f"missing {path}")
            continue
        if path.read_text(encoding="utf-8") != spec["source"]:
            problems.append(f"content mismatch: {path}")
    current = C_STAR / "manifest.json"
    if not current.is_file() or json.loads(current.read_text(encoding="utf-8")) != manifest:
        problems.append("manifest.json does not match the builder")
    if problems:
        print("C_STAR mismatch:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(f"C_STAR matches the builder ({len(candidates)} candidates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
