# PhishGuard local verification

Use Python 3.12 and the checked-in dependency lock. This preserves the scikit-learn version matched to the bundled model.

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pytest -q
```

On Windows, use `.venv\Scripts\python.exe`. The tests use Flask test clients, isolated SQLite data and fake external-service configuration. Translation and remote storage require separate credentials and integration testing. Use the checked-in classifier artifact and its matching package versions. Keep user-submitted serialized model files out of trusted model loading.

The [project documentation](../PROJECT_DOCUMENTATION.md) describes app architecture. [Training code](../train_model.py) and [metrics](../models/metrics.json) document the packaged model's reported experiment.
