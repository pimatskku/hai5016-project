import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

# Load environment variables so this module also works in scripts and schedulers.
load_dotenv()


def get_krw_conversions() -> dict[str, float]:
    """Return all current conversion rates using KRW as the base currency."""
    # Read the API key from the .env file.
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing EXCHANGE_RATE_API_KEY in .env")

    # Ask the exchange-rate service for all rates using KRW as the base currency.
    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/KRW"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; hai5016-project/1.0)"},
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as error:
        raise RuntimeError(f"Failed to fetch exchange rates: {error}") from error

    # Surface API-level failures clearly.
    if data.get("result") != "success":
        error_type = data.get("error-type", "unknown_error")
        raise RuntimeError(f"ExchangeRate API error: {error_type}")

    rates = data.get("conversion_rates", {})

    if not rates:
        raise RuntimeError("ExchangeRate API returned no conversion rates")

    return {code: float(value) for code, value in rates.items()}


def get_fx(currency: str) -> float:
    """Return the conversion rate from KRW to the requested currency code."""
    rates = get_krw_conversions()
    currency_code = currency.upper()

    if currency_code not in rates:
        raise ValueError(f"Currency code not found: {currency_code}")

    return float(rates[currency_code])


if __name__ == "__main__":
    print(json.dumps(get_krw_conversions(), indent=2, sort_keys=True))
