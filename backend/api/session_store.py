"""In-memory session store for valuation results."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from engine.data_dictionary import CompanyValuationInput
from engine.orchestrator import ValuationReport
from engine.source_tracker import SourceTracker


@dataclass
class Session:
    id: str
    inputs: CompanyValuationInput
    report: ValuationReport
    source_tracker: SourceTracker | None = None
    unresolved_fields: list[dict] = field(default_factory=list)


_sessions: dict[str, Session] = {}


def create_session(
    inputs: CompanyValuationInput,
    report: ValuationReport,
    source_tracker: SourceTracker | None = None,
    unresolved_fields: list[dict] | None = None,
) -> Session:
    sid = uuid.uuid4().hex[:12]
    session = Session(
        id=sid,
        inputs=inputs,
        report=report,
        source_tracker=source_tracker or SourceTracker(),
        unresolved_fields=unresolved_fields or [],
    )
    _sessions[sid] = session
    return session


def get_session(sid: str) -> Session | None:
    return _sessions.get(sid)


def list_sessions() -> list[str]:
    return list(_sessions.keys())
