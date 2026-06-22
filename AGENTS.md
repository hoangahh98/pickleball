# Repository Guidelines

## Project Structure & Module Organization
This repository is a Flask pickleball tournament application. The main web entry point is `app.py`, with supporting modules split by responsibility: `auth.py` for authentication helpers, `config.py` for configuration, `models.py` for data access structures, `services.py` for application services, `knockout_logic.py` for bracket logic, and `logging_service.py` for log handling.

HTML templates live in `templates/`. Static files and user-uploaded images live under `static/`, currently `static/uploads/`. Avoid committing generated cache files such as `__pycache__/`.

## Build, Test, and Development Commands
Create and activate a virtual environment before installing dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the app locally with:

```powershell
python app.py
```

The development server listens on `0.0.0.0:5000` as configured at the bottom of `app.py`. For production-style execution, use Gunicorn on a compatible Unix-like host:

```bash
gunicorn app:app
```

## Coding Style & Naming Conventions
Use standard Python style with 4-space indentation, clear function names in `snake_case`, and constants in `UPPER_SNAKE_CASE`. Keep route handlers in `app.py` thin where possible by moving reusable logic into `services.py`, `models.py`, or domain-specific modules such as `knockout_logic.py`.

Template filenames are Vietnamese and descriptive, for example `them_giai_dau.html` and `sua_van_dong_vien.html`; follow that pattern for new templates.

## Testing Guidelines
No automated test suite is currently present. When adding tests, prefer `pytest`, place tests in a new `tests/` directory, and name files `test_*.py`. Focus first on bracket generation, authentication behavior, and database-facing service functions. Run tests with:

```powershell
pytest
```

## Commit & Pull Request Guidelines
Recent commits use short Vietnamese summaries such as `thay toan bo app pickleball`. There is no strict convention yet; keep future commit messages concise, imperative, and specific to the change, for example `them loc vdv theo giai`.

Pull requests should include a short description, manual test steps, database or configuration changes, and screenshots for visible UI updates. Link related issues when available.

## Security & Configuration Tips
Keep secrets and deployment-specific settings out of source control. Use environment variables or a local `.env` file for values consumed by `config.py`, including database credentials and Flask secret keys. Do not commit uploaded private images or production data.
