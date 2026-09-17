# Pharmadost

A small full-stack pharmacy stock management app (Flask + SQLite) with FEFO dispensing, expiry alerts, and simple reorder notifications.

## Setup

1. Create and activate a Python virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Environment variables (optional):

- `SECRET_KEY` — Flask secret key (defaults to `dev-secret`)
- `JWT_SECRET_KEY` — JWT signing secret (defaults to `jwt-secret`)
- `DATABASE_URL` — database URL (defaults to `sqlite:///pharmadost.db`)

4. Database initialization and seed:

- On first run the app will create the SQLite file defined by `DATABASE_URL` (default `pharmadost.db`) and run the embedded seed script to populate demo medicines and batches.
- If you change models and need a fresh DB during development, delete `pharmadost.db` and restart the app; `create_app()` will call `db.create_all()` and `seed_data()`.

## Run

Start the app:

```bash
python app.py
```

The app runs in Flask debug mode by default when launched this way.

## Tests

Run the test suite with:

```bash
pytest -q
```

## Debugging

- Flask debug mode is enabled when running `python app.py`, errors show tracebacks in the terminal and browser.
- If you see errors like `no such column: batch.in_date` or similar schema drift, inspect the on-disk DB schema with SQLite PRAGMA (example):

```sql
PRAGMA table_info('batch');
```

You can run that via a small Python snippet inside the app context or use the `sqlite3` CLI.

## API Endpoints

All API endpoints are JSON and most are protected by JWT (send `Authorization: Bearer <token>`).

Routes are grouped by blueprint; below are the endpoints implemented in the codebase.

**Authentication (routes/auth.py)**

- POST `/api/auth/register` — create a new user account (body: `username`, `password`).
- POST `/api/auth/login` — authenticate and return JWT access token (body: `username`, `password`).
- GET `/api/auth/me` — return current user info (requires JWT).

**Medicines (routes/medicines.py)**

- GET `/api/medicines` — list medicines with pagination/sorting (query: `page`, `limit`, `sort`, `order`, `search`).
- GET `/api/medicines/search` — search medicines by `q` (searches `name` and `generic_name`), supports pagination and sorting; returns `sellable_stock` and boolean `in_date`.
- GET `/api/dashboard/summary` — returns summary counts: total medicines, total sellable stock, expiring soon count.
- POST `/api/medicines` — create a new medicine (body: `name`, optional `generic_name`, `manufacturer`).
- GET `/api/medicines/<id>` — get a medicine with its batches and computed `sellable_stock`.
- PUT `/api/medicines/<id>` — update medicine metadata.
- DELETE `/api/medicines/<id>` — delete a medicine.
- GET `/api/medicines/<id>/batches` — list batches for a medicine (supports `sort` and `order`).
- POST `/api/medicines/<id>/batches` — create a batch (body: `batch_number`, `quantity`, `in_date` (YYYY-MM-DD), `expiry_date` (YYYY-MM-DD)).

**Batches / Dispense (routes/batches.py)**

- PUT `/api/batches/<id>` — update a batch (quantity or expiry_date).
- POST `/api/medicines/<med_id>/dispense` — dispense a quantity from a medicine using FEFO logic (body: `quantity`).

**Alerts & Clock (routes/alerts.py)**

- GET `/api/alerts/expiry` — list batches expiring within `days` (query param `days`, default 30).
- POST `/api/clock` — quarantine expired batches and report counts (runs the inventory "clock").

**Outbox / Notifications (routes/outbox.py)**

- GET `/api/outbox` — list unresolved outbox notifications (paginated `page`, `limit`).
- POST `/api/outbox/<id>/resolve` — mark an outbox notification resolved.

If you add routes, follow the existing blueprint pattern and register the blueprint in `app.create_app()`.

---

If you'd like, I can add a short Quickstart script or Dockerfile next.
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

