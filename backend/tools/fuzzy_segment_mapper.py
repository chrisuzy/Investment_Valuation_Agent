"""
tools/fuzzy_segment_mapper.py

Standards-first fuzzy mapper from raw CIQ geographic-segment labels to
Aswath Damodaran's ERP taxonomy (181 countries + 10 regions).

Design:
  - Damodaran's taxonomy is the ONLY target (no sub-national granularity)
  - ISO 3166-1/3166-2 via pycountry anchors country + subdivision recognition
  - Sub-national segments (Chinese provinces, Indian states, etc.) collapse to parent country
  - A small embedded dict handles Chinese regions and jargon not in ISO
  - difflib is the last-resort fuzzy layer (threshold 0.80)

Usage:
  python -m tools.fuzzy_segment_mapper                       # full-DB audit
  python -m tools.fuzzy_segment_mapper --sample 100          # random 100 companies
  python -m tools.fuzzy_segment_mapper --sample 100 --seed 7 # reproducible sample
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pycountry  # type: ignore

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from data_sources.damodaran_store import DamodaranStore  # noqa: E402
from engine.module_2_risk import _REF  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Normalisation
# ─────────────────────────────────────────────────────────────────────────────
_STRIP_PREFIXES = (
    "the ", "republic of the ", "republic of ", "democratic republic of the ",
    "democratic republic of ", "people's republic of ", "peoples republic of ",
    "kingdom of the ", "kingdom of ", "state of the ", "state of ",
    "province of ", "autonomous region of ", "special administrative region of ",
    "principality of ", "federation of ", "commonwealth of ",
)
# Subdivision suffixes to strip from ISO 3166-2 names / raw segments
# (Chinese: sheng/shi/zizhiqu; Japanese: prefecture; generic: province/state)
_CN_SUBDIV_SUFFIXES = (
    " sheng", " shi", " zizhiqu", " tebiexingzhengqu",
    " province", " prefecture", " municipality", " autonomous region",
    " special administrative region", " sar", " state", " region",
    " territory", " oblast", " krai",
)
# "Other X" / "Rest of X" prefixes — strip and retry
_OTHER_REST_PREFIXES = (
    "other ", "others ", "rest of ", "rest of the ", "all other ",
    "remaining ", "remainder of ",
)
_PAREN_RE = re.compile(r"\s*\([^()]*\)\s*")


def _normalise(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # Normalise typographic apostrophes, hyphens, and slashes
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("–", "-").replace("—", "-")
    s = s.lower().strip()
    s = _PAREN_RE.sub(" ", s).strip()
    # Treat hyphens as word separators so "north-west" == "north west"
    s = s.replace("-", " ")
    # Handle comma-inverted ISO names: "Korea, Republic of" → "Korea"
    # "Iran, Islamic Republic of" → "Iran". Take the segment before the first comma
    # if what follows looks like a descriptor (starts with a stripped prefix).
    if "," in s:
        head, tail = s.split(",", 1)
        tail = tail.strip()
        if any(tail.startswith(p.strip()) for p in _STRIP_PREFIXES) or tail in ("republic of", "province of china", "d.p.r.", "dpr"):
            s = head.strip()
    # Drop apostrophes entirely so "People's" → "Peoples" (matches strip prefix)
    s = s.replace("'", "")
    # Iteratively strip prefixes until no match (handles "The Republic of Korea")
    sorted_pfx = sorted(_STRIP_PREFIXES, key=len, reverse=True)
    changed = True
    while changed:
        changed = False
        for pfx in sorted_pfx:
            if s.startswith(pfx):
                s = s[len(pfx):].strip()
                changed = True
                break
    s = re.sub(r"[^\w\s\-/&]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Damodaran region canonical names
# ─────────────────────────────────────────────────────────────────────────────
DAMODARAN_REGIONS = {
    "Africa", "Asia", "Australia & New Zealand", "Caribbean",
    "Central and South America", "Eastern Europe", "Global",
    "Middle East", "North America", "Western Europe",
}

# Region-level aliases → Damodaran region name
_REGION_ALIASES = {
    # Asia variants
    "asia": "Asia",
    "asia pacific": "Asia",
    "asia-pacific": "Asia",
    "asia/pacific": "Asia",
    "asia pac": "Asia",
    "apac": "Asia",
    "ap": "Asia",
    "far east": "Asia",
    "east asia": "Asia",
    "south asia": "Asia",
    "southeast asia": "Asia",
    "south east asia": "Asia",
    "south-east asia": "Asia",
    "southeastern asia": "Asia",
    "asean": "Asia",
    "north asia": "Asia",
    "northeast asia": "Asia",
    "central asia": "Asia",
    "western asia": "Asia",
    "asia and oceania": "Asia",
    "asia oceania": "Asia",
    "asia/oceania": "Asia",
    "asia & oceania": "Asia",
    "asia and others": "Asia",
    "asia and pacific": "Asia",
    "asia/pacific region": "Asia",
    "asia-pacific region": "Asia",
    "rest of asia": "Asia",
    "rest of asia pacific": "Asia",
    "rest of apac": "Asia",
    "other asia": "Asia",
    "other asia pacific": "Asia",
    "other asia-pacific": "Asia",
    "greater asia": "Asia",
    # Europe variants (default to Western Europe per Damodaran default)
    "europe": "Western Europe",
    "european": "Western Europe",
    "europe union": "Western Europe",
    "european union": "Western Europe",
    "eu": "Western Europe",
    "eu countries": "Western Europe",
    "eurozone": "Western Europe",
    "euro zone": "Western Europe",
    "euro area": "Western Europe",
    "western europe": "Western Europe",
    "northern europe": "Western Europe",
    "southern europe": "Western Europe",
    "central europe": "Western Europe",
    "nordic": "Western Europe",
    "nordics": "Western Europe",
    "nordic countries": "Western Europe",
    "scandinavia": "Western Europe",
    "benelux": "Western Europe",
    "dach": "Western Europe",
    "iberia": "Western Europe",
    "rest of europe": "Western Europe",
    "other europe": "Western Europe",
    "other eu": "Western Europe",
    "other eu countries": "Western Europe",
    "other european union": "Western Europe",
    "other european union countries": "Western Europe",
    "european region": "Western Europe",
    "european countries": "Western Europe",
    "eu and efta": "Western Europe",
    "efta": "Western Europe",
    # Eastern Europe
    "eastern europe": "Eastern Europe",
    "central and eastern europe": "Eastern Europe",
    "cee": "Eastern Europe",
    "cis": "Eastern Europe",
    "former soviet union": "Eastern Europe",
    "balkans": "Eastern Europe",
    "baltic": "Eastern Europe",
    "baltics": "Eastern Europe",
    "baltic countries": "Eastern Europe",
    # Americas
    "americas": "North America",
    "north america": "North America",
    "northern america": "North America",
    "na": "North America",
    "rest of americas": "North America",
    "other americas": "North America",
    "other america": "North America",
    "latin america": "Central and South America",
    "latam": "Central and South America",
    "south america": "Central and South America",
    "central america": "Central and South America",
    "central and south america": "Central and South America",
    "south and central america": "Central and South America",
    "north and central america": "North America",
    "other latin america": "Central and South America",
    "rest of latin america": "Central and South America",
    "caribbean": "Caribbean",
    # Africa
    "africa": "Africa",
    "sub-saharan africa": "Africa",
    "sub saharan africa": "Africa",
    "north africa": "Africa",
    "northern africa": "Africa",
    "west africa": "Africa",
    "east africa": "Africa",
    "southern africa": "Africa",
    "rest of africa": "Africa",
    "other africa": "Africa",
    # Middle East
    "middle east": "Middle East",
    "mideast": "Middle East",
    "gulf": "Middle East",
    "gcc": "Middle East",
    "levant": "Middle East",
    "other middle east": "Middle East",
    "rest of middle east": "Middle East",
    # Australia/Oceania
    "oceania": "Australia & New Zealand",
    "australasia": "Australia & New Zealand",
    "anz": "Australia & New Zealand",
    "australia new zealand": "Australia & New Zealand",
    "australia/new zealand": "Australia & New Zealand",
    "australia & new zealand": "Australia & New Zealand",
    "australia and new zealand": "Australia & New Zealand",
    "pacific": "Australia & New Zealand",
    # Catch-all / weak defaults → Global
    "global": "Global",
    "worldwide": "Global",
    "international": "Global",
    "rest of world": "Global",
    "rest of the world": "Global",
    "row": "Global",
    "other": "Global",
    "others": "Global",
    "all other": "Global",
    "all others": "Global",
    "unallocated": "Global",
    "corporate": "Global",
    "corporate and other": "Global",
    "head office": "Global",
    "eliminations": "Global",
    "other countries": "Global",
    "other countries and regions": "Global",
    "other regions": "Global",
    "other region": "Global",
    "other locations": "Global",
    "other areas": "Global",
    "other area": "Global",
    "third countries": "Global",
    "foreign": "Global",
    "overseas": "Global",
    "overseas regions": "Global",
    "export": "Global",
    "exports": "Global",
    "other export": "Global",
    "other international countries": "Global",
    "other continents": "Global",
    "elsewhere in the world": "Global",
    "emerging markets": "Global",
    "emerging": "Global",
    "developed markets": "Global",
    # Composites (mapped to dominant Damodaran region)
    "emea": "Western Europe",  # EMEA dominant region by market cap
    "europe middle east and africa": "Western Europe",
    "europe the middle east and africa": "Western Europe",
    "europe and middle east": "Western Europe",
    "europe and africa": "Western Europe",
    "europe and the middle east": "Western Europe",
    "europe middle east africa": "Western Europe",
    "europe/middle east/africa": "Western Europe",
    "europe / middle east / africa": "Western Europe",
    "other emea": "Western Europe",
    "rest of emea": "Western Europe",
    "africa and middle east": "Middle East",
    "middle east and africa": "Middle East",
    "middle east/africa": "Middle East",
    "africa & middle east": "Middle East",
    "africa and others": "Africa",
    "africa and asia": "Africa",
    "mena": "Middle East",
    "uk and ireland": "Western Europe",
    "uk & ireland": "Western Europe",
    "uk & europe": "Western Europe",
    "united kingdom and europe": "Western Europe",
    # Chinese mainland-only aliases (sub-national → China; multi-entity uses split)
    "mainland china": "China",
    "china mainland": "China",
    "prc": "China",
    "prc except hong kong": "China",
    "the prc excluding hong kong": "China",
    "china and others": "China",
    "hong kong china": "Hong Kong",      # disambiguator suffix
    "hong kong, china": "Hong Kong",     # disambiguator suffix
    "taiwan china": "Taiwan",            # disambiguator suffix
    "taiwan, china": "Taiwan",           # disambiguator suffix
    "taiwan province of china": "Taiwan",
    # Chinese regions (all → China per user: no sub-national)
    "eastern china": "China",
    "western china": "China",
    "southern china": "China",
    "northern china": "China",
    "central china": "China",
    "northeast china": "China",
    "northwest china": "China",
    "southwest china": "China",
    "southeast china": "China",
    "north china": "China",
    "south china": "China",
    "east china": "China",
    "west china": "China",
    "south central china": "China",
    "central south china": "China",
    "south central china region": "China",
    "north east china": "China",
    "north west china": "China",
    "south west china": "China",
    "south east china": "China",
    "huadong region": "China",
    "huanan region": "China",
    "huabei region": "China",
    "huazhong region": "China",
    "dongbei region": "China",
    "xinan region": "China",
    "xibei region": "China",
    "pearl river delta": "China",
    "yangtze river delta": "China",
    "bohai rim": "China",
    "other china": "China",
    "rest of china": "China",
    "mainland china region": "China",
    "beijing area": "China",
    "shanghai area": "China",
    "guangdong province": "China",
    "northeast district": "China",
    # USA variants
    "u.s.": "United States",
    "us": "United States",
    "usa": "United States",
    "u.s.a": "United States",
    "u.s.a.": "United States",
    "united states of america": "United States",
    "america": "United States",
    "the us": "United States",
    "the united states": "United States",
    # Complement patterns ("not X" / "outside X") → Global
    "non-us": "Global",
    "non-u.s.": "Global",
    "non us": "Global",
    "non united states": "Global",
    "outside united states": "Global",
    "outside of the united states": "Global",
    "outside the united states": "Global",
    "americas excluding united states": "Global",
    "americas excl united states": "Global",
    "americas excl. united states": "Global",
    "non-united states": "Global",
    "north america excluding united states": "Global",
    "all other foreign countries": "Global",
    "other foreign countries": "Global",
    "non-eu": "Global",
    "non-eu countries": "Global",
    "non-european union": "Global",
    "outside eu": "Global",
    "outside the eu": "Global",
    "outside europe": "Global",
    "europe excluding germany": "Global",
    "europe excluding france": "Global",
    "non-euro zone": "Global",
    "outside indonesia": "Global",
    "other country": "Global",
    "other items": "Global",
    "outside of the mainland of china countries and regions": "Global",
    # Specific domain: UK/GB
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "great britain": "United Kingdom",
    "england": "United Kingdom",
    "scotland": "United Kingdom",
    "wales": "United Kingdom",
    "northern ireland": "United Kingdom",
    "britain": "United Kingdom",
    # Damodaran-specific spelling overrides (pycountry uses a different form)
    "south korea": "Korea",
    "korea": "Korea",
    "republic of korea": "Korea",
    "korea republic": "Korea",
    "north korea": "Korea, D.P.R.",
    "dpr korea": "Korea, D.P.R.",
    "macau": "Macao",
    "macao": "Macao",
    "macao sar": "Macao",
    "macau sar": "Macao",
    "macau china": "Macao",
    "dutch antilles": "Aruba",  # closest Damodaran proxy (Netherlands Antilles dissolved 2010)
    "netherlands antilles": "Aruba",
    # Chinese autonomous regions — pycountry uses compound names ("Xinjiang Uygur Zizhiqu")
    "xinjiang": "China",
    "tibet": "China",
    "inner mongolia": "China",
    "ningxia": "China",
    "guangxi": "China",
    # Additional China composites discovered during evaluation
    "chinese mainland": "China",
    "northwestern china": "China",
    "northeastern china": "China",
    "southwestern china": "China",
    "southeastern china": "China",
    "continental china": "China",
    # Regions (discovered during evaluation)
    "continental europe": "Western Europe",
    "other asian countries": "Asia",
    "other asian country": "Asia",
    # UAE variants (Damodaran uses "United Arab Emirates")
    "uae": "United Arab Emirates",
    "u.a.e.": "United Arab Emirates",
    "u a e": "United Arab Emirates",
    # Dubai/Abu Dhabi (Damodaran has "Abu Dhabi" as a country, Dubai as part of UAE)
    "dubai": "United Arab Emirates",
    # UK variants
    "u.k.": "United Kingdom",
    "u k": "United Kingdom",
    # BVI — Damodaran has no entry; use Caribbean region
    "british virgin islands": "Caribbean",
    "bvi": "Caribbean",
    # Additional complement / region-label cleanup
    "outside china": "Global",
    "outside mainland china": "Global",
    "outside the mainland of china countries and regions": "Global",
    "other markets": "Global",
    "other countries/regions": "Global",
    "other countries or regions": "Global",
    # ISO-vs-Damodaran divergences (ISO modern names; Damodaran traditional)
    "turkiye": "Turkey",
    "czechia": "Czech Republic",
    "cote divoire": "Côte d'Ivoire",
    "cote d ivoire": "Côte d'Ivoire",
    "ivory coast": "Côte d'Ivoire",
    "north macedonia": "Macedonia",
    "republic of north macedonia": "Macedonia",
    "cabo verde": "Cape Verde",
    "eswatini": "Swaziland",
    "kingdom of eswatini": "Swaziland",
    "timor-leste": "East Timor",
    "timor leste": "East Timor",
    "burma": "Myanmar",
    # Colloquial country names
    "holland": "Netherlands",
    # ISO 3166-1 countries not in Damodaran — map to nearest regional proxy
    "bhutan": "India",           # geographic/economic neighbor
    "oversea": "Global",         # typo of "overseas"
    # Greater China composite — default to China (dominant component)
    "greater china": "China",
    # Greenland (Danish territory) — Damodaran has no entry
    "greenland": "Denmark",
    # Internal region codes with no country context → Global (user can override)
    "southwest region": "Global",
    "southeast region": "Global",
    "northwest region": "Global",
    "northeast region": "Global",
    "southern region": "Global",
    "northern region": "Global",
    "western region": "Global",
    "eastern region": "Global",
    "central region": "Global",
    "north east area": "Global",
    "north west area": "Global",
    "south east area": "Global",
    "south west area": "Global",
    "northwest district": "Global",
    "northeast district": "Global",
    # North Sea (oil & gas jargon) → Western Europe
    "north sea": "Western Europe",
    "european union countries": "Western Europe",
    "central south": "Global",
    "central south region": "Global",
    "mainland": "Global",
    "other american countries": "North America",
    "asia and africa": "Asia",
    "asia and the middle east": "Asia",
    "asia and latin america": "Asia",
    "asia latin america and oceania": "Asia",
    "china north asia and oceania": "Asia",
    # Small country long-tail
    "cayman": "Cayman Islands",
    "cayman island": "Cayman Islands",
    "monaco": "Monaco",
    "kosovo": "Serbia",  # Damodaran has no Kosovo; Serbia is the nearest proxy
    "gibraltar": "United Kingdom",
    "international markets": "Global",
    "new markets": "Global",
    "other areas in china": "China",
    "other asia countries": "Asia",
    "other asia country": "Asia",
    "other emea countries": "Western Europe",
    "other emea country": "Western Europe",
    "other than india": "Global",
    "other countries of the european union": "Western Europe",
    # Complement / catch-all additions from eval
    "abroad": "Global",
    "foreign countries": "Global",
    "foreign country": "Global",
    "all other countries": "Global",
    "all other foreign countries": "Global",
    "regions outside mainland china": "Global",
    "out of india": "Global",
    "outside india": "Global",
    "africa and oceania": "Africa",
    "africa & oceania": "Africa",
    "far east pacific": "Asia",
    "far east/pacific": "Asia",
    "china & hong kong": "China",
    "north-west region": "Global",  # not a real geography
    "northwest region": "Global",
    "north west region": "Global",
}


# ─────────────────────────────────────────────────────────────────────────────
# Indices (built once)
# ─────────────────────────────────────────────────────────────────────────────
def build_indices(store: DamodaranStore) -> dict:
    """Build normalized → Damodaran-target lookups from pycountry and Damodaran."""
    damo_countries = set(store._country_risk.keys())

    # ISO 3166-1 country variants → Damodaran canonical (if present)
    country_idx: dict[str, str] = {}
    iso_to_damo: dict[str, str] = {}  # alpha_2 → Damodaran name

    def _add(norm_key: str, damo_name: str) -> None:
        if not norm_key:
            return
        country_idx.setdefault(norm_key, damo_name)

    # Seed with Damodaran's own 181 names
    for damo_name in damo_countries:
        _add(_normalise(damo_name), damo_name)

    for c in pycountry.countries:
        # Match this ISO country to a Damodaran name
        candidates = [c.name]
        for attr in ("official_name", "common_name"):
            v = getattr(c, attr, None)
            if v:
                candidates.append(v)
        # Try each to find a Damodaran country
        damo_match = None
        for cand in candidates:
            if cand in damo_countries:
                damo_match = cand
                break
            norm = _normalise(cand)
            if norm in country_idx:
                damo_match = country_idx[norm]
                break
        if damo_match is None:
            # Try normalised match across damo_countries
            for damo in damo_countries:
                if _normalise(damo) == _normalise(c.name):
                    damo_match = damo
                    break
        if damo_match is None:
            continue  # country not tracked by Damodaran — skip
        iso_to_damo[c.alpha_2] = damo_match
        for cand in candidates:
            _add(_normalise(cand), damo_match)
        # Add alpha_2 and alpha_3 as keys (rare but possible: "US", "USA")
        _add(c.alpha_2.lower(), damo_match)
        _add(c.alpha_3.lower(), damo_match)

    # ISO 3166-2 subdivisions → parent country (via iso_to_damo)
    for sub in pycountry.subdivisions:
        damo_parent = iso_to_damo.get(sub.country_code)
        if damo_parent is None:
            continue
        _add(_normalise(sub.name), damo_parent)
        # Strip Chinese / admin suffixes and add
        norm = _normalise(sub.name)
        for suf in _CN_SUBDIV_SUFFIXES:
            if norm.endswith(suf):
                _add(norm[: -len(suf)].strip(), damo_parent)
                break

    # Region aliases overlay (highest precedence for exact-match region labels)
    region_idx: dict[str, str] = {}
    for k, v in _REGION_ALIASES.items():
        # v may be a country name too (e.g., "China", "United States")
        region_idx[_normalise(k)] = v

    # Build fuzzy candidate lists
    country_norm_keys = list(country_idx.keys())
    region_names_norm = {_normalise(r): r for r in DAMODARAN_REGIONS}

    return {
        "country_idx": country_idx,
        "region_idx": region_idx,
        "iso_to_damo": iso_to_damo,
        "damo_countries": damo_countries,
        "country_norm_keys": country_norm_keys,
        "region_names_norm": region_names_norm,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Single-segment resolver
# ─────────────────────────────────────────────────────────────────────────────
def map_segment(raw_name: str, idx: dict) -> dict:
    """Map one raw segment label to a Damodaran country or region.

    Returns: {raw_name, target, kind, confidence, source}
      target   = Damodaran country name, Damodaran region name, or None
      kind     = "country" | "region" | "unresolved"
      source   = "exact_country" | "country_alias" | "subdivision"
                 | "region_alias" | "fuzzy_country" | "unresolved"
    """
    norm = _normalise(raw_name)
    if not norm:
        return {"raw_name": raw_name, "target": None, "kind": "unresolved",
                "confidence": 0.0, "source": "unresolved"}

    # Layer 1: region alias (catch-all terms, composites, collapsed sub-nationals)
    if norm in idx["region_idx"]:
        tgt = idx["region_idx"][norm]
        kind = "region" if tgt in DAMODARAN_REGIONS or tgt == "Global" else "country"
        return {"raw_name": raw_name, "target": tgt, "kind": kind,
                "confidence": 0.95, "source": "region_alias"}

    # Layer 2: country (ISO / pycountry + Damodaran seed + subdivisions)
    if norm in idx["country_idx"]:
        tgt = idx["country_idx"][norm]
        # Detect whether this was a direct Damodaran match vs alias
        src = "exact_country" if _normalise(tgt) == norm else "country_alias"
        return {"raw_name": raw_name, "target": tgt, "kind": "country",
                "confidence": 1.0 if src == "exact_country" else 0.95,
                "source": src}

    # Layer 2.5: "Other X" / "Rest of X" — strip prefix and retry (recurse once via _normalise)
    for pfx in sorted(_OTHER_REST_PREFIXES, key=len, reverse=True):
        if norm.startswith(pfx):
            inner = _normalise(norm[len(pfx):])
            if inner in idx["region_idx"]:
                tgt = idx["region_idx"][inner]
                kind = "region" if tgt in DAMODARAN_REGIONS or tgt == "Global" else "country"
                return {"raw_name": raw_name, "target": tgt, "kind": kind,
                        "confidence": 0.90, "source": "other_prefix"}
            if inner in idx["country_idx"]:
                tgt = idx["country_idx"][inner]
                return {"raw_name": raw_name, "target": tgt, "kind": "country",
                        "confidence": 0.90, "source": "other_prefix"}
            break  # only strip one prefix layer

    # Layer 2.6: subdivision suffix strip (e.g. "Aomori Prefecture" → "aomori")
    for suf in _CN_SUBDIV_SUFFIXES:
        if norm.endswith(suf):
            inner = norm[: -len(suf)].strip()
            if inner in idx["country_idx"]:
                tgt = idx["country_idx"][inner]
                return {"raw_name": raw_name, "target": tgt, "kind": "country",
                        "confidence": 0.95, "source": "subdivision"}
            if inner in idx["region_idx"]:
                tgt = idx["region_idx"][inner]
                kind = "region" if tgt in DAMODARAN_REGIONS or tgt == "Global" else "country"
                return {"raw_name": raw_name, "target": tgt, "kind": kind,
                        "confidence": 0.90, "source": "subdivision"}
            break

    # Layer 3: fuzzy against Damodaran country names (0.80 threshold)
    matches = difflib.get_close_matches(norm, idx["country_norm_keys"], n=1, cutoff=0.80)
    if matches:
        best = matches[0]
        ratio = difflib.SequenceMatcher(None, norm, best).ratio()
        if ratio >= 0.85:
            return {"raw_name": raw_name, "target": idx["country_idx"][best],
                    "kind": "country", "confidence": round(ratio, 3),
                    "source": "fuzzy_country"}

    # Layer 4: fuzzy against Damodaran region names
    region_matches = difflib.get_close_matches(
        norm, list(idx["region_names_norm"].keys()), n=1, cutoff=0.80
    )
    if region_matches:
        ratio = difflib.SequenceMatcher(None, norm, region_matches[0]).ratio()
        if ratio >= 0.85:
            return {"raw_name": raw_name,
                    "target": idx["region_names_norm"][region_matches[0]],
                    "kind": "region", "confidence": round(ratio, 3),
                    "source": "fuzzy_region"}

    # Layer 7: keyword-based weak default (always succeeds)
    target, reason = _weak_default_target(norm)
    return {"raw_name": raw_name, "target": target,
            "kind": "region" if target in DAMODARAN_REGIONS or target == "Global" else "country",
            "confidence": 0.30, "source": "weak_default",
            "red_flag": True, "note": reason}


def _weak_default_target(norm: str) -> tuple[str, str]:
    """Keyword-heuristic fallback. Guarantees a Damodaran target for any input.

    Returns (target, human-readable reason). Every result should be red-flagged
    in the UI so the user knows this wasn't a clean match.
    """
    # EMEA composite — dominant region is Western Europe (largest by market cap)
    if "emea" in norm:
        return "Western Europe", "Weak default: EMEA blend — defaulted to Western Europe"
    # Europe substring
    if "europe" in norm or "european" in norm or "eu " in f" {norm} " or f" {norm} ".endswith(" eu "):
        if any(k in norm for k in ("eastern", "cee", "cis", "balkan", "baltic")):
            return "Eastern Europe", "Weak default: European label with eastern hint"
        return "Western Europe", "Weak default: European label — defaulted to Western Europe"
    # Asia substring
    if "asia" in norm or "apac" in norm or "orient" in norm or "asean" in norm:
        return "Asia", "Weak default: Asian label"
    # Middle East
    if "middle east" in norm or "mideast" in norm or "mena" in norm or "gulf" in norm or "arab" in norm:
        return "Middle East", "Weak default: Middle East label"
    # Africa
    if "africa" in norm:
        return "Africa", "Weak default: African label"
    # Americas
    if "america" in norm or "latam" in norm:
        if any(k in norm for k in ("latin", "south", "central", "brazil", "mexico", "argentina", "chile")):
            return "Central and South America", "Weak default: Latin/South/Central America label"
        if "caribbean" in norm or "antilles" in norm or "indies" in norm:
            return "Caribbean", "Weak default: Caribbean label"
        return "North America", "Weak default: Americas label — defaulted to North America"
    # Pacific / Oceania
    if "pacific" in norm or "oceania" in norm or "australas" in norm:
        return "Australia & New Zealand", "Weak default: Pacific/Oceania label"
    # Chinese hints (city / province / region keywords without specific name)
    if "china" in norm or "chinese" in norm or "prc" in norm:
        return "China", "Weak default: China label"
    # No geographic signal — use Global average
    return "Global", "Weak default: no geographic keyword detected — using Global average"


_SPLIT_RE = re.compile(r"\s*[/,&+]\s*|\s+and\s+")


def try_split(raw_name: str, idx: dict) -> list[dict] | None:
    """If raw_name contains separators and ALL pieces resolve cleanly, return list.

    'Cleanly' = not via weak_default. If any piece would fall back to weak_default,
    we prefer to treat the whole string as one weak_default (more informative).
    """
    parts = [p.strip() for p in _SPLIT_RE.split(raw_name) if p.strip()]
    if len(parts) < 2:
        return None
    results = []
    for p in parts:
        res = map_segment(p, idx)
        if res.get("source") == "weak_default":
            return None  # bail — whole-string weak_default is more informative
        results.append(res)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Sub-national collapse at the company level
# ─────────────────────────────────────────────────────────────────────────────
def resolve_company_segments(segments: list[dict], idx: dict) -> list[dict]:
    """Resolve all segments for one company and collapse to Damodaran targets.

    Input:  [{"name": "Shanghai", "revenue": 100, "pct": 0.3}, ...]
    Output: [{"target": "China", "revenue": 100, "pct": 0.3,
              "raw_names": ["Shanghai", "Guangdong"], "confidence": 1.0,
              "source": "subdivision_collapsed"}]
    """
    bucketed: dict[str, dict] = {}
    per_segment: list[dict] = []  # flat record for reporting

    def _deposit(target: str, kind: str, source: str, confidence: float,
                 raw_name: str, revenue: float, pct: float,
                 red_flag: bool = False, note: str | None = None) -> None:
        b = bucketed.setdefault(target, {
            "target": target, "kind": kind,
            "revenue": 0.0, "pct": 0.0,
            "raw_names": [], "confidence_min": confidence, "source": source,
            "red_flag": red_flag, "notes": [],
        })
        b["revenue"] += revenue
        b["pct"] += pct
        b["raw_names"].append(raw_name)
        b["confidence_min"] = min(b["confidence_min"], confidence)
        if red_flag:
            b["red_flag"] = True
        if note and note not in b["notes"]:
            b["notes"].append(note)
        if len(b["raw_names"]) > 1 and b["source"] != "collapsed":
            b["source"] = "collapsed"
        per_segment.append({"raw_name": raw_name, "target": target,
                            "source": source, "red_flag": red_flag,
                            "revenue": revenue, "pct": pct})

    for s in segments:
        name = (s.get("name") or "").strip()
        if not name:
            continue
        revenue = s.get("revenue") or 0.0
        pct = s.get("pct") or 0.0
        # Prefer split if possible (but only when all pieces resolve cleanly)
        split_results = try_split(name, idx)
        if split_results:
            n = len(split_results)
            per_rev = revenue / n
            per_pct = pct / n
            for r in split_results:
                _deposit(r["target"], r["kind"], "split",
                         r["confidence"] * 0.9, name, per_rev, per_pct,
                         red_flag=False)
            continue
        res = map_segment(name, idx)
        _deposit(res["target"], res["kind"], res["source"],
                 res["confidence"], name, revenue, pct,
                 red_flag=res.get("red_flag", False),
                 note=res.get("note"))

    return list(bucketed.values()), per_segment


# ─────────────────────────────────────────────────────────────────────────────
# DB iteration + reporting
# ─────────────────────────────────────────────────────────────────────────────
def iter_companies(db_path: str, limit: int | None = None,
                   sample: int | None = None, seed: int | None = None):
    """Yield (ticker, segments_list) for every company with segment data."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    q = ("SELECT ticker, geographic_segments_json FROM companies "
         "WHERE geographic_segments_json IS NOT NULL "
         "AND geographic_segments_json != '[]'")
    cur.execute(q)
    rows = cur.fetchall()
    conn.close()
    if sample:
        import random
        rng = random.Random(seed)
        rows = rng.sample(rows, min(sample, len(rows)))
    if limit:
        rows = rows[:limit]
    for ticker, raw in rows:
        try:
            segs = json.loads(raw)
            yield ticker, segs
        except Exception:
            continue


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=str(_REPO_ROOT / "backend/data_sources/us_cn_hk.sqlite"))
    parser.add_argument("--sample", type=int, default=None, help="Random sample size (default: all)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--show-unresolved", type=int, default=20, help="Top N unresolved names to show")
    parser.add_argument("--verbose", action="store_true", help="Print per-company detail")
    args = parser.parse_args()

    store = DamodaranStore.from_directory(str(_REPO_ROOT / "knowledge_base/damodaran"))
    idx = build_indices(store)

    total_companies = 0
    clean_resolved = 0          # no red-flag buckets
    has_red_flag = 0
    total_inst = 0
    clean_inst = 0
    flagged_inst = 0
    layer_counter = Counter()
    red_flag_freq: Counter = Counter()

    for ticker, segs in iter_companies(args.db, sample=args.sample, seed=args.seed):
        total_companies += 1
        resolved, per_seg = resolve_company_segments(segs, idx)

        company_flagged = False
        for rec in per_seg:
            layer_counter[rec["source"]] += 1
            total_inst += 1
            if rec["red_flag"]:
                flagged_inst += 1
                company_flagged = True
                red_flag_freq[rec["raw_name"]] += 1
            else:
                clean_inst += 1

        if company_flagged:
            has_red_flag += 1
        else:
            clean_resolved += 1

        if args.verbose:
            print(f"\n{ticker}:")
            for b in resolved:
                tag = " [RED-FLAG]" if b.get("red_flag") else ""
                print(f"  → {b['target']} ({b['kind']}, {b['source']}, "
                      f"conf={b['confidence_min']:.2f}){tag}  revenue={b['revenue']:.0f}  "
                      f"raw={b['raw_names']}")

    label = f"SAMPLE (n={args.sample}, seed={args.seed})" if args.sample else "FULL DB"
    print(f"\n{'=' * 60}\n{label}\n{'=' * 60}")
    print(f"Companies processed:          {total_companies:,}")
    print(f"  cleanly resolved:           {clean_resolved:,}  ({clean_resolved/max(total_companies,1)*100:.1f}%)")
    print(f"  has red-flag segments:      {has_red_flag:,}  ({has_red_flag/max(total_companies,1)*100:.1f}%)")
    print(f"Segment instances:            {total_inst:,}  (100% assigned to a Damodaran target)")
    print(f"  clean:                      {clean_inst:,}  ({clean_inst/max(total_inst,1)*100:.1f}%)")
    print(f"  red-flagged:                {flagged_inst:,}  ({flagged_inst/max(total_inst,1)*100:.1f}%)")
    print(f"\nBy source:")
    for src in ("exact_country", "country_alias", "region_alias", "subdivision",
                "collapsed", "split", "other_prefix",
                "fuzzy_country", "fuzzy_region", "weak_default"):
        c = layer_counter.get(src, 0)
        if c:
            print(f"  {src:<20} {c:>8,}")
    if red_flag_freq and args.show_unresolved:
        print(f"\nTop {args.show_unresolved} red-flagged names (weak_default):")
        for name, count in red_flag_freq.most_common(args.show_unresolved):
            print(f"  {count:4d}×  {name!r}")


if __name__ == "__main__":
    main()
