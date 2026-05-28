import json
import os
from datetime import datetime, timezone
import urllib.error
import urllib.request

from dotenv import load_dotenv

# Load environment variables so this module also works in scripts and schedulers.
load_dotenv()


def _fetch_exchange_rate_payload() -> dict:
    """Fetch raw exchange-rate API payload for KRW base."""
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

    return data


def get_krw_conversions() -> dict[str, float]:
    """Return all current conversion rates using KRW as the base currency."""
    data = _fetch_exchange_rate_payload()

    rates = data.get("conversion_rates", {})

    if not rates:
        raise RuntimeError("ExchangeRate API returned no conversion rates")

    return {code: float(value) for code, value in rates.items()}


def save_daily_rates_to_supabase() -> int:
    """Fetch KRW rates and upsert one Supabase row per quote currency for today."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase_connection_string = os.getenv("SUPABASE_CONNECTION_STRING")

    data = _fetch_exchange_rate_payload()
    rates = data.get("conversion_rates", {})
    base_code = str(data.get("base_code", "KRW")).upper()

    if not rates:
        raise RuntimeError("ExchangeRate API returned no conversion rates")

    now_utc = datetime.now(timezone.utc)
    cache_date = now_utc.date().isoformat()
    fetched_at = now_utc.isoformat()

    # Build one record per currency pair (KRW -> quote_code).
    records = []
    for quote_code, rate in rates.items():
        records.append(
            {
                "provider": "exchangerate-api",
                "base_code": base_code,
                "quote_code": str(quote_code).upper(),
                "rate": float(rate),
                "cache_date": cache_date,
                "fetched_at": fetched_at,
                "raw_response": data,
            }
        )

    # Try PostgREST first when URL and key are available.
    if supabase_url and supabase_key:
        return _save_rows_via_postgrest(
            records=records,
            supabase_url=supabase_url,
            supabase_key=supabase_key,
        )

    # Fallback to direct PostgreSQL connection if provided.
    if supabase_connection_string:
        return _save_rows_via_postgres(
            records=records,
            connection_string=supabase_connection_string,
        )

    raise RuntimeError(
        "Missing Supabase credentials. Set either SUPABASE_URL + SUPABASE_KEY "
        "or SUPABASE_CONNECTION_STRING in .env"
    )


def _save_rows_via_postgrest(
    records: list[dict],
    supabase_url: str,
    supabase_key: str,
) -> int:
    """Upsert rows using Supabase PostgREST API."""

    endpoint = (
        f"{supabase_url.rstrip('/')}/rest/v1/fx_rates_daily_cache"
        "?on_conflict=provider,base_code,quote_code,cache_date"
    )
    body = json.dumps(records).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30):
            pass
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Failed to upsert FX rows into Supabase: HTTP {error.code} - {error_body}"
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Failed to connect to Supabase: {error}") from error

    return len(records)


def _save_rows_via_postgres(records: list[dict], connection_string: str) -> int:
    """Upsert rows using direct PostgreSQL connection."""
    import psycopg
    from psycopg.types.json import Jsonb

    sql = """
    INSERT INTO public.fx_rates_daily_cache (
        provider,
        base_code,
        quote_code,
        rate,
        cache_date,
        fetched_at,
        raw_response
    )
    VALUES (
        %(provider)s,
        %(base_code)s,
        %(quote_code)s,
        %(rate)s,
        %(cache_date)s,
        %(fetched_at)s,
        %(raw_response)s::jsonb
    )
    ON CONFLICT (provider, base_code, quote_code, cache_date)
    DO UPDATE SET
        rate = EXCLUDED.rate,
        fetched_at = EXCLUDED.fetched_at,
        raw_response = EXCLUDED.raw_response,
        updated_at = now()
    """

    payload_rows = []
    for row in records:
        payload_rows.append(
            {
                "provider": row["provider"],
                "base_code": row["base_code"],
                "quote_code": row["quote_code"],
                "rate": row["rate"],
                "cache_date": row["cache_date"],
                "fetched_at": row["fetched_at"],
                "raw_response": Jsonb(row["raw_response"]),
            }
        )

    try:
        with psycopg.connect(connection_string) as connection:
            with connection.cursor() as cursor:
                cursor.executemany(sql, payload_rows)
            connection.commit()
    except Exception as error:
        raise RuntimeError(f"Failed to upsert FX rows into Supabase PostgreSQL: {error}") from error

    return len(records)


def get_fx(currency: str) -> float:
    """Return the conversion rate from KRW to the requested currency code."""
    rates = get_krw_conversions()
    currency_code = currency.upper()

    if currency_code not in rates:
        raise ValueError(f"Currency code not found: {currency_code}")

    return float(rates[currency_code])


if __name__ == "__main__":
    upserted_rows = save_daily_rates_to_supabase()
    print(f"Saved {upserted_rows} FX rows to Supabase.")
