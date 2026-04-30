"""
Geographic segment resolver — maps CIQ segment labels to Damodaran ERPs.

Four-layer deterministic resolution:
  1. Exact country match  (case-insensitive) against ctryprem.xlsx
  2. Alias table          (curated in knowledge_base/segment_aliases.json)
  3. Composite expansion  (broad regions → weighted blend of countries/regions)
  4. Weak default         (Rest of World → Global avg) or unresolved (→ user)

Every resolution is deterministic and inspectable. No AI at runtime.
Users can edit `knowledge_base/segment_aliases.json` to extend mappings.

Output per segment:
  SegmentResolution(
    raw_name:  "Europe-Middle East-Africa (EMEA)",
    mapped_to: "EMEA (composite)",
    mapped_kind: "composite",
    erp: 0.0651,          # weighted average of members' ERPs
    members: [
      {to: "Western Europe", kind: "region", weight: 0.55, erp: 0.0516},
      ...
    ],
    confidence: 0.70,
    source: "composite",
  )
"""

from __future__ import annotations

import json
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ALIAS_PATH = _REPO_ROOT / "knowledge_base" / "segment_aliases.json"

_ALIASES_CACHE: dict | None = None


def _load_aliases() -> dict:
    """Load segment aliases from disk; cached after first read."""
    global _ALIASES_CACHE
    if _ALIASES_CACHE is None:
        try:
            with _ALIAS_PATH.open() as f:
                _ALIASES_CACHE = json.load(f)
        except FileNotFoundError:
            _ALIASES_CACHE = {
                "exact_country_aliases": {},
                "composite_definitions": {},
                "weak_defaults": {},
            }
    return _ALIASES_CACHE


def reload_aliases() -> None:
    """Force reload from disk (for use after user edits the JSON)."""
    global _ALIASES_CACHE
    _ALIASES_CACHE = None


def _follow_alias(key: str, entry: dict, pool: dict) -> tuple[str, dict]:
    """If entry is `{"alias_of": ...}`, follow it. Returns (canonical_key, canonical_entry)."""
    while isinstance(entry, dict) and "alias_of" in entry:
        target_key = entry["alias_of"]
        target_entry = pool.get(target_key)
        if target_entry is None:
            break
        key = target_key
        entry = target_entry
    return key, entry


def _get_regional_erp(region_name: str, store) -> float | None:
    """Look up a region's ERP from cost_of_capital_reference.json (regional_erp dict)."""
    # Re-use the ref data loaded by module_2_risk
    from .module_2_risk import _REF
    return _REF.get("regional_erp", {}).get(region_name, {}).get("total_erp")


def _get_country_erp(country_name: str, store) -> float | None:
    """Look up a country's total ERP (base + CRP) from Damodaran's ctryprem dict."""
    raw = getattr(store, "_country_risk", {}).get(country_name)
    if raw is None:
        # Try case-insensitive alias
        lower_map = {k.lower(): v for k, v in getattr(store, "_country_risk", {}).items()}
        raw = lower_map.get(country_name.lower())
    if raw is None:
        return None
    erp = raw.get("equity_risk_premium", 0) or 0
    crp = raw.get("country_risk_premium", 0) or 0
    return erp + crp


def _candidate_keys(raw_name: str) -> list[str]:
    """Generate ordered list of lookup keys to try for a raw segment name.

    Handles common cosmetic variations:
      "Europe-Middle East-Africa (EMEA)" →
          ["europe-middle east-africa (emea)",
           "europe-middle east-africa",
           "emea"]
      "Americas (AG)" → ["americas (ag)", "americas", "ag"]
      "Asia Pacific (AP)" → ["asia pacific (ap)", "asia pacific", "ap"]
    """
    import re
    raw = raw_name.strip()
    lower = raw.lower()
    keys = [lower]
    # Extract any "(...)" suffix
    m = re.search(r"\(([^()]+)\)\s*$", lower)
    if m:
        keys.append(lower[:m.start()].strip())       # "emea" dropped
        keys.append(m.group(1).strip())               # just "emea"
    # Also try common punctuation variants
    keys.append(lower.replace("&", "and"))
    keys.append(lower.replace(" and ", " & "))
    keys.append(lower.replace(",", ""))
    # Dedup preserving order
    seen = set()
    ordered = []
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            ordered.append(k)
    return ordered


