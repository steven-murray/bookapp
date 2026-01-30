# Quick Setup Guide

Follow these steps to get your Book Tracker app running:

## 1. Install uv
```powershell
pip install uv
```

Or using the standalone installer:
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

## 2. Sync Dependencies (creates virtual environment automatically)
```powershell
uv sync
```

## 3. Set Up Environment
```powershell
Copy-Item .env.example .env
```

Edit `.env` file and change the SECRET_KEY to something secure.

## 4. Initialize Database
```powershell
uv run python -c "from bookapp.app import app, db; app.app_context().push(); db.create_all(); print('Database created!')"
```

## 5. Create Admin User
```powershell
uv run python scripts/create_admin.py
```

## 6. Run the Application
```powershell
uv run python scripts/run.py
```

## 7. Access the App
Open your browser to: http://localhost:5000

---

That's it! You're ready to start tracking books. 📚
