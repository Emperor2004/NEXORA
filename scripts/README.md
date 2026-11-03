# Repository scripts

All scripts resolve paths from their own location, so they can be run from any
working directory. They never remove databases or model artifacts.

## Local development

- `setup/check-prerequisites.ps1` checks Python, Node, npm, and the backend
  virtual environment.
- `setup/verify-environment.ps1` checks local configuration and model files.
- `setup/setup-backend.ps1` creates `backend/.venv` when needed and installs
  `backend/requirements.txt`.
- `setup/setup-frontend.ps1` installs the locked frontend dependencies.
- `dev/start-backend.ps1` starts FastAPI at `http://127.0.0.1:8000`.
- `dev/start-frontend.ps1` starts Vite at `http://127.0.0.1:5173`.
- `dev/start-nexora.ps1` opens both local servers and records their process
  IDs in ignored `.nexora-dev/` state; `dev/stop-nexora.ps1` stops only those
  recorded server processes after checking their command lines.

## Model metadata and checks

```powershell
backend\.venv\Scripts\python.exe scripts\models\validate-model-config.py
backend\.venv\Scripts\python.exe scripts\models\evaluate-fixtures.py
```

The fixture tool checks source/evidence consistency only. It does not call a
model and makes no accuracy claim.

## Quality checks

`quality/run-backend-tests.ps1` runs a focused offline regression suite for
agent contracts, the workflow pipeline, multi-source discovery, extraction,
and LinkedIn metadata parsing. It excludes live-network checks and an API
TestClient scenario that currently stalls on Windows. `quality/run-frontend-tests.ps1`
builds and runs frontend unit tests. Temporary files and npm cache are directed
to ignored `data/cache/` on the project drive. `quality/run-all-tests.ps1` runs
both plus model metadata and fixture-integrity checks.
