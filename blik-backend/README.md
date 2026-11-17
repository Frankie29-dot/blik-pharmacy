# Blik Pharmacy API: step 1

Backend for the refill form on the Blik Pharmacy website (Port Harcourt).
Customers submit refill requests from the site; staff log in to see them and update their status.

**Stack:** Python, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (Neon-compatible).
**Not included yet:** payments, SMS/WhatsApp/email notifications (later steps).

## What it does

| Endpoint | Who | What |
|---|---|---|
| `POST /refills` | public | Save a refill request (rate-limited per IP) |
| `POST /auth/login` | staff | Exchange email + password for a JWT |
| `GET /refills` | staff | List requests, newest first. `?status=new`, `limit`, `offset` |
| `PATCH /refills/{id}` | staff | Set status: `new`, `preparing`, `ready`, `collected` |
| `GET /health` | anyone | Returns `{"status": "ok"}` |

Interactive docs are at `/docs` once the server is running. Use the **Authorize** button there
to log in as staff (enter the email in the `username` field).

## Setup

You need Python 3.11 or 3.12 and PostgreSQL 14+. (Python 3.13 is not supported yet because `passlib` needs a module that was removed in 3.13.)

**1. Create the database in Neon**

Create a Neon project and copy its **pooled** connection string. In `DATABASE_URL`, replace
the prefix `postgres://` or `postgresql://` with `postgresql+psycopg://` and keep
`?sslmode=require` at the end. The pooled URL is preferred for the web API.

**2. Install dependencies**

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. Configure**

```bash
cp .env.example .env
```

Edit `.env`:

- `DATABASE_URL`: use the Neon pooled URL, with the `postgresql+psycopg://` prefix and `sslmode=require`.
- `SECRET_KEY`: generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- `CORS_ORIGINS`: your website's exact origin, e.g. `https://www.yoursite.com` (no path, no trailing slash, not `*`). For local testing use `http://127.0.0.1:5500`.

**4. Create the tables**

```bash
alembic upgrade head
```

**5. Create the first staff account**

```bash
python -m scripts.create_staff --email you@yourpharmacy.com --role pharmacist
```

You'll be asked for the password at a hidden prompt (minimum 10 characters). Run it again to add more staff. Roles are `pharmacist` and `assistant`; both can currently see and update requests.

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Run the migration once against Neon before starting the deployed API. Set the same
environment variables in your hosting provider; never upload `.env` or put the Neon
password in frontend code.

The frontend API URL is configured in the `blik-api-url` meta tag in
`public/index.html`. Set it to the deployed API origin, for example
`https://api.your-site.example`, before publishing the website. The API must include
the frontend origin in `CORS_ORIGINS`.

Add `--reload` while developing.

Try it:

```bash
# Customer submits a refill (what the website form does)
curl -X POST http://127.0.0.1:8000/refills \
  -H "Content-Type: application/json" \
  -d '{"prescription_number":"RX-1001","date_of_birth":"1985-03-21","phone":"0903 123 4567","method":"pickup"}'

# Staff log in
curl -X POST http://127.0.0.1:8000/auth/login \
  -d "username=you@yourpharmacy.com" -d "password=YOUR_PASSWORD"

# Staff list new requests, then mark one as preparing
curl "http://127.0.0.1:8000/refills?status=new" -H "Authorization: Bearer TOKEN"
curl -X PATCH http://127.0.0.1:8000/refills/1 \
  -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{"status":"preparing"}'
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests run against an in-memory SQLite database and their own test settings, so they don't need PostgreSQL and never touch your real data or `.env`.

## Behaviour worth knowing

- **Phone numbers:** Nigerian mobile numbers only. `0903...`, `+234903...`, `234903...` and spaced or dashed versions are all stored as `+234903...`. Landlines are rejected, since later steps will need to message customers.
- **Customers:** matched on phone **and** date of birth. A phone number alone isn't unique, because family members often share one. Same phone + same date of birth reuses the customer; otherwise a new customer row is created.
- **Prescription numbers:** letters, digits, `-` and `/`, 3 to 40 characters; stored in upper case.
- **Rate limits:** 5 refill submissions per minute per IP and 10 login attempts per minute per IP (change in `.env`). Counters are kept in memory per process, which is fine for a single server. Many customers on one mobile network can share an IP, so don't set the refill limit too low.
- **Behind nginx or another reverse proxy:** the limiter needs the visitor's real IP. Start uvicorn with `--forwarded-allow-ips 127.0.0.1` (or the proxy's address) and make sure the proxy sets `X-Forwarded-For`. Without this, every visitor looks like the proxy and shares one limit.
- **Status changes:** staff can set any status at any time, so mistakes can be corrected.
- **Tokens:** valid for `ACCESS_TOKEN_EXPIRE_MINUTES` (default 8 hours). The staff account is re-checked on every request, so deleting a staff row cuts off access immediately.

## Privacy: phone and prescription numbers are never logged

- No application code logs request data.
- SQLAlchemy runs with `hide_parameters=True`, so database errors don't print the values being saved. Don't turn on `echo=True`.
- Validation errors (422) don't echo submitted values back.
- The public confirmation returns only the reference number, status, method and time.
- There's a test for the logging rule. Keep it passing when you add features, and avoid logging request bodies in any proxy or monitoring tool you add.

## Project layout

```
app/
  main.py          app, CORS, error handling
  config.py        settings from .env
  database.py      engine and session
  models.py        customers, refill_requests, staff
  schemas.py       Pydantic request/response models
  phone.py         Nigerian phone normalisation
  security.py      password hashing (argon2), JWT
  deps.py          "current staff" dependency
  ratelimit.py     per-IP rate limiter
  routers/         refills.py, auth.py
alembic/           migrations
scripts/create_staff.py
tests/
```

To change the database later, edit `app/models.py`, then run
`alembic revision --autogenerate -m "describe the change"`, review the generated file, and run `alembic upgrade head`.
