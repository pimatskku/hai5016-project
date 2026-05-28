I’m checking the current script and repo setup first so I can wire the smallest reliable scheduled workflow around the existing entry point.

Read [](file:///workspaces/hai5016-project/.github)

Search complete: Locate rate script

Searched for files matching `**/{exchangerates.py,main.py,pyproject.toml,README.md,.github/workflows/**}`, 4 matches

Searched for regex `exchange rate|exchangerates|scheduler|cron|workflow|GitHub Actions|pyproject|dependencies|python` (`hai5016-project`), 200 results

Read [](file:///workspaces/hai5016-project/exchangerates.py#1-1), lines 1 to 260

Read [](file:///workspaces/hai5016-project/README.md)

Read [](file:///workspaces/hai5016-project/main.py)

Read [](file:///workspaces/hai5016-project/pyproject.toml)

Searched for files matching `hai5016-project` · `.github/workflows/**`, no matches

Searched for regex `if __name__ == "__main__"|save_daily_rates_to_supabase|get_krw_conversions` (`**/exchangerates.py`), 5 results

Read [](file:///workspaces/hai5016-project/exchangerates.py#261-261), lines 261 to 376

Read [](file:///workspaces/hai5016-project/.github/copilot-instructions.md#60-60), lines 60 to 80

Read memory

I found a direct script entry point already: running exchangerates.py will fetch and save fresh rates. Next I’m checking its runtime requirements and whether the repo needs any small hardening so GitHub Actions can run it non-interactively.

Read [](file:///workspaces/hai5016-project)

Read [](file:///workspaces/hai5016-project/exchangerates.py#1-1), lines 1 to 260

Read [](file:///workspaces/hai5016-project/exchangerates.py#261-261), lines 261 to 376

Read [](file:///workspaces/hai5016-project/README.md)

The script already supports scheduler-style execution because it reads environment variables directly and has a `__main__` entry point. I’m adding a GitHub Actions workflow that runs it at a Seoul-morning UTC cron time, then I’ll do a narrow validation of the new workflow file.

Created 3 todos

Generating patch (75 lines) in [](file:///workspaces/hai5016-project/.github/workflows/update-exchange-rates.yml), [](file:///workspaces/hai5016-project/README.md)


```

```

```

```
The workflow and docs are in place. I’m doing a focused validation now to catch YAML or file-level issues before I wrap this up.

Checked [](file:///workspaces/hai5016-project/.github/workflows/update-exchange-rates.yml), [](file:///workspaces/hai5016-project/README.md), no problems found

Read [](file:///workspaces/hai5016-project/.github/workflows/update-exchange-rates.yml)

Completed: *Add scheduled GitHub workflow* (1/3)

GitHub Actions is set up to run the exchange-rate script every day at 06:00 Korea time. The workflow is in update-exchange-rates.yml, and I added setup notes in README.md.

It uses `uv sync --frozen` and then runs `uv run python exchangerates.py`, with values read from GitHub repository secrets instead of a local .env file. I also did a file-level validation and found no errors in the new workflow or README.

Next steps:
1. Add these repository secrets in GitHub: `EXCHANGE_RATE_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, and optionally `SUPABASE_CONNECTION_STRING`.
2. Open the Actions tab in GitHub and run `Update exchange rates` once manually to confirm the secrets and database write path are correct.

If you want, I can also add a second workflow that only logs the latest fetched rates without writing to Supabase, so you have a safer test job.

Made changes.