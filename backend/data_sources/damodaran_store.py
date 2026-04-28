"""
Damodaran Data Store — loads all Damodaran datasets and provides lookup by industry/country.

Usage:
    store = DamodaranStore.from_directory("knowledge_base/damodaran")
    industry = store.lookup_industry("Food Processing", region="US")
    country  = store.lookup_country("Saudi Arabia")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from engine.data_dictionary import IndustryData, MacroInputs

from .damodaran_parsers.beta_parser import parse_betas
from .damodaran_parsers.wacc_parser import parse_wacc
from .damodaran_parsers.margin_parser import parse_margins
from .damodaran_parsers.taxrate_parser import parse_industry_tax_rates
from .damodaran_parsers.country_risk_parser import parse_country_risk
from .damodaran_parsers.country_tax_parser import parse_country_tax_rates
from .damodaran_parsers.capex_parser import parse_capex
from .damodaran_parsers.fundgr_parser import parse_fundgr
from .damodaran_parsers.eva_parser import parse_eva
from .damodaran_parsers.vebitda_parser import parse_vebitda
from .damodaran_parsers.pedata_parser import parse_pedata
from .damodaran_parsers.pbvdata_parser import parse_pbvdata
from .damodaran_parsers.psdata_parser import parse_psdata

# All regions Damodaran provides
_REGIONS = {
    "":        "US",
    "Global":  "Global",
    "China":   "China",
    "India":   "India",
    "Japan":   "Japan",
    "Europe":  "Europe",
    "emerg":   "Emerging",
    "Rest":    "Rest",
}

# Base datasets → (file_stem_prefix, parser)
_BASE_DATASETS = [
    ("betas",     "beta",     parse_betas),
    ("wacc",      "wacc",     parse_wacc),
    ("margin",    "margin",   parse_margins),
    ("taxrate",   "taxrate",  parse_industry_tax_rates),
    ("capex",     "capex",    parse_capex),
    ("fundgrEB",  "fundgrEB", parse_fundgr),
    ("EVA",       "EVA",      parse_eva),
    ("vebitda",   "vebitda",  parse_vebitda),
    ("pedata",    "pe",       parse_pedata),
    ("pbvdata",   "pbv",      parse_pbvdata),
    ("psdata",    "ps",       parse_psdata),
]

# Build the full mapping: {file_stem: (region, parser)}
_INDUSTRY_FILES: dict[str, tuple[str, callable]] = {}
for us_stem, prefix, parser in _BASE_DATASETS:
    for suffix, region in _REGIONS.items():
        if suffix == "":
            # US version: use the us_stem directly (e.g., "betas", "pedata")
            _INDUSTRY_FILES[us_stem] = (region, parser)
        else:
            # Regional: prefix + suffix (e.g., "betaGlobal", "capexChina", "peGlobal")
            _INDUSTRY_FILES[f"{prefix}{suffix}"] = (region, parser)


@dataclass
class DamodaranStore:
    """In-memory store for all Damodaran reference data."""

    # Industry data: {region: {industry_name: {dataset_type: {field: value}}}}
    # Flattened for lookup: {(region, industry_name): merged_dict}
    _industry_data: dict[tuple[str, str], dict] = field(default_factory=dict)

    # Country data: {country_name: {field: value}}
    _country_risk: dict[str, dict] = field(default_factory=dict)
    _country_tax: dict[str, dict] = field(default_factory=dict)

    # Industry stat distributions (Q1/Median/Q3 for key ratios) — from Ginzu Input Stat Distributioons sheet.
    # Used as Damodaran-style benchmark for user-hypothesis inputs.
    _industry_stats: dict[str, dict] = field(default_factory=dict)

    # Metadata
    industries_loaded: dict[str, int] = field(default_factory=dict)
    countries_loaded: int = 0

    @classmethod
    def from_directory(cls, dir_path: str | Path) -> DamodaranStore:
        """Load all Damodaran datasets from a directory."""
        store = cls()
        dir_path = Path(dir_path)

        # Load industry-level datasets
        for stem, (region, parser) in _INDUSTRY_FILES.items():
            for ext in (".xls", ".xlsx"):
                fpath = dir_path / f"{stem}{ext}"
                if fpath.exists():
                    data = parser(str(fpath))
                    store._merge_industry_data(region, stem, data)
                    break

        # Load country risk premiums
        for name in ("ctryprem.xlsx", "ctryprem.xls"):
            fpath = dir_path / name
            if fpath.exists():
                store._country_risk = parse_country_risk(str(fpath))
                store.countries_loaded = len(store._country_risk)
                break

        # Load country tax rates
        for name in ("countrytaxrates.xls", "countrytaxrates.xlsx"):
            fpath = dir_path / name
            if fpath.exists():
                store._country_tax = parse_country_tax_rates(str(fpath))
                break

        # Load industry statistical distributions (extracted from Ginzu workbook)
        import json
        stats_path = Path(__file__).parent / "industry_stats.json"
        if stats_path.exists():
            try:
                with stats_path.open() as f:
                    data = json.load(f)
                    store._industry_stats = data.get("industries", {})
            except Exception:
                pass

        return store

    def _merge_industry_data(self, region: str, file_stem: str, data: dict[str, dict]) -> None:
        """Merge parsed industry data into the store."""
        for industry_name, values in data.items():
            key = (region, industry_name)
            if key not in self._industry_data:
                self._industry_data[key] = {}
            self._industry_data[key].update(values)
        self.industries_loaded[f"{file_stem}_{region}"] = len(data)

    def list_industries(self, region: str = "US") -> list[str]:
        """List all industry names for a given region."""
        return sorted({name for (r, name) in self._industry_data if r == region})

    def list_countries(self) -> list[str]:
        """List all countries with risk premium data."""
        return sorted(k for k in self._country_risk if not k.startswith("__"))

    def lookup_industry(self, industry_name: str, region: str = "US") -> IndustryData | None:
        """Look up industry data and return a typed IndustryData model.

        Tries exact match first, then fuzzy matching:
        1. Case-insensitive exact
        2. Prefix match (e.g., "Retail (Online)" → "Retail (General)")
        3. Best substring overlap
        """
        key = (region, industry_name)
        raw = self._industry_data.get(key)

        # Known industry name mappings (CIQ name → Damodaran name)
        _INDUSTRY_ALIASES = {
            "retail (online)": "Retail (General)",
            "software (entertainment)": "Entertainment",
            "software (system & application)": "Software (System & Application)",
            "financial svcs. (non-bank & insurance)": "Financial Svcs. (Non-bank & Insurance)",
        }

        # Fuzzy fallback if exact match fails
        if raw is None:
            query_lower = industry_name.lower()

            # Check alias table first
            alias = _INDUSTRY_ALIASES.get(query_lower)
            if alias:
                raw = self._industry_data.get((region, alias))
                if raw:
                    industry_name = alias

            # If alias didn't work, try fuzzy matching
            if raw is None:
                query_prefix = query_lower.split("(")[0].strip() if "(" in query_lower else query_lower
                best_name = None
                best_score = 0

                for (r, name) in self._industry_data:
                    if r != region:
                        continue
                    name_lower = name.lower()
                    # Case-insensitive exact
                    if name_lower == query_lower:
                        best_name = name
                        best_score = 100
                        break
                    # Prefix match — prefer "General" variant for generic categories
                    name_prefix = name_lower.split("(")[0].strip() if "(" in name_lower else name_lower
                    if name_prefix == query_prefix:
                        score = 80
                        if "general" in name_lower:
                            score = 85  # prefer "General" over specific variants
                        if score > best_score:
                            best_name = name
                            best_score = score
                    # Word overlap (lower priority)
                    query_words = set(query_lower.replace("(", " ").replace(")", " ").split())
                    name_words = set(name_lower.replace("(", " ").replace(")", " ").split())
                    overlap = len(query_words & name_words)
                    if overlap > 1 and overlap > best_score:
                        best_name = name
                        best_score = overlap

                if best_name:
                    raw = self._industry_data.get((region, best_name))
                    industry_name = best_name

        if raw is None:
            return None

        return IndustryData(
            industry_name=industry_name,
            region=region,
            beta_u=raw.get("beta_u", 0.0),
            beta_u_corrected_for_cash=raw.get("beta_u_corrected_for_cash"),
            industry_d_e_ratio=raw.get("d_e_ratio"),
            industry_effective_tax_rate=raw.get("effective_tax_rate") or raw.get("effective_tax_rate_avg"),
            cost_of_equity=raw.get("cost_of_equity"),
            cost_of_debt_pretax=raw.get("cost_of_debt_pretax"),
            wacc=raw.get("wacc"),
            pretax_operating_margin=raw.get("pretax_operating_margin"),
            after_tax_operating_margin=raw.get("aftertax_operating_margin"),
            sales_to_capital=raw.get("sales_to_capital"),
            revenue_growth=raw.get("revenue_growth"),
            std_dev_stock=raw.get("std_dev_stock"),
            roic=raw.get("roic"),
            ev_ebitda=raw.get("ev_ebitda"),
            ev_sales=raw.get("ev_sales"),
            pe_ratio=raw.get("pe_ratio"),
            pbv_ratio=raw.get("pbv_ratio"),
        )

    def lookup_country(self, country_name: str) -> MacroInputs | None:
        """Look up country-level macro data and return a typed MacroInputs model.

        Note: risk_free_rate must be provided separately (it's not country-specific
        in Damodaran's framework — it's the US T-bond rate).
        """
        # The country-risk dataset uses shorter names ("United States", "United Kingdom")
        # but the country-tax dataset uses formal names ("United States of America",
        # "United Kingdom of Great Britain and Northern Ireland"). Match both via alias list.
        def _find(country_dict: dict, name: str) -> dict | None:
            if name in country_dict:
                return country_dict[name]
            # Try case-insensitive exact
            lower = {k.lower(): v for k, v in country_dict.items()}
            if name.lower() in lower:
                return lower[name.lower()]
            # Known alias families — short-form → formal
            aliases_try = {
                "United States": ["United States of America"],
                "United Kingdom": ["United Kingdom of Great Britain and Northern Ireland"],
                "Russia": ["Russian Federation"],
                "South Korea": ["Korea, Republic of"],
                "North Korea": ["Korea, Democratic People's Republic of", "Korea, D.P.R."],
                "Iran": ["Iran, Islamic Republic of"],
                "Venezuela": ["Venezuela, Bolivarian Republic of"],
                "Taiwan": ["Taiwan, Province of China"],
                "Hong Kong": ["Hong Kong, Special Administrative Region of China",
                              "China, Hong Kong Special Administrative Region"],
                "Macau": ["Macao", "Macao, Special Administrative Region of China",
                          "China, Macao Special Administrative Region"],
                "Vietnam": ["Viet Nam"],
                "Syria": ["Syrian Arab Republic"],
                "Bolivia": ["Plurinational State of Bolivia", "Bolivia (Plurinational State of)"],
                "Tanzania": ["United Republic of Tanzania"],
                "Moldova": ["Republic of Moldova"],
                "Czech Republic": ["Czechia"],
                "Congo (Democratic Republic of)": ["Democratic Republic of the Congo"],
                "Laos": ["Lao People's Democratic Republic"],
                "Cape Verde": ["Cabo Verde"],
                "Ivory Coast": ["Côte d'Ivoire", "Cote d'Ivoire"],
                "Myanmar": ["Burma"],
                "Palestine": ["State of Palestine"],
                "Micronesia": ["Federated States of Micronesia"],
            }
            for target in aliases_try.get(name, []):
                if target in country_dict:
                    return country_dict[target]
            # Reverse: if caller passed a formal name, try the short form
            for short, formals in aliases_try.items():
                if name in formals and short in country_dict:
                    return country_dict[short]
            return None

        risk = _find(self._country_risk, country_name)
        tax = _find(self._country_tax, country_name)

        if risk is None and tax is None:
            return None

        erp = risk.get("equity_risk_premium", 0.0) if risk else 0.0
        crp = risk.get("country_risk_premium", 0.0) if risk else 0.0
        tax_rate = tax.get("corporate_tax_rate", 0.0) if tax else 0.0

        return MacroInputs(
            risk_free_rate=0.0,  # Must be set by caller
            equity_risk_premium=erp,
            country_risk_premium=crp,
            tax_rate_marginal=tax_rate,
            default_spread=risk.get("default_spread") if risk else None,
        )

    def get_mature_market_erp(self) -> float | None:
        """Get the mature market ERP extracted from the ctryprem file."""
        meta = self._country_risk.get("__mature_market_erp__")
        if meta:
            return meta.get("equity_risk_premium")
        return None

    def lookup_industry_stats(self, industry_name: str) -> dict | None:
        """Look up industry statistical distribution (Q1/Median/Q3 for key ratios).

        Falls back to fuzzy matching (case-insensitive substring) if exact match fails.
        Returns None if industry not found.
        """
        if not industry_name:
            return None
        # Exact match
        if industry_name in self._industry_stats:
            return self._industry_stats[industry_name]
        # Case-insensitive
        lower_map = {k.lower(): v for k, v in self._industry_stats.items()}
        if industry_name.lower() in lower_map:
            return lower_map[industry_name.lower()]
        # Substring fuzzy
        for k in self._industry_stats:
            if industry_name.lower() in k.lower() or k.lower() in industry_name.lower():
                return self._industry_stats[k]
        return None
