"""The report branch: "which retained candidate does Loreley report as best?"

The protocol's A0.2 check for Loreley requires asserting that the report branch
points at ``c_1`` after the same-cell replacement (``plan:567``).  In the pinned
checkout the report branch is the primary-objective query inside
``EvolutionScheduler._resolve_best_primary_commit``
(``loreley/scheduler/main.py:876-931``): a ``Metric`` row joined to
``MapElitesArchiveCell`` (archive membership) filtered by island, ordered by
``Metric.value DESC`` for a max primary with tie-break ``commit_hash ASC``, LIMIT 1.

This module runs **that method**, against a real PostgreSQL instance holding the
same rows the ingestion path would have written.  The only seam is the object
construction: ``EvolutionScheduler.__init__`` insists on a writable git
repository, so the instance is allocated with ``__new__`` and the two attributes
the method reads (``settings``, ``_root_commit_hash``) are set directly.  The
method body, the ORM models, the SQL and the session factory are the runtime's
own.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .runtime import FrozenEnvironment, build_settings, ensure_importable

REPORT_SCHEMA = "a0.loreley.report_branch/v1"


@dataclass(slots=True)
class ReportProbe:
    island_id: str
    primary_metric_name: str
    members: Sequence[Mapping[str, Any]]
    best_commit_hash: str | None
    meta: Mapping[str, Any]
    sql_trace: str

    def as_document(self, env: FrozenEnvironment) -> dict[str, Any]:
        return {
            "schema": REPORT_SCHEMA,
            "runtime": "loreley",
            "seam": "EvolutionScheduler.__new__ + settings/_root_commit_hash attributes",
            "real_code": [
                "loreley/scheduler/main.py:876-931 (_resolve_best_primary_commit)",
                "loreley/db/models.py:301-325 (Metric)",
                "loreley/db/models.py:1347-1376 (MapElitesArchiveCell)",
            ],
            "database_url": env.as_dict()["DATABASE_URL"],
            "island_id": self.island_id,
            "primary_metric_name": self.primary_metric_name,
            "archive_members": [dict(item) for item in self.members],
            "resolved_best_commit_hash": self.best_commit_hash,
            "resolved_meta": dict(self.meta),
            "sql": self.sql_trace,
        }


def _connect(env: FrozenEnvironment):
    ensure_importable()
    from loreley.db.base import ensure_database_schema, session_scope

    settings = build_settings(env)
    ensure_database_schema(settings=settings, auto_migrate=True)
    return settings, session_scope


def _clear(session, island_id: str, commit_hashes: Sequence[str]) -> None:
    from sqlalchemy import delete

    from loreley.db.models import CommitCard, MapElitesArchiveCell, Metric

    session.execute(
        delete(Metric).where(
            Metric.commit_card_id.in_(
                session.query(CommitCard.id).filter(CommitCard.commit_hash.in_(tuple(commit_hashes)))
            )
        )
    )
    session.execute(
        delete(MapElitesArchiveCell).where(
            MapElitesArchiveCell.commit_hash.in_(tuple(commit_hashes))
        )
    )
    session.execute(delete(CommitCard).where(CommitCard.commit_hash.in_(tuple(commit_hashes))))
    session.commit()


def probe_report_branch(
    env: FrozenEnvironment,
    *,
    island_id: str,
    members: Sequence[Mapping[str, Any]],
) -> ReportProbe:
    """Write archive rows and ask the runtime's own report query who is best.

    ``members`` entries are ``{"commit_hash", "value", "cell_index",
    "objective_values", "measures"}``.
    """

    ensure_importable()
    from loreley.config import resolve_objective_contract
    from loreley.db.models import CommitCard, MapElitesArchiveCell, Metric
    from loreley.scheduler.main import EvolutionScheduler

    settings, session_scope = _connect(env)
    primary = resolve_objective_contract(settings).primary

    commit_hashes = [str(item["commit_hash"]) for item in members]
    with session_scope() as session:
        _clear(session, island_id, commit_hashes)
        for item in members:
            card = CommitCard(
                id=uuid.uuid4(),
                commit_hash=str(item["commit_hash"]),
                island_id=island_id,
                parent_commit_hash=item.get("parent_commit_hash"),
                author="a0-adapter",
                subject=f"A0 archive probe {item['commit_hash']}",
                change_summary="A0.2 archive probe; rows written by the adapter",
                evaluation_summary=json.dumps(item.get("evaluated_fields") or {}),
            )
            session.add(card)
            session.flush()
            session.add(
                Metric(
                    id=uuid.uuid4(),
                    commit_card_id=card.id,
                    name=primary.name,
                    value=float(item["value"]),
                    unit=getattr(primary, "unit", None),
                    higher_is_better=bool(primary.higher_is_better),
                    details=dict(item.get("details") or {}),
                )
            )
            session.add(
                MapElitesArchiveCell(
                    island_id=island_id,
                    cell_index=int(item["cell_index"]),
                    commit_hash=str(item["commit_hash"]),
                    objective_values=[float(v) for v in item["objective_values"]],
                    measures=[float(v) for v in item["measures"]],
                    timestamp=float(item.get("timestamp") or 0.0),
                )
            )
        session.commit()

    scheduler = EvolutionScheduler.__new__(EvolutionScheduler)
    scheduler.settings = settings
    scheduler._root_commit_hash = None

    best_commit_hash, meta = scheduler._resolve_best_primary_commit()

    statement = (
        "SELECT commit_cards.commit_hash, map_elites_archive_cells.island_id, metrics.value "
        "FROM metrics JOIN commit_cards ON metrics.commit_card_id = commit_cards.id "
        "JOIN map_elites_archive_cells "
        "ON map_elites_archive_cells.commit_hash = commit_cards.commit_hash "
        "WHERE metrics.name = :primary AND map_elites_archive_cells.island_id IN (:island) "
        "ORDER BY metrics.value DESC, commit_cards.commit_hash ASC LIMIT 1"
    )
    return ReportProbe(
        island_id=island_id,
        primary_metric_name=str(primary.name),
        members=members,
        best_commit_hash=best_commit_hash,
        meta=meta,
        sql_trace=statement,
    )
