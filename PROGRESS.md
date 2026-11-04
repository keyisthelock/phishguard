# PhishGuard — live build progress

- [x] Flask application and responsive interface
- [x] Password-hashed authentication and server-enforced user/admin roles
- [x] Trained TF-IDF + Logistic Regression baseline on UCI SMS Spam Collection
- [x] URL structure analysis, estimated risk and explanations
- [x] Private scan history and deletion
- [x] Personal dashboard and aggregate administrator dashboard
- [x] Azure Translator adapter with customer-owned environment credentials
- [x] SQLite / Azure SQL provider configuration
- [x] Integration and security tests (28 passed)
- [x] Browser visual review and guest navigation checks
- [ ] Live Azure verification (needs resource credentials)

Model evaluation: 1,035 held-out messages, 97.68% accuracy, 90.91% spam F1.
These are SMS spam benchmark results, not phishing detection accuracy claims.

Credentials go in `.env` copied from `.env.example`. Never commit this file.

UI revision: frosted glass surfaces, hover and entrance motion, reduced-motion support, separate Azure credential form, temporary guest history/overview, history search/filter, clear input, copy result and text report download.
Azure Translator keys entered through the form remain in server memory, isolated by browser session. Live Azure still needs real credentials.

Platform upgrade completed: dark/light responsive design, separate message/URL modes, safe phrase highlighting, optional text previews, normalized result/indicator/feedback tables and migration, advanced analytics, feedback review, CSV export and deletion, education lessons and local learning challenge. See UPGRADE_NOTES.md for current verification and limitations.

Reference-led redesign completed: warm editorial palette, full-width header, poster typography, original animated CSS signal lens, mobile menu, and matching scanner/dashboard/learning styles. See DESIGN_NOTES.md.
