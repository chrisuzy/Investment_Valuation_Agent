"""
Geographic segment resolver — maps CIQ segment labels to Damodaran ERPs.

Resolution layers (applied in order, first match wins):
  1. Exact country match     (case-insensitive) against Damodaran ctryprem
  2. Alias table exact       (curated exact_country_aliases section)
  3. Fuzzy country match     (difflib against Damodaran's 181 countries, confidence ≥ 0.60)
  4. Composite definitions   (broad regions → weighted blend of countries/regions)
  5. Weak defaults           (Rest of World → Global avg)
  6. Unresolved              (→ flagged for user review)

Layer 3 (fuzzy) normalises both sides before comparing:
  - Strip leading articles / governmental prefixes ("The ", "Republic of ", …)
  - ASCII-fold accented characters
  - Remove punctuation other than hyphens and spaces
  - Try difflib SequenceMatcher (ratio) against every Damodaran country name
  - Confidence = ratio; threshold 0.60 minimum (anything below left for user review)

Output per segment:
  {
    raw_name:    "Peoples Republic of China",
    mapped_to:   "China",
    mapped_kind: "country" | "region" | "composite" | "unresolved",
    erp:         float | None,
    members:     list[dict],   # non-empty for composites
    confidence:  float,        # 1.0 = exact; 0.60–0.99 = fuzzy (review recommended)
    source:      "exact_country" | "alias" | "fuzzy_country" | "composite"
                 | "weak_default" | "collapsed" | "unresolved",
    note:        str | None,
  }
"""

from __future__ import annotations

import difflib
import json
import re
import unicodedata
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ALIAS_PATH = _REPO_ROOT / "knowledge_base" / "segment_aliases.json"

_ALIASES_CACHE: dict | None = None
_FUZZY_INDEX_CACHE: dict | None = None   # {normalized_key: canonical_damodaran_name}

# ── Common governmental/article prefixes to strip before fuzzy matching ───────
_STRIP_PREFIXES = [
    "the ", "republic of the ", "republic of ", "democratic republic of the ",
    "democratic republic of ", "people's republic of ", "peoples republic of ",
    "kingdom of the ", "kingdom of ", "state of the ", "state of ",
    "province of ", "autonomous region of ", "special administrative region of ",
    "principality of ", "confederation of ", "federation of ",
]

# ── Suffixes to strip ──────────────────────────────────────────────────────────
_STRIP_SUFFIXES_RE = re.compile(
    r"\s*\((?:excluding|excl\.?|ex\.?|including|incl\.?|and others?|"
    r"and overseas|mainly mainland china|[^()]{1,60})\)\s*$",
    re.IGNORECASE,
)


def _load_aliases() -> dict:
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
    global _ALIASES_CACHE, _FUZZY_INDEX_CACHE
    _ALIASES_CACHE = None
    _FUZZY_INDEX_CACHE = None


def _normalise(s: str) -> str:
    """Normalise a string for fuzzy matching:
    - ASCII-fold accented characters
    - Lowercase
    - Strip governmental prefixes
    - Remove parenthetical suffixes ("(excluding …)", "(AP)", etc.)
    - Collapse punctuation/whitespace
    """
    # ASCII-fold (é→e, ü→u, etc.)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    # Strip parenthetical suffixes before prefix stripping
    s = _STRIP_SUFFIXES_RE.sub("", s).strip()
    # Remove standalone parentheticals
    s = re.sub(r"\([^()]*\)", "", s).strip()
    # Strip leading governmental prefixes (longest first)
    for pfx in sorted(_STRIP_PREFIXES, key=len, reverse=True):
        if s.startswith(pfx):
            s = s[len(pfx):].strip()
            break
    # Normalise punctuation (keep hyphens and spaces)
    s = re.sub(r"[^\w\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _build_fuzzy_index(store) -> dict[str, str]:
    """Build {normalised_name → canonical_damodaran_name} for all Damodaran countries."""
    global _FUZZY_INDEX_CACHE
    if _FUZZY_INDEX_CACHE is not None:
        return _FUZZY_INDEX_CACHE
    idx: dict[str, str] = {}
    for canonical in getattr(store, "_country_risk", {}):
        norm = _normalise(canonical)
        idx[norm] = canonical
    _FUZZY_INDEX_CACHE = idx
    return idx


def _fuzzy_country_match(raw_name: str, store) -> tuple[str, float] | None:
    """Find the best Damodaran country match for raw_name using normalisation + difflib.

    Returns (canonical_damodaran_name, confidence) or None if below threshold.
    Confidence is the difflib ratio (0.0–1.0).
    """
    norm_input = _normalise(raw_name)
    if not norm_input:
        return None
    idx = _build_fuzzy_index(store)
    norm_keys = list(idx.keys())

    # --- exact normalised match first (confidence=0.99) ---
    if norm_input in idx:
        return idx[norm_input], 0.99

    # --- sub-string check: Damodaran name contains the input or vice versa ---
    for norm_key, canonical in idx.items():
        if norm_input == norm_key:
            return canonical, 0.99
        # "england" ⊂ "united kingdom" won't help — skip substring for short terms
        if len(norm_input) >= 5:
            if norm_input in norm_key or norm_key in norm_input:
                ratio = len(min(norm_input, norm_key, key=len)) / len(max(norm_input, norm_key, key=len))
                if ratio >= 0.60:
                    return canonical, round(ratio * 0.90, 3)

    # --- difflib fuzzy ratio ---
    matches = difflib.get_close_matches(norm_input, norm_keys, n=3, cutoff=0.60)
    if not matches:
        return None
    best = matches[0]
    ratio = difflib.SequenceMatcher(None, norm_input, best).ratio()
    return idx[best], round(ratio, 3)


def _follow_alias(key: str, entry: dict, pool: dict) -> tuple[str, dict]:
    while isinstance(entry, dict) and "alias_of" in entry:
        target_key = entry["alias_of"]
        target_entry = pool.get(target_key)
        if target_entry is None:
            break
        key = target_key
        entry = target_entry
    return key, entry


def _get_regional_erp(region_name: str, store) -> float | None:
    from .module_2_risk import _REF
    return _REF.get("regional_erp", {}).get(region_name, {}).get("total_erp")


def _get_country_erp(country_name: str, store) -> float | None:
    raw = getattr(store, "_country_risk", {}).get(country_name)
    if raw is None:
        lower_map = {k.lower(): v for k, v in getattr(store, "_country_risk", {}).items()}
        raw = lower_map.get(country_name.lower())
    if raw is None:
        return None
    erp = raw.get("equity_risk_premium", 0) or 0
    crp = raw.get("country_risk_premium", 0) or 0
    return erp + crp


def _candidate_keys(raw_name: str) -> list[str]:
    """Generate lookup keys covering common cosmetic variations."""
    raw = raw_name.strip()
    lower = raw.lower()
    keys = [lower]
    # Strip parenthetical suffix: "Americas (AG)" → ["americas (ag)", "americas", "ag"]
    m = re.search(r"\(([^()]+)\)\s*$", lower)
    if m:
        keys.append(lower[:m.start()].strip())
        keys.append(m.group(1).strip())
    # Punctuation variants
    keys.append(lower.replace("&", "and"))
    keys.append(lower.replace(" and ", " & "))
    keys.append(lower.replace(",", ""))
    # Dedup preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            ordered.append(k)
    return ordered


def resolve_segment(raw_name: str, store) -> dict:
    """Resolve a single raw segment name to a Damodaran ERP.

    Returns a dict with keys: raw_name, mapped_to, mapped_kind, erp, members,
    confidence, source, note.
    """
    name_stripped = raw_name.strip()
    candidates = _candidate_keys(raw_name)
    aliases = _load_aliases()

    # ── Layer 1: exact country match (case-insensitive) ───────────────────────
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

    # ── Layer 2: alias table exact match ─────────────────────────────────────
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
                    "note": f"Matched via alias table ({raw_name!r} → {alias_target!r})",
                }

    # ── Layer 3: composite definitions ───────────────────────────────────────
    # (Must come BEFORE fuzzy so "Asia", "Americas", "Africa" etc. resolve here)
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
        canonical_key, comp_entry = _follow_alias(matched_key, comp_entry, comp_pool)
        composition = comp_entry.get("composition") or []
        if composition:
            members = []
            total_weight = 0.0
            total_erp = 0.0
            for m in composition:
                kind = m.get("kind", "region")
                to = m.get("to")
                weight = float(m.get("weight", 0))
                mem_erp = _get_country_erp(to, store) if kind == "country" else _get_regional_erp(to, store)
                members.append({"to": to, "kind": kind, "weight": weight, "erp": mem_erp})
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

    # ── Layer 4: weak defaults ────────────────────────────────────────────────
    weak_pool = aliases.get("weak_defaults", {})
    weak_entry = None
    matched_key = None
    for key in candidates:
        ent = weak_pool.get(key)
        if ent:
            weak_entry = ent
            matched_key = key
            break
    if weak_entry:
        canonical_key, weak_entry = _follow_alias(matched_key, weak_entry, weak_pool)
        to_region = weak_entry.get("to", "Global")
        region_erp = _get_regional_erp(to_region, store) if weak_entry.get("kind") == "region" else None
        return {
            "raw_name": raw_name,
            "mapped_to": to_region,
            "mapped_kind": "region",
            "erp": region_erp,
            "members": [],
            "confidence": float(weak_entry.get("confidence", 0.25)),
            "source": "weak_default",
            "note": weak_entry.get("note"),
        }

    # ── Layer 5: fuzzy country match (last resort before unresolved) ─────────
    # Only fires if composites + weak_defaults didn't match.
    # Threshold raised to 0.72 to avoid spurious matches on short strings.
    fuzzy_result = _fuzzy_country_match(name_stripped, store)
    if fuzzy_result is not None:
        fuzzy_country, ratio = fuzzy_result
        erp = _get_country_erp(fuzzy_country, store)
        if erp is not None and ratio >= 0.72:
            confidence = round(ratio * 0.95, 3)
            note = None if ratio >= 0.95 else (
                f"Fuzzy match ({ratio:.0%} similarity) — verify that {raw_name!r} "
                f"refers to {fuzzy_country!r}"
            )
            return {
                "raw_name": raw_name,
                "mapped_to": fuzzy_country,
                "mapped_kind": "country",
                "erp": erp,
                "members": [],
                "confidence": confidence,
                "source": "fuzzy_country",
                "note": note,
            }

    # ── Layer 6: unresolved ───────────────────────────────────────────────────
    return {
        "raw_name": raw_name,
        "mapped_to": None,
        "mapped_kind": "unresolved",
        "erp": None,
        "members": [],
        "confidence": 0.0,
        "source": "unresolved",
        "note": f"No mapping found for {raw_name!r}. Add to knowledge_base/segment_aliases.json.",
    }


