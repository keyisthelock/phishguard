# PhishGuard platform upgrade

## Audit findings and changes

The existing Flask app already had working authentication, model inference, basic history, aggregate counts and Azure adapters. Its main weaknesses were a single message-centric scan flow, limited URL validation, totals-only analytics, no feedback or education, technical copy on the main screen, and a monolithic schema/route module. Guest state and Azure form keys lived only in process memory.

The upgrade preserves Flask and the trusted trained model, with no new external services or front-end dependencies. Added:

- Ivory/ink/vermilion/yellow editorial design system, original CSS signal-lens art, oversized type, responsive navigation, visible keyboard focus, skip navigation and reduced-motion support. See DESIGN_NOTES.md for the reference direction and visual checks.
- Persistent light/dark preference, asynchronous scanning with an ordinary form fallback, paste/clear/examples, input validation and Ctrl/Cmd+Enter.
- Separate URL mode with HTTP(S) normalization, hostname/port validation, host/path/query inspection, punycode, shortened-link, embedded-user-info and lookalike heuristics. URLs are never fetched.
- Separate model spam signal and rule score, matched phrase highlighting through escaped Jinja text, possible techniques, practical advice and timestamped results. URL-only mode does not claim a model probability.
- Real scan activity, classifications, indicator counts, feedback summaries, recent scans and date ranges. Charts use native progress elements, labels, title tooltips and an accessible data table. No fabricated trends.
- Seven fictional education lessons and a five-question learning challenge with browser-local progress.
- Per-owner scan detail, feedback reports, protected administrator review queue, text report export, CSV history export and deletion controls.
- Metadata-only history by default; redacted preview is a separate opt-in. Stored URL paths, query names/values, translated text and live highlight segments are omitted. Analyzed content is returned for the live result only.
- Modular relational models, URL inspection, analytics, learning content and additive migration. CSRF, role checks, password hashes and secure headers remain in place. Scan/register/feedback limits complement login throttling.

## Database migration

`migrations.py` runs at startup. It creates `detection_results`, `warning_indicators`, `feedback` and `schema_versions`, adds missing scan indexes and backfills normalized result metadata from existing JSON. Existing `users` and `scans` columns are unchanged. Schema version 2 is recorded in the same backfill transaction. Repeated runs do not duplicate data. A pre-upgrade local database backup was saved outside the deliverable in the work directory.

`Scan.result` JSON remains a compatibility snapshot while normalized result and indicator tables support relational relationships. Scan deletion explicitly removes feedback, warning rows and detection metadata in one transaction. Owner checks precede detail, feedback and delete operations. Administrator analytics show aggregates; feedback notes are visible only in the protected review queue.

SQLite execution and repeated migrations were tested. Azure SQL uses SQLAlchemy's existing SQL Server dialect and encrypted ODBC connection configuration, but a live Azure migration remains unverified without credentials. Run only one migration process during deployment; do not start concurrent migrations.

## Run and test

No additional dependencies were introduced. In a normal Windows Python 3.12 installation:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
Copy-Item .env.example .env  # only if .env does not already exist
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000/. Use Continue as guest or register. VS Code includes a Run PhishGuard launch configuration; select the project's Python interpreter first.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m flask --app app:create_app create-admin
```

The locked environment includes pytest. For runtime-only installation use `requirements.txt`; the bundled model is best reproduced with the locked scikit-learn version. Never load an untrusted joblib artifact.

## Validation

28 tests pass, covering authentication, CSRF, admin permissions, cross-user ownership, escaping/redaction, metadata-only storage, URL validation and offline inspection, normalized result records, feedback submission/review/deletion, CSV export, date-filtered analytics, guest isolation, rate limits and repeatable migrations. Node syntax checks cover the two JavaScript assets.

Live browser checks completed: asynchronous message scan and URL-only scan, warning explanations, guest feedback redirect to owned detail, learning challenge scoring, guest overview, 390px mobile layout with no horizontal overflow, 1440px desktop layout, and light/dark switching. The original test failures after the upgrade were assertions expecting text to be stored by default and old status labels; tests now explicitly opt in to previews where needed. The final run has no failing tests.

## Remaining limits

- Azure Translator and Azure SQL still require resource credentials and live verification. Translation-assisted English-model analysis is not validated multilingual phishing detection.
- This model is an English SMS spam baseline (4,136 train / 1,035 held-out deduplicated messages). 90.2% spam precision, 91.6% recall and 90.9% F1 are benchmark results, not phishing accuracy guarantees. Original v1 training timestamp was not recorded; the model page identifies the artifact date separately. No invented confidence or training date is used.
- URL checks are structural heuristics without reputation lookup. Lookalikes can produce false positives. Subdomain display uses label splitting, not a public-suffix registry. The URL model signal is unavailable because no URL classifier is trained.
- Guest history, guest feedback, keys and rate limits are process-local. Use one server worker for this demo. Multi-instance deployment needs shared server-side state, durable guest expiry and distributed throttling.
- Account records persist until owner deletion. Optional redaction is deliberately described as limited, and older records are not silently scrubbed. Feedback is unverified and never automatically retrains the model.
- Review queues support marking feedback reviewed; account deletion/role editing and production-grade audit logging were left out to avoid a rushed privileged management flow.

## Academic mapping

| Subject | Working evidence |
|---|---|
| DBMS | Users/scans/results/indicators/feedback relationships, primary and foreign keys, indexed queries, transactions, migrations and reporting |
| System Design | Flask routes, separate inference/URL/analytics/model modules, async request flow, reusable result template and UI components |
| Cloud Security | Password hashing, sessions, server role/ownership checks, CSRF, CSP, rate limits, environment credentials and Azure connection separation |
| PBL-III / AI-ML | Actual trained TF-IDF + Logistic Regression inference, held-out metrics, explainable rules, honest limitations and feedback for future evaluation |

All six registered core features remain available.
