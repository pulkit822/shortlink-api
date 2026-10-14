# ShortLink API

URL shortener with JWT auth and per-link click analytics. FastAPI, SQLAlchemy 2.0, PostgreSQL, Docker, GitHub Actions CI.

**Live demo:** `<your-render-url>/docs`

## Features
- Register/login with PBKDF2-hashed passwords and JWT bearer auth
- Create short links (random 7-char code or custom), collision-safe via unique constraint + retry
- `GET /{code}` issues a 307 redirect and records a click (timestamp, user agent)
- Per-link stats (total and clicks per day); users can only see and delete their own links
- `/health` endpoint verifies DB connectivity

## Endpoints
| Method | Path | Auth |
|---|---|---|
| POST | /auth/register, /auth/login | no |
| POST | /links | yes |
| GET | /links | yes |
| GET | /links/{code}/stats | yes |
| DELETE | /links/{code} | yes |
| GET | /{code} | no |

## Run locally
```
docker compose up --build        # API + Postgres on :8000
pip install -r requirements-dev.txt && pytest --cov=app   # tests use SQLite
```

## Design notes
- Short codes: base62, 7 chars (~3.5 trillion combinations); uniqueness enforced by DB, not by check-then-insert, so concurrent requests can't collide.
- Click stats are aggregated in SQL (`GROUP BY date`), not in Python.
- Click and link rows cascade-delete with their parent.

## Deploy (Render, free tier)
Push to GitHub, then Render > New > Blueprint > select repo. `render.yaml` provisions the web service and Postgres. Set `BASE_URL` to the service URL.