def resolve_segments(raw_segments: list[dict], store) -> list[dict]:
    """Resolve a list of {name, revenue, pct} segments.

    Sub-national segments that resolve to the same parent country are collapsed
    into a single entry: revenue is summed, pct is summed, source is "collapsed".
    """
    resolved = []
    for s in raw_segments:
        res = resolve_segment(s["name"], store)
        resolved.append({
            "name": s["name"],
            "revenue": s.get("revenue") or 0.0,
            "pct": s.get("pct", 0.0),
            "resolution": res,
        })

    # Collapse sub-national duplicates (same mapped_to country)
    buckets: dict[str, dict] = {}
    non_country: list[dict] = []
    for item in resolved:
        res = item["resolution"]
        if res.get("mapped_kind") == "country" and res.get("mapped_to"):
            key = res["mapped_to"]
            if key not in buckets:
                buckets[key] = {
                    "name": key,
                    "revenue": 0.0,
                    "pct": 0.0,
                    "resolution": {**res},
                    "_raw_names": [],
                }
            buckets[key]["revenue"] += item["revenue"]
            buckets[key]["pct"] += item["pct"]
            buckets[key]["_raw_names"].append(item["name"])
        else:
            non_country.append(item)

    out: list[dict] = []
    for key, bucket in buckets.items():
        raw_names = bucket.pop("_raw_names")
        if len(raw_names) > 1:
            bucket["resolution"] = {
                **bucket["resolution"],
                "source": "collapsed",
                "note": f"Sub-national labels collapsed: {', '.join(repr(n) for n in raw_names)}",
            }
        elif raw_names and raw_names[0] != key:
            bucket["name"] = raw_names[0]
        out.append(bucket)

    out.extend(non_country)
    return out


def compute_blended_erp(resolved_segments: list[dict]) -> tuple[float | None, list[str]]:
    """Revenue-weighted ERP across resolved segments.

    Excludes unresolved segments and renormalises remaining weights.
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
            warnings.append(
                f"Segment '{s['name']}' ({pct*100:.1f}%) is unresolved — excluded from blend."
            )
            continue
        total_erp += pct * res["erp"]
        total_weight += pct
    if total_weight <= 0:
        return None, warnings + ["No resolvable segments; cannot compute blended ERP."]
    blended = total_erp / total_weight
    if unresolved_pct > 0.01:
        warnings.append(f"Renormalized weights: {unresolved_pct*100:.1f}% of revenue was unresolved.")
    return blended, warnings
