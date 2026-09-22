"""Loading C* and enforcing its integrity before any evaluation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path


class CandidateSetError(RuntimeError):
    """Malformed manifest, missing candidate, or a solution.py whose bytes moved."""


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    path: Path
    solution_sha256: str
    role: str
    kind: str
    note: str = ""
    expected_status: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateSet:
    set_id: str
    manifest_path: Path
    manifest_sha256: str
    base_dir: Path
    candidates: tuple[Candidate, ...]
    designed_relations: dict
    root: dict

    def by_id(self, candidate_id: str) -> Candidate:
        for c in self.candidates:
            if c.candidate_id == candidate_id:
                return c
        raise CandidateSetError(f"{candidate_id!r} is not a member of {self.set_id}")

    def baseline(self, candidate_id: str | None = None) -> Candidate:
        """`c_0` — the C* member the search starts from.

        Two ways to name it, because the two frozen sets name it differently: the
        plumbing set marks exactly one member ``role: "baseline"``, while
        ``C*(T1)`` describes ``c02_ok_low_baseline`` as "the c_0 baseline a search
        must beat" in its purpose text. So a caller may pass the id explicitly,
        and when it does not, the single member with ``role == "baseline"`` is
        used.
        """
        if candidate_id is not None:
            return self.by_id(candidate_id)
        baselines = [c for c in self.candidates if c.role == "baseline"]
        if len(baselines) != 1:
            raise CandidateSetError(
                f"expected exactly one C* member with role=baseline, found {len(baselines)}; "
                f"name the baseline explicitly instead"
            )
        return baselines[0]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_candidate_set(manifest_path: Path) -> CandidateSet:
    manifest_path = Path(manifest_path).resolve()
    if not manifest_path.is_file():
        raise CandidateSetError(f"candidate manifest not found: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    if manifest.get("schema") != "a0.candidateset/v1":
        raise CandidateSetError(f"unexpected candidate-set schema {manifest.get('schema')!r}")
    base_dir = manifest_path.parent
    entries = manifest.get("candidates")
    if not isinstance(entries, list) or not entries:
        raise CandidateSetError("manifest carries no candidates")

    candidates = []
    seen = set()
    for entry in entries:
        for key in ("candidate_id",):
            if key not in entry:
                raise CandidateSetError(f"candidate entry missing {key!r}: {entry!r}")
        candidate_id = entry["candidate_id"]
        if candidate_id in seen:
            raise CandidateSetError(f"duplicate candidate_id {candidate_id!r}")
        seen.add(candidate_id)
        # `path` is the plumbing set's key; `C*(T1)`'s manifest uses `dir`.
        rel = entry.get("path") or entry.get("dir")
        if not rel:
            raise CandidateSetError(f"candidate {candidate_id!r} names no directory")
        candidate_dir = (base_dir / rel).resolve()
        if base_dir not in candidate_dir.parents and candidate_dir != base_dir:
            raise CandidateSetError(f"candidate {candidate_id!r} escapes the manifest dir: {rel}")
        solution = candidate_dir / "solution.py"
        if not solution.is_file():
            raise CandidateSetError(f"candidate {candidate_id!r} has no solution.py at {solution}")
        # Integrity before evaluation: a silently edited candidate invalidates the
        # whole comparison (adapter_contract.md §2.2). Two declarations are
        # accepted, and when the manifest carries a per-file table that table is
        # what is checked — it is the stronger statement.
        actual = sha256_file(solution)
        if entry.get("files"):
            for record in entry["files"]:
                path = candidate_dir / record["path"]
                if not path.is_file():
                    raise CandidateSetError(
                        f"candidate {candidate_id!r} declares {record['path']!r} but it is missing"
                    )
                digest = sha256_file(path)
                if digest != record["sha256"]:
                    raise CandidateSetError(
                        f"candidate {candidate_id!r} {record['path']} sha256 mismatch: "
                        f"declared {record['sha256']} actual {digest}"
                    )
        declared = entry.get("solution_sha256") or entry.get("source_sha256")
        if declared and entry.get("solution_sha256") and actual != declared:
            raise CandidateSetError(
                f"candidate {candidate_id!r} solution.py sha256 mismatch: "
                f"declared {declared} actual {actual}"
            )
        candidates.append(
            Candidate(
                candidate_id=candidate_id,
                path=candidate_dir,
                solution_sha256=actual,
                role=entry.get("role", ""),
                kind=entry.get("kind", ""),
                note=entry.get("note") or entry.get("purpose", ""),
                expected_status=entry.get("expected_status_at_theta_e_star")
                or (entry.get("expected") or {}).get("status"),
                raw=entry,
            )
        )

    declared_count = manifest.get("candidate_count")
    if declared_count is not None and declared_count != len(candidates):
        raise CandidateSetError(
            f"manifest declares candidate_count={declared_count} but lists {len(candidates)}"
        )

    return CandidateSet(
        set_id=manifest.get("candidate_set_id", "C*"),
        manifest_path=manifest_path,
        manifest_sha256=sha256_file(manifest_path),
        base_dir=base_dir,
        candidates=tuple(candidates),
        designed_relations=manifest.get("designed_relations", {}),
        root={k: v for k, v in manifest.items() if k != "candidates"},
    )
