"""
Source Tracker — tracks provenance of every computed/fetched value.

Three detail levels:
1. CIQ fetched → exact formula: =CIQ("SASE:2280","IQ_TOTAL_REV","IQ_FY-0")
2. Calculated → formula expression: = EBIT / Revenues
3. Damodaran reference → file + field: wacc.xls → cost_of_equity
"""

from __future__ import annotations


class SourceTracker:
    """Tracks the source/provenance of every field in the valuation."""

    def __init__(self) -> None:
        self._sources: dict[str, str] = {}

    def record_ciq(self, field_path: str, formula: str) -> None:
        """Record a CIQ-fetched value with its exact formula."""
        self._sources[field_path] = formula

    def record_computed(self, field_path: str, expression: str) -> None:
        """Record a calculated value with its formula expression."""
        self._sources[field_path] = f"= {expression}"

    def record_damodaran(self, field_path: str, file_name: str, field_name: str) -> None:
        """Record a Damodaran reference with file + field."""
        self._sources[field_path] = f"{file_name} → {field_name}"

    def record(self, field_path: str, source: str) -> None:
        """Record an arbitrary source string."""
        self._sources[field_path] = source

    def get(self, field_path: str) -> str | None:
        """Get the source for a field path."""
        return self._sources.get(field_path)

    def to_dict(self) -> dict[str, str]:
        """Export all sources as a plain dict."""
        return dict(self._sources)

    def merge(self, other: SourceTracker) -> None:
        """Merge another tracker's sources into this one."""
        self._sources.update(other._sources)
