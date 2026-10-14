# ShortLink API

A URL shortener backend with JWT authentication and per-link click analytics, built with FastAPI, SQLAlchemy 2.0 and PostgreSQL. It is containerized with Docker, tested with pytest, and has a CI pipeline on GitHub Actions.

**Live demo:** https://shortlink-api-y8xr.onrender.com/docs

> Hosted on Render's free tier. The first request after a period of inactivity may take 30-60 seconds while the service wakes up.

## Features
- User registration and login with PBKDF2-hashed passwords and JWT bearer authentication
- Create short links with a random 7-character code or a custom code
- Collision-safe code generation: uniqueness is enforced by a database constraint with retry, not by check-then-insert
- `GET /{code}` issues a 307 redirect and records a click (timestamp and user agent)
- Per-link analytics: total clicks and clicks per day, aggregated in SQL
- Ownership checks: users can only view stats for, list and delete their own links
- `/health` endpoint that verifies database connectivity

## Tech stack
Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL, PyJWT, pytest, Docker, Docker Compose, GitHub Actions, Render

## API endpoints
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Create an account, returns a JWT |
| POST | `/auth/login` | No | Log in, returns a JWT |
| POST | `/links` | Yes | Create a short link (optional `custom_code`) |
| GET | `/links` | Yes | List your links with click counts |
| GET | `/links/{code}/stats` | Yes | Total clicks and clicks per day |
| DELETE | `/links/{code}` | Yes | Delete a link and its click history |
| GET | `/{code}` | No | Redirect to the original URL and record a click |
| GET | `/health` | No | Health check including database connectivity |

Interactive documentation is available at `/docs`.

## Quick try
```bash
# 1. Register and get a token
curl -X POST https://shortlink-api-y8xr.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "password123"}'

# 2. Create a short link (replace TOKEN with the access_token from step 1)
curl -X POST https://shortlink-api-y8xr.onrender.com/links \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com"}'
```
Open the returned `short_url` in a browser to be redirected.

## Run locally

With Docker (API plus PostgreSQL):
```bash
docker compose up --build
```
The API is then available at http://localhost:8000/docs.

Without Docker (uses SQLite):
```bash
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

## Tests
```bash
pytest --cov=app
```
11 integration tests with 98% coverage, covering authentication, validation, redirects, click analytics, access control between users and cascade deletion. Tests run against SQLite for speed. CI runs them on every push and fails below 90% coverage.

## Project structure
```
app/
  main.py        # routes and app setup
  models.py      # User, Link, Click tables
  schemas.py     # request/response validation
  security.py    # password hashing, JWT, auth dependency
  database.py    # engine and session (SQLite locally, PostgreSQL in production)
tests/           # pytest integration tests
Dockerfile
docker-compose.yml
render.yaml      # Render Blueprint (web service + PostgreSQL)
.github/workflows/ci.yml
```

## Design notes
- **Short codes:** base62, 7 characters (about 3.5 trillion combinations). A unique index guarantees no duplicates even under concurrent requests.
- **Analytics:** click counts per day are computed with `GROUP BY` in SQL rather than in application code.
- **Data integrity:** clicks cascade-delete with their link, and links with their user.
- **Security:** salted PBKDF2-SHA256 password hashes, expiring JWTs, constant-time hash comparison, and `SECRET_KEY` read from the environment.

## Configuration
| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | Database connection string | `sqlite:///./shortlink.db` |
| `SECRET_KEY` | JWT signing key | dev-only value, always set in production |
| `BASE_URL` | Public URL used in `short_url` | `http://localhost:8000` |
| `TOKEN_TTL_MIN` | Token lifetime in minutes | `60` |

## Deployment
Deployed on Render using the `render.yaml` Blueprint, which provisions the Docker web service and a managed PostgreSQL database.

## Possible improvements
- Rate limiting on link creation and login
- Link expiry dates
- Alembic migrations instead of `create_all`
- Redis caching for hot redirects
