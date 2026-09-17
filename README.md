# Pharmadost

Pharmadost is a minimal pharmacy stock management system built as a timed coding challenge. It helps pharmacists manage medicine batches, track sellable stock, dispense using FEFO (First-Expiry-First-Out), search medicines, and view expiry alerts.

Features
- User registration and JWT authentication
- Medicines CRUD
- Batch management with expiry dates
- Sellable stock calculation (excludes expired batches)
- FEFO dispensing with DB transaction
- Expiry alerts API
- Simple responsive UI using Flask templates and vanilla JS

Tech stack
- Python 3, Flask, Flask-SQLAlchemy
- SQLite
- Flask-JWT-Extended

Setup
1. Create a virtualenv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the app:

```bash
python app.py
```

This will create `pharmadost.db` and seed demo data (user `admin` / `password`).

Testing

Run tests with:

```bash
pytest -q
```

API Endpoints

- `POST /api/auth/register` – register
- `POST /api/auth/login` – login
- `GET /api/auth/me` – current user
- `GET /api/medicines` – list medicines (supports `search`, `page`, `limit`, `sort`, `order`)
- `POST /api/medicines` – create medicine
- `GET /api/medicines/<id>` – medicine detail
- `PUT /api/medicines/<id>` – update
- `DELETE /api/medicines/<id>` – delete
- `GET /api/medicines/<id>/batches` – list batches
- `POST /api/medicines/<id>/batches` – create batch
- `PUT /api/batches/<id>` – update batch
- `POST /api/medicines/<id>/dispense` – dispense quantity using FEFO
- `GET /api/alerts/expiry?days=30` – expiry alerts

