"""
Comprehensive test: 100 global tickers across all major exchanges.

Tests the full lookup pipeline:
1. IndustryMapper.lookup(ticker) → CompanyInfo (company_name, country, industry, exchange_ticker)
2. get_stock_price_currency(exchange_ticker) → currency code
3. _country_to_region(country) → Damodaran region
4. DamodaranStore.lookup_industry(industry, region) → IndustryData with all fields
5. Correct source file identification for each region

Every failure is a bug that must be fixed.
"""

import sys
import os
import random
from pathlib import Path

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data_sources.industry_mapper import IndustryMapper
from data_sources.exchange_currency_map import get_stock_price_currency, EXCHANGE_CURRENCY
from data_sources.damodaran_store import DamodaranStore

# Import the country→region mapping from routes
# We replicate it here to avoid importing FastAPI
_COUNTRY_TO_REGION: dict[str, str] = {}
for _c in ("China", "Hong Kong", "Macau", "Taiwan"):
    _COUNTRY_TO_REGION[_c] = "China"
_COUNTRY_TO_REGION["India"] = "India"
_COUNTRY_TO_REGION["Japan"] = "Japan"
for _c in ("United Kingdom", "Germany", "France", "Italy", "Spain", "Netherlands",
           "Switzerland", "Sweden", "Norway", "Denmark", "Finland", "Belgium",
           "Austria", "Ireland", "Portugal", "Greece", "Luxembourg", "Poland",
           "Czech Republic", "Hungary", "Romania", "Croatia", "Iceland",
           "Liechtenstein", "Monaco", "Malta", "Cyprus", "Estonia", "Latvia",
           "Lithuania", "Slovenia", "Slovakia", "Bulgaria"):
    _COUNTRY_TO_REGION[_c] = "Europe"
for _c in ("United States", "Canada"):
    _COUNTRY_TO_REGION[_c] = "US"
for _c in ("South Korea", "Australia", "New Zealand", "Singapore",
           "Israel", "Qatar", "Kuwait", "Bahrain", "Oman", "Jordan", "Lebanon"):
    _COUNTRY_TO_REGION[_c] = "Global"
for _c in ("Brazil", "Mexico", "Argentina", "Chile", "Colombia", "Peru",
           "South Africa", "Turkey", "Russia", "Saudi Arabia", "UAE",
           "Egypt", "Nigeria", "Kenya", "Pakistan", "Bangladesh",
           "Thailand", "Indonesia", "Malaysia", "Philippines", "Vietnam"):
    _COUNTRY_TO_REGION[_c] = "Emerging"


def _country_to_region(country: str) -> str:
    if not country:
        return "US"
    if country in _COUNTRY_TO_REGION:
        return _COUNTRY_TO_REGION[country]
    country_lower = country.lower()
    for key, region in _COUNTRY_TO_REGION.items():
        if key.lower() in country_lower or country_lower in key.lower():
            return region
    return "Global"


# Region → expected file suffix for source traceability
_REGION_FILE_SUFFIXES = {
    "US": "",
    "Global": "Global",
    "China": "China",
    "India": "India",
    "Japan": "Japan",
    "Europe": "Europe",
    "Emerging": "emerg",
    "Rest": "Rest",
}


def _expected_source_files(region: str) -> dict[str, str]:
    """Return expected Damodaran source filenames for a given region."""
    s = _REGION_FILE_SUFFIXES.get(region, "Global")
    return {
        "beta": f"beta{s}.xls" if s else "betas.xls",
        "wacc": f"wacc{s}.xls" if s else "wacc.xls",
        "margin": f"margin{s}.xls" if s else "margin.xls",
        "taxrate": f"taxrate{s}.xls" if s else "taxrate.xls",
        "capex": f"capex{s}.xls" if s else "capex.xls",
        "fundgr": f"fundgrEB{s}.xls" if s else "fundgrEB.xls",
        "eva": f"EVA{s}.xls" if s else "EVA.xls",
        "vebitda": f"vebitda{s}.xls" if s else "vebitda.xls",
        "pe": f"pe{s}.xls" if s else "pedata.xls",
        "pbv": f"pbv{s}.xls" if s else "pbvdata.xls",
    }


