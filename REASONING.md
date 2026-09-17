This document records design decisions, architecture, and reasoning for Pharmadost.

Problem understanding
- Build a small full-stack pharmacy stock manager that supports batches, FEFO dispensing, expiry alerts, search, pagination and authentication.

Architecture decisions
- Flask with server-rendered templates keeps frontend minimal and avoids extra build steps.
- SQLite for simplicity; SQLAlchemy ORM for ease of use.

Database design
- `User` for authentication.
- `Medicine` for medicines.
- `Batch` for batches linked to a medicine with expiry_date and quantity.

FEFO algorithm
- Query non-expired batches ordered by `expiry_date` ascending and consume from earliest expiry first until quantity satisfied. Use DB transaction to avoid race conditions.

Expiry handling
- Sellable stock uses batches with `expiry_date >= today`.

Authentication
- JWT (Flask-JWT-Extended) with password hashing via Werkzeug.

Search, pagination, sorting
- Basic query params implemented on `GET /api/medicines` supporting `search`, `page`, `limit`, `sort`, `order`.

Testing
- Pytest tests cover registration/login, creation flows, FEFO behavior, expiry alerts and search.

Trade-offs and future improvements
- Frontend is intentionally minimal; could migrate to SPA for richer UX.
- No role-based permissions or audit logs; these could be added.
