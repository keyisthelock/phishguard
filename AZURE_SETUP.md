# Azure setup — reserved for the next session

The local demo is complete and works without Azure. Live provisioning and verification are intentionally deferred. No Azure resources were created or charged by this project session.

## 1. Create the SQL database

1. Sign in to the [Azure SQL hub](https://aka.ms/azuresqlhub) with an active Azure subscription.
2. If available for your subscription, select **Start free**. Microsoft documents a free database tier with limits; availability depends on the subscription. Keep the option to pause when free limits are reached. Do not select paid continuation for this demo.
3. Choose a project resource group, a database name such as `phishguard`, and create a logical SQL server with a globally unique name. Choose a region appropriate for the account. For a simple demo, SQL authentication works with the existing connector; enter the administrator password privately and keep it out of chat, screenshots and Git.
4. Review the cost summary before selecting Create. If no free option appears or the summary is not zero, stop and decide on a budget first. Resource creation is an account-owner action.
5. Under the SQL server's Networking settings, allow only your current client IP. Do not enable all IP addresses. Keep secure transport and certificate validation.
6. In the database's Connection strings page, choose the ODBC example.

Official references: [free-tier limits and pause behavior](https://learn.microsoft.com/en-us/azure/azure-sql/database/free-tier), [create a single database](https://learn.microsoft.com/en-us/azure/azure-sql/database/single-database-create-quickstart).

## 2. Install the client driver and set local credentials

Install the Windows x64 **Microsoft ODBC Driver 18 for SQL Server** from [Microsoft's download page](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server). Use the matching architecture if your computer is not x64.

Copy `.env.example` to `.env` if you have not already done so, then privately set:

```dotenv
AZURE_SQL_CONNECTION_STRING=Driver={ODBC Driver 18 for SQL Server};Server=tcp:YOUR-SERVER.database.windows.net,1433;Database=phishguard;Uid=YOUR-LOGIN;Pwd={YOUR-PASSWORD};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
```

Use the portal's correctly escaped ODBC syntax if a password contains special characters. Do not put the connection string in command-line arguments. Never commit `.env`. Generate a random `SECRET_KEY` for hosted deployment.

## 3. Verify and initialize

In the VS Code terminal, after activating the project's environment:

```powershell
python azure_diagnostics.py        # offline configuration status, no secrets
python azure_diagnostics.py --sql  # live SELECT 1; does not create or migrate data
python app.py                     # creates the application tables on the configured database
```

Startup applies the additive schema migration. Stop the app before switching providers. SQLite users and history are not automatically copied to Azure SQL; register a new account there. Visit `/health` and confirm `database` reports `azure-sql`, then save a synthetic scan and check History and Overview.

For the DBMS / DP-900 demonstration, use Query Editor with synthetic records:

```sql
SELECT label, COUNT(*) AS scans, AVG(CAST(score AS FLOAT)) AS average_risk
FROM scans GROUP BY label;
SELECT u.username, COUNT(s.id) AS saved_scans
FROM users u LEFT JOIN scans s ON s.user_id = u.id
GROUP BY u.username;
SELECT d.mode, COUNT(*) AS analyses
FROM detection_results d GROUP BY d.mode;
SELECT description, COUNT(*) AS observations
FROM warning_indicators GROUP BY description;
```

Explain managed relational storage, primary/foreign keys, indexes, transactions, operational inserts and aggregate reporting. SQL Database is the data service; Translator is a separate AI service.

## 4. Connect Translator

Create a Translator resource, review its selected tier and then open **Keys and Endpoint**. In PhishGuard's **Azure** page, enter the key and region privately and select Save connection. The key is held only in server memory for this browser session. Select **Test Translator connection** to send a synthetic Hindi sentence. This verifies service connectivity, not multilingual classification accuracy.

Select Hindi in the scanner for a demo. A translation outage, rejected key, access denial or quota limit is shown as a user-facing error, without exposing the key. [Microsoft Translator reference](https://learn.microsoft.com/en-us/azure/ai-services/translator/text-translation/reference/v3/reference).

## Common blockers

| Symptom | Next check |
|---|---|
| Driver missing | Install Driver 18 from Microsoft; the built-in `SQL Server` driver is not the required driver |
| SQL connection fails | Firewall IP, logical server name, target database, credentials and encrypted ODBC settings |
| Translator rejects key | Correct resource key and exact region; resource/subscription access |
| Translator rate/quota limit | Resource usage and quota; wait before retrying |
| History vanishes after switching | SQL and SQLite are separate databases; accounts are separate |

Use one server process for this demo. Shared guest state and distributed throttling are required before scaling to multiple instances. Hosting itself is a separate deployment step, not something claimed as completed here.