def main():
    data_dir = Path(__file__).resolve().parent.parent.parent / "knowledge_base"

    print("Loading IndustryMapper...")
    mapper = IndustryMapper.from_file(str(data_dir / "industry_lookup" / "indname.xlsx"))
    print(f"  Loaded {mapper.total_companies} companies")

    print("Loading DamodaranStore...")
    store = DamodaranStore.from_directory(str(data_dir / "damodaran"))
    print(f"  Loaded {len(store.industries_loaded)} dataset files")

    # ----- STEP 1: Sample 100 tickers from the mapper, ensuring diverse exchanges -----
    # Collect all companies by exchange
    all_companies = []
    for key, info in mapper._by_exchange_ticker.items():
        all_companies.append(info)

    # Group by exchange prefix
    by_exchange: dict[str, list] = {}
    for info in all_companies:
        if ":" in info.exchange_ticker:
            exch = info.exchange_ticker.split(":")[0]
            by_exchange.setdefault(exch, []).append(info)

    print(f"\nFound {len(by_exchange)} unique exchanges across {len(all_companies)} companies")

    # Sample: take up to 3 companies per exchange, fill to 100
    random.seed(42)  # reproducible
    sampled = []
    exchanges_sorted = sorted(by_exchange.keys(), key=lambda e: -len(by_exchange[e]))

    for exch in exchanges_sorted:
        companies = by_exchange[exch]
        n = min(3, len(companies))
        sampled.extend(random.sample(companies, n))
        if len(sampled) >= 100:
            break

    # If we haven't reached 100, sample more from large exchanges
    if len(sampled) < 100:
        remaining = [c for c in all_companies if c not in sampled]
        extra = random.sample(remaining, min(100 - len(sampled), len(remaining)))
        sampled.extend(extra)

    sampled = sampled[:100]
    random.shuffle(sampled)

    print(f"Testing {len(sampled)} tickers across {len(set(c.exchange_ticker.split(':')[0] for c in sampled if ':' in c.exchange_ticker))} exchanges\n")

    # ----- STEP 2: Run tests -----
    results = {
        "total": len(sampled),
        "currency_found": 0,
        "currency_missing": 0,
        "region_mapped": 0,
        "region_unmapped": 0,
        "industry_found": 0,
        "industry_missing": 0,
        "industry_has_all_fields": 0,
        "source_files_exist": 0,
        "source_files_missing": 0,
    }

    missing_exchanges = set()
    missing_countries = set()
    missing_industries = []
    missing_fields_detail = []

    print(f"{'#':>3} {'Ticker':<20} {'Country':<20} {'Region':<10} {'CCY':<5} {'Industry':<30} {'Fields'}")
    print("-" * 130)

    for i, info in enumerate(sampled):
        ticker = info.exchange_ticker
        country = info.country or ""
        industry = info.industry_group or ""

        # Test 1: Currency lookup
        currency = get_stock_price_currency(ticker)
        if currency:
            results["currency_found"] += 1
        else:
            results["currency_missing"] += 1
            exch = ticker.split(":")[0] if ":" in ticker else ticker
            missing_exchanges.add(exch)

        # Test 2: Country → Region mapping
        region = _country_to_region(country)
        if region != "Global":  # "Global" is our fallback
            results["region_mapped"] += 1
        else:
            results["region_unmapped"] += 1
            if country:
                missing_countries.add(country)

        # Test 3: Industry lookup in the correct region
        ind = store.lookup_industry(industry, region=region)
        if ind is None and region not in ("US", "Global"):
            # Fallback
            for fb in ("US", "Global"):
                ind = store.lookup_industry(industry, region=fb)
                if ind:
                    region = fb
                    break

        if ind:
            results["industry_found"] += 1

            # Test 4: Check all key fields are populated
            key_fields = {
                "beta_u": ind.beta_u,
                "wacc": ind.wacc,
                "margin": ind.pretax_operating_margin,
                "sales_to_cap": ind.sales_to_capital,
                "rev_growth": ind.revenue_growth,
                "roic": ind.roic,
                "std_dev": ind.std_dev_stock,
                "ev_ebitda": ind.ev_ebitda,
                "pe_ratio": ind.pe_ratio,
                "pbv_ratio": ind.pbv_ratio,
            }
            missing = [k for k, v in key_fields.items() if v is None]
            filled = len(key_fields) - len(missing)

            if not missing:
                results["industry_has_all_fields"] += 1
            else:
                missing_fields_detail.append((ticker, industry, region, missing))

            # Test 5: Verify source files exist on disk
            expected_files = _expected_source_files(region)
            dam_dir = data_dir / "damodaran"
            files_ok = True
            for dataset, filename in expected_files.items():
                if not (dam_dir / filename).exists():
                    files_ok = False
            if files_ok:
                results["source_files_exist"] += 1
            else:
                results["source_files_missing"] += 1

            fields_str = f"{filled}/{len(key_fields)}" + (f" MISSING: {','.join(missing)}" if missing else " OK")
        else:
            results["industry_missing"] += 1
            missing_industries.append((ticker, industry, region, country))
            fields_str = "NO INDUSTRY DATA"

        ccy_str = currency or "???"
        print(f"{i+1:>3} {ticker:<20} {country[:19]:<20} {region:<10} {ccy_str:<5} {industry[:29]:<30} {fields_str}")

    # ----- STEP 3: Summary -----
    print("\n" + "=" * 130)
    print("SUMMARY")
    print("=" * 130)

    total = results["total"]
    print(f"\nCurrency Lookup:     {results['currency_found']}/{total} found ({results['currency_found']*100/total:.0f}%)")
    if missing_exchanges:
        print(f"  Missing exchanges: {sorted(missing_exchanges)}")

    print(f"\nRegion Mapping:      {results['region_mapped']}/{total} mapped ({results['region_mapped']*100/total:.0f}%)")
    if missing_countries:
        print(f"  Unmapped countries ({len(missing_countries)}): {sorted(missing_countries)[:20]}")

    print(f"\nIndustry Lookup:     {results['industry_found']}/{total} found ({results['industry_found']*100/total:.0f}%)")
    if missing_industries:
        print(f"  Missing ({len(missing_industries)}):")
        for t, ind, reg, ctry in missing_industries[:10]:
            print(f"    {t}: industry='{ind}' region={reg} country={ctry}")

    print(f"\nAll Fields Populated: {results['industry_has_all_fields']}/{results['industry_found']} ({results['industry_has_all_fields']*100/max(1,results['industry_found']):.0f}%)")

    print(f"\nSource Files Exist:  {results['source_files_exist']}/{results['industry_found']} ({results['source_files_exist']*100/max(1,results['industry_found']):.0f}%)")

    # Check for FAILURES
    failures = []
    if results["currency_missing"] > 10:
        failures.append(f"Too many missing currencies: {results['currency_missing']}")
    if results["industry_missing"] > 5:
        failures.append(f"Too many missing industries: {results['industry_missing']}")
    if results["industry_has_all_fields"] < results["industry_found"] * 0.9:
        failures.append(f"Too many incomplete industry records")

    if failures:
        print(f"\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    else:
        print(f"\nALL CHECKS PASSED")
        return 0


if __name__ == "__main__":
    sys.exit(main())