def resolve_segment(raw_name: str, store) -> dict:
    """Resolve a single raw segment name to a mapping + ERP.

    Returns a dict matching SegmentResolution schema:
      {
        raw_name: str,
        mapped_to: str,
        mapped_kind: "country" | "region" | "composite" | "unresolved",
        erp: float | None,
        members: list[dict],   # non-empty for composites
        confidence: float,
        source: str,
        note: str | None,
      }
    """
    name_stripped = raw_name.strip()
    candidates = _candidate_keys(raw_name)
    aliases = _load_aliases()

    # ── Layer 1: exact country match ────────────────────────────────
    erp = _get_country_erp(name_stripped, store)
    if erp is not None:
        return {
            "raw_name": raw_name,
            "mapped_to": name_stripped,
            "mapped_kind": "country",
            "erp": erp,
            "members": [],
            "confidence": 1.0,
            "source": "exact_country",
            "note": None,
        }

    # ── Layer 2: alias table (try every candidate key) ──────────────
    alias_map = aliases.get("exact_country_aliases", {})
    for key in candidates:
        alias_target = alias_map.get(key)
        if alias_target:
            erp = _get_country_erp(alias_target, store)
            if erp is not None:
                return {
                    "raw_name": raw_name,
                    "mapped_to": alias_target,
                    "mapped_kind": "country",
                    "erp": erp,
                    "members": [],
                    "confidence": 0.90,
                    "source": "alias",
                    "note": f"Matched via alias table ({raw_name} → {alias_target})",
                }

    # ── Layer 3: composite definitions (try every candidate key) ────
    comp_pool = aliases.get("composite_definitions", {})
    comp_entry = None
    matched_key = None
    for key in candidates:
        ent = comp_pool.get(key)
        if ent:
            comp_entry = ent
            matched_key = key
            break
    if comp_entry:
        name_lower = matched_key  # for alias-follow
        # Follow alias_of indirection
        canonical_key, comp_entry = _follow_alias(name_lower, comp_entry, comp_pool)
        composition = comp_entry.get("composition") or []
        if composition:
            members = []
            total_weight = 0.0
            total_erp = 0.0
            for m in composition:
                kind = m.get("kind", "region")
                to = m.get("to")
                weight = float(m.get("weight", 0))
                if kind == "country":
                    mem_erp = _get_country_erp(to, store)
                else:
                    mem_erp = _get_regional_erp(to, store)
                members.append({
                    "to": to,
                    "kind": kind,
                    "weight": weight,
                    "erp": mem_erp,
                })
                if mem_erp is not None and weight > 0:
                    total_erp += weight * mem_erp
                    total_weight += weight
            blended = (total_erp / total_weight) if total_weight > 0 else None
            return {
                "raw_name": raw_name,
                "mapped_to": comp_entry.get("label") or canonical_key,
                "mapped_kind": "composite",
                "erp": blended,
                "members": members,
                "confidence": float(comp_entry.get("confidence", 0.7)),
                "source": "composite",
                "note": comp_entry.get("note"),
            }

    # ── Layer 4: weak defaults (try every candidate key) ────────────
    weak_pool = aliases.get("weak_defaults", {})
    weak = None
    weak_key = None
    for key in candidates:
        w = weak_pool.get(key)
        if w:
            weak = w
            weak_key = key
            break
    if weak:
        _, weak = _follow_alias(weak_key, weak, weak_pool)
        to = weak.get("to")
        kind = weak.get("kind", "region")
        if to:
            erp = _get_country_erp(to, store) if kind == "country" else _get_regional_erp(to, store)
            return {
                "raw_name": raw_name,
                "mapped_to": to,
                "mapped_kind": kind,
                "erp": erp,
                "members": [],
                "confidence": float(weak.get("confidence", 0.3)),
                "source": "weak_default",
                "note": weak.get("note"),
            }

    # ── Unresolved ──────────────────────────────────────────────────
    return {
        "raw_name": raw_name,
        "mapped_to": None,
        "mapped_kind": "unresolved",
        "erp": None,
        "members": [],
        "confidence": 0.0,
        "source": "unresolved",
        "note": f"No automatic mapping for '{raw_name}'. User must select manually.",
    }


def resolve_segments(raw_segments: list[dict], store) -> list[dict]:
    """Resolve a list of {name, revenue, pct} segments.

    Returns list of {name, revenue, pct, resolution} where resolution is the
    dict produced by resolve_segment().
    """
    out = []
    for s in raw_segments:
        res = resolve_segment(s["name"], store)
        out.append({
            "name": s["name"],
            "revenue": s["revenue"],
            "pct": s.get("pct", 0.0),
            "resolution": res,
        })
    return out


def compute_blended_erp(resolved_segments: list[dict]) -> tuple[float | None, list[str]]:
    """Compute revenue-weighted ERP across resolved segments.

    Handles unresolved segments (excludes them, renormalizes remaining weights).
    Returns (blended_erp, warnings).
    """
    warnings: list[str] = []
    total_weight = 0.0
    total_erp = 0.0
    unresolved_pct = 0.0
    for s in resolved_segments:
        res = s["resolution"]
        pct = s.get("pct", 0.0)
        if res["erp"] is None:
            unresolved_pct += pct
            warnings.append(f"Segment '{s['name']}' ({pct*100:.1f}%) is unresolved — excluded from blend.")
            continue
        total_erp += pct * res["erp"]
        total_weight += pct
    if total_weight <= 0:
        return None, warnings + ["No resolvable segments; cannot compute blended ERP."]
    blended = total_erp / total_weight
    if unresolved_pct > 0.01:
        warnings.append(f"Renormalized weights: {unresolved_pct*100:.1f}% of revenue was unresolved.")
    return blended, warnings
