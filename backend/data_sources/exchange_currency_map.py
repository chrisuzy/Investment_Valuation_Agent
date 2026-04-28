"""Exchange prefix → stock price currency mapping."""

EXCHANGE_CURRENCY: dict[str, str] = {
    # North America
    "NasdaqGS": "USD",
    "NasdaqGM": "USD",
    "NasdaqCM": "USD",
    "NYSE": "USD",
    "AMEX": "USD",
    "OTC": "USD",
    "OTCPK": "USD",
    "OTCQB": "USD",
    "OTCQX": "USD",
    "CNSX": "CAD",
    "TSX": "CAD",
    "TSXV": "CAD",
    "BMV": "MXN",
    # Europe
    "LSE": "GBP",
    "AIM": "GBP",
    "XETRA": "EUR",
    "XTRA": "EUR",
    "DB": "EUR",
    "ENXTPA": "EUR",
    "ENXTAM": "EUR",
    "ENXTBR": "EUR",
    "ENXTLS": "EUR",
    "SWX": "CHF",
    "BIT": "EUR",
    "BME": "EUR",
    "WBAG": "EUR",
    "OMX": "SEK",
    "OM": "SEK",
    "HLSE": "EUR",
    "OSE": "NOK",
    "CSE": "DKK",
    "ISE": "EUR",
    "MOEX": "RUB",
    "WSE": "PLN",
    "ATSE": "EUR",
    "IBSE": "TRY",
    # Middle East & Africa
    "SASE": "SAR",
    "DFM": "AED",
    "ADX": "AED",
    "TASE": "ILS",
    "QSE": "QAR",
    "KSE": "KWD",
    "KASE": "PKR",
    "BSE_BH": "BHD",
    "MSM": "OMR",
    "EGX": "EGP",
    "JSE": "ZAR",
    # Asia-Pacific
    "TSE": "JPY",
    "HKSE": "HKD",
    "SEHK": "HKD",
    "SSE": "CNY",
    "SHSE": "CNY",
    "SZSE": "CNY",
    "BSE": "INR",
    "NSE": "INR",
    "NSEI": "INR",
    "KRX": "KRW",
    "KOSE": "KRW",
    "KOSDAQ": "KRW",
    "TWSE": "TWD",
    "TPEX": "TWD",
    "SET": "THB",
    "SGX": "SGD",
    "ASX": "AUD",
    "NZX": "NZD",
    "IDX": "IDR",
    "KLSE": "MYR",
    "PSE": "PHP",
    "HOSE": "VND",
    "HNX": "VND",
    # South America
    "BOVESPA": "BRL",
    "BCS": "CLP",
    "BVL": "PEN",
    "BCBA": "ARS",
}


def get_stock_price_currency(ticker: str) -> str | None:
    """Extract exchange prefix from ticker and return the stock price currency.

    Ticker formats: 'SASE:2280', 'NasdaqGS:AAPL', etc.
    Returns None if exchange not recognized.
    """
    if ":" not in ticker:
        return None
    exchange_prefix = ticker.split(":")[0]
    return EXCHANGE_CURRENCY.get(exchange_prefix)
