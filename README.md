# hai5016-project

## Daily exchange-rate refresh with GitHub Actions

This repository now includes a scheduled workflow at [.github/workflows/update-exchange-rates.yml](/workspaces/hai5016-project/.github/workflows/update-exchange-rates.yml).

The workflow:
- runs every day at 06:00 Korea time
- can also be started manually from the GitHub Actions tab
- installs the project with `uv`
- runs `python exchangerates.py` to fetch and save the latest rates

## Required GitHub repository secrets

Add these secrets in GitHub:

- `EXCHANGE_RATE_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_CONNECTION_STRING` (optional if you use `SUPABASE_URL` and `SUPABASE_KEY` instead)

GitHub path:
- Repository -> Settings -> Secrets and variables -> Actions -> New repository secret

## Manual test

After adding the secrets, open the GitHub repository page and run the workflow once:

1. Open the `Actions` tab.
2. Select `Update exchange rates`.
3. Click `Run workflow`.

If the run succeeds, GitHub will keep running it every morning automatically.