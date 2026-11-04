# Customer demo / local handoff

## Launch

Open this folder in VS Code. Run `Start-PhishGuard.ps1` from its terminal, or use `python app.py` in the configured environment. The app opens at http://127.0.0.1:5000/. Keep the server terminal running.

## Demonstration sequence

1. Continue as guest. Load **Everyday message** and analyze. Explain that lower risk is not a guarantee.
2. Load **Bank alert** and analyze. Show the model spam signal, separate rule score, highlighted phrases and recommended response.
3. Load **Lookalike URL**. Explain the hostname, path, query-name checks and why the domain resembles a brand. The URL is never opened.
4. Copy or download the result. Open its detail and submit feedback. Guest feedback stays in this temporary session.
5. Visit History. Search/filter records and export CSV. Text previews were not retained unless opted in.
6. Visit Overview. Select a date range and show the actual classification/activity/indicator/feedback counts.
7. Open Learn & protect and try the Scam challenge. Explain the local practice score.
8. Sign in to a registered account and save a scan. Show database-backed history. Administrator accounts alone can open `/admin` and review feedback.
9. Show the Azure page separately. Credentials and cloud verification are deferred; do not claim the current database is Azure SQL.

All sample messages are fictional and use reserved .example domains. Use sample data rather than real bank messages or verification codes.

## What is finished

Local full-stack functionality, UI, testing, migration, source packaging, documentation and Azure verification tooling.

## What is intentionally deferred

Translator provisioning/credentials, Azure SQL resource creation and driver installation, live cloud connectivity tests, and hosting. Follow AZURE_SETUP.md when the account owner is ready. These are external setup tasks; they are not presented as completed or simulated.
