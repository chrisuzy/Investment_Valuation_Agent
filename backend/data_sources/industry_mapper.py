"""
Industry Mapper — maps a company ticker to Damodaran industry classification.

Uses Damodaran's indname.xlsx (48K+ companies) which contains:
  Company Name, Exchange:Ticker, Industry Group, Primary Sector, SIC Code, Country, Broad Group, Sub Group

The Exchange:Ticker format is "Exchange:Symbol" (e.g., "SASE:4071", "NasdaqGS:AAPL").
We build lookup indexes on both the full Exchange:Ticker and the bare symbol.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl


@dataclass
class CompanyInfo:
    company_name: str
    exchange_ticker: str  # e.g. "NasdaqGS:AAPL"
    industry_group: str   # Damodaran industry classification
    primary_sector: str
    sic_code: str
    country: str
    broad_group: str      # e.g. "Developed Markets"
    sub_group: str        # e.g. "United States"


@dataclass
class IndustryMapper:
    """Maps tickers to Damodaran industry groups."""

    # Lookup by bare ticker symbol (e.g., "AAPL" → CompanyInfo)
    _by_symbol: dict[str, CompanyInfo] = field(default_factory=dict)

    # Lookup by full Exchange:Ticker (e.g., "NasdaqGS:AAPL" → CompanyInfo)
    _by_exchange_ticker: dict[str, CompanyInfo] = field(default_factory=dict)

    # Lookup by company name (lowercase, for fuzzy matching)
    _by_name: dict[str, CompanyInfo] = field(default_factory=dict)

    total_companies: int = 0

    _US_EXCHANGES = {"NASDAQGS", "NASDAQGM", "NASDAQCM", "NYSE", "NYSEAMERICAN"}

    def _index_company(self, info: CompanyInfo) -> None:
        """Add a CompanyInfo entry to all lookup indexes."""
        if info.exchange_ticker:
            self._by_exchange_ticker[info.exchange_ticker.upper()] = info
            if ":" in info.exchange_ticker:
                symbol = info.exchange_ticker.split(":")[-1].upper()
                exchange = info.exchange_ticker.split(":")[0].upper()
                if symbol not in self._by_symbol:
                    self._by_symbol[symbol] = info
                elif exchange in self._US_EXCHANGES:
                    existing_exchange = self._by_symbol[symbol].exchange_ticker.split(":")[0].upper()
                    if existing_exchange not in self._US_EXCHANGES:
                        self._by_symbol[symbol] = info
        name_key = info.company_name.lower()
        if name_key and name_key not in self._by_name:
            self._by_name[name_key] = info
        self.total_companies += 1

    @classmethod
    def from_file(cls, file_path: str | Path) -> IndustryMapper:
        """Load from Damodaran's indname.xlsx."""
        mapper = cls()
        wb = openpyxl.load_workbook(str(file_path), data_only=True, read_only=True)
        ws = wb.active

        rows = ws.iter_rows(min_row=2, values_only=True)
        for row in rows:
            if not row or not row[0]:
                continue
            # Columns: CompanyName, Exchange:Ticker, IndustryGroup, PrimarySector, SIC, Country, BroadGroup, SubGroup
            vals = [str(v).strip() if v else "" for v in row[:8]]
            while len(vals) < 8:
                vals.append("")

            info = CompanyInfo(
                company_name=vals[0],
                exchange_ticker=vals[1],
                industry_group=vals[2],
                primary_sector=vals[3],
                sic_code=vals[4],
                country=vals[5],
                broad_group=vals[6],
                sub_group=vals[7],
            )

            mapper._index_company(info)

        wb.close()

        # Load supplemental companies (tickers missing from Damodaran's data)
        supplemental = Path(file_path).parent / "supplemental_companies.json"
        if supplemental.exists():
            mapper.load_supplemental(supplemental)

        return mapper

    def load_supplemental(self, json_path: str | Path) -> None:
        """Load additional companies from a JSON file to fill gaps in indname.xlsx."""
        with open(json_path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        for entry in entries:
            info = CompanyInfo(
                company_name=entry.get("company_name", ""),
                exchange_ticker=entry.get("exchange_ticker", ""),
                industry_group=entry.get("industry_group", ""),
                primary_sector=entry.get("primary_sector", ""),
                sic_code=entry.get("sic_code", ""),
                country=entry.get("country", ""),
                broad_group=entry.get("broad_group", ""),
                sub_group=entry.get("sub_group", ""),
            )
            self._index_company(info)

    def lookup(self, query: str) -> CompanyInfo | None:
        """
        Look up a company by ticker symbol, Exchange:Ticker, or company name.

        Tries in order:
        1. Exact match on bare symbol (e.g., "AAPL")
        2. Exact match on Exchange:Ticker (e.g., "NasdaqGS:AAPL")
        3. Substring match on company name
        """
        q = query.strip().upper()

        # Try bare symbol
        if q in self._by_symbol:
            return self._by_symbol[q]

        # Try full exchange:ticker
        if q in self._by_exchange_ticker:
            return self._by_exchange_ticker[q]

        # Try company name (case-insensitive substring)
        q_lower = query.strip().lower()
        for name_key, info in self._by_name.items():
            if q_lower in name_key:
                return info

        return None

    def search(self, query: str, max_results: int = 20) -> list[CompanyInfo]:
        """
        Fuzzy search: return ALL matching companies by symbol, exchange:ticker, or name.

        Matches by:
        1. Exact symbol match (e.g., "2280" → all exchanges with symbol 2280)
        2. Exact Exchange:Ticker match (e.g., "SASE:2280")
        3. Company name substring (e.g., "Almarai", "Lenovo")
        4. Exchange prefix match (e.g., "SASE" → all SASE-listed companies, capped)
        """
        q = query.strip()
        q_upper = q.upper()
        q_lower = q.lower()
        results: list[CompanyInfo] = []
        seen: set[str] = set()

        def _add(info: CompanyInfo) -> None:
            key = info.exchange_ticker.upper()
            if key not in seen:
                seen.add(key)
                results.append(info)

        # 1. Exact Exchange:Ticker
        if q_upper in self._by_exchange_ticker:
            _add(self._by_exchange_ticker[q_upper])

        # 2. All exchanges with this symbol (e.g., "2280" → SASE:2280, SZSE:2280, etc.)
        for et_key, info in self._by_exchange_ticker.items():
            if et_key.endswith(f":{q_upper}"):
                _add(info)

        # 3. Company name substring (case-insensitive)
        for name_key, info in self._by_name.items():
            if q_lower in name_key:
                _add(info)
                if len(results) >= max_results:
                    break

        return results[:max_results]

    def get_industry(self, query: str) -> str | None:
        """Shorthand: look up and return just the Damodaran industry group name."""
        info = self.lookup(query)
        return info.industry_group if info else None

    def get_country(self, query: str) -> str | None:
        """Shorthand: look up and return just the country."""
        info = self.lookup(query)
        return info.country if info else None
