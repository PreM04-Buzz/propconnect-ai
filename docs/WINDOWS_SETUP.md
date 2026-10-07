# Windows setup

Tested commands for Windows 10/11 using **PowerShell**. Run each block in order.

## 1. Install the tools (once)

Open PowerShell and run:

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.12 -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Docker.DockerDesktop -e
winget install --id GitHub.cli -e
```

Then:

1. **Restart the computer** (Docker needs it, and new tools need a fresh PATH).
2. Open **Docker Desktop**, accept the terms, and wait for "Engine running". If it asks to install or update WSL, say yes.
3. Allow PowerShell to run the Python virtual environment script (once):

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Check everything:

```powershell
git --version; py -3.12 --version; node --version; docker --version; gh --version
```

## 2. Get the code

```powershell
gh auth login                      # GitHub.com → HTTPS → Yes → Login with a web browser
cd $HOME
git clone https://github.com/PreM04-Buzz/propconnect-ai.git
cd propconnect-ai
```

## 3. Database

```powershell
docker compose up -d db
docker ps                          # wait until propconnect-db shows (healthy)
```

## 4. Backend (PowerShell window 1)

```powershell
cd $HOME\propconnect-ai\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item ..\.env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
notepad .env                       # paste the secret as JWT_SECRET, set ADMIN_PASSWORD, save
alembic upgrade head
python -m app.scripts.seed
pytest
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## 5. Data and demo records (PowerShell window 2)

Copy `realtor-data.zip.csv` (or `archive.zip`) and `Metro_invt_fs_uc_sfrcondo_sm_month.csv`
into `propconnect-ai\data\raw\` (create the `raw` folder if needed). Then:

```powershell
cd $HOME\propconnect-ai\backend
.\.venv\Scripts\Activate.ps1
python -m app.scripts.prepare_data
python -m app.scripts.load_data
python -m app.scripts.seed_demo
```

## 6. Frontend (PowerShell window 3)

```powershell
cd $HOME\propconnect-ai\frontend
npm install
npm run dev
```

Open http://localhost:5173 and sign in as an agent:
`maria.lopez@propconnect-demo.com` / the `DEMO_PASSWORD` in `.env` (default `DemoAgent2026`).

## Every day after that

1. Start Docker Desktop.
2. Window 1: `cd $HOME\propconnect-ai\backend; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload`
3. Window 2: `cd $HOME\propconnect-ai\frontend; npm run dev`

## Troubleshooting

| Problem | Fix |
|---|---|
| `Activate.ps1 cannot be loaded` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once |
| `py` not found | Reopen PowerShell; or use the full path `$env:LOCALAPPDATA\Programs\Python\Python312\python.exe` |
| `port 5432 is already allocated` | Another PostgreSQL is running. Stop it in Services, or change the port in `docker-compose.yml` to `"5433:5432"` and in `DATABASE_URL` |
| `connection refused` on `alembic upgrade` | Docker Desktop isn't running yet, or the container is still starting |
| Forgot a password | `python -m app.scripts.reset_password admin@propconnect-demo.com NewPassword123` |
| Want fresh demo data | `python -m app.scripts.seed_demo --reset` |
| Line ending warnings from Git | Harmless. Optional: `git config --global core.autocrlf true` |
