"""Isolated candidate runner used by E* (`e_star.py`).

This process is the ONLY place candidate code is ever imported.  It performs no
validation and no scoring: it calls `pack_circles(n)` `--runs` times, records the
raw return value of every call plus its wall-clock duration, and writes one
artifact file per run into `--run-dir`.  All judgement is made by the parent
process from those artifacts, which is what keeps a candidate from being able to
monkey-patch the evaluation at runtime.

Artifacts are written with write-to-temp + rename, one file per run, plus a
`child_done.json` marker written only after the last run.  A candidate that
kills this process (os._exit, segfault, hang) therefore leaves an incomplete
artifact set and no done marker, which the parent reports as an evaluation
error rather than as a score.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time

DONE_NAME = "child_done.json"
RUN_TEMPLATE = "run_{index:02d}.json"
MODULE_NAME = "circle_packing_solution"
ENTRY_NAME = "pack_circles"


def _jsonable(value: object) -> object:
    """Keep JSON scalars verbatim; anything else becomes its repr.

    The parent re-coerces with `float()`, mirroring upstream's
    `_coerce_circle`; a repr that happens to parse as a float is accepted there
    exactly as upstream would accept the original object.
    """
    if value is None or isinstance(value, (int, float, bool, str)):
        return value
    return repr(value)


def _materialize(raw: object) -> tuple[list[object], int]:
    """Turn the candidate's return value into a JSON-able list of entries."""
    entries = list(raw)  # type: ignore[call-overload]
    out: list[object] = []
    for entry in entries:
        try:
            sequence = list(entry)  # type: ignore[call-overload]
        except TypeError:
            out.append(_jsonable(entry))
            continue
        out.append([_jsonable(value) for value in sequence])
    return out, len(entries)


def _write(path: str, payload: object) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, allow_nan=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="E* isolated candidate runner.")
    parser.add_argument("--solution", required=True)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--runs", type=int, required=True)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args(argv)

    run_dir = os.path.abspath(args.run_dir)
    done = {
        "runs_requested": int(args.runs),
        "runs_written": 0,
        "import_error": None,
        "entry_error": None,
        "entry_type": None,
    }

    spec = importlib.util.spec_from_file_location(MODULE_NAME, args.solution)
    if spec is None or spec.loader is None:
        done["import_error"] = f"could not create an import spec for {args.solution!r}"
        _write(os.path.join(run_dir, DONE_NAME), done)
        return 0

    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except BaseException as exc:  # noqa: BLE001 - a candidate may raise anything
        sys.modules.pop(MODULE_NAME, None)
        done["import_error"] = f"{type(exc).__name__}: {exc}"
        _write(os.path.join(run_dir, DONE_NAME), done)
        return 0

    entry = getattr(module, ENTRY_NAME, None)
    done["entry_type"] = type(entry).__name__
    if not callable(entry):
        done["entry_error"] = f"module does not define a callable {ENTRY_NAME!r}"
        _write(os.path.join(run_dir, DONE_NAME), done)
        return 0

    for index in range(int(args.runs)):
        record: dict[str, object] = {"run": index, "error": None, "value": None, "length": None}
        started = time.perf_counter()
        try:
            raw = entry(args.n)
            value, length = _materialize(raw)
            record["value"] = value
            record["length"] = length
        except BaseException as exc:  # noqa: BLE001 - a candidate may raise anything
            record["error"] = f"{type(exc).__name__}: {exc}"
        record["duration_s"] = time.perf_counter() - started
        _write(os.path.join(run_dir, RUN_TEMPLATE.format(index=index)), record)
        done["runs_written"] = index + 1

    _write(os.path.join(run_dir, DONE_NAME), done)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
