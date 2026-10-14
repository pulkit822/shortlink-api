import os
import secrets
import string
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import schemas
from .database import Base, engine, get_db
from .models import Click, Link, User
from .security import create_token, current_user, hash_password, verify_password

ALPHABET = string.ascii_letters + string.digits
RESERVED = {"auth", "links", "health", "docs", "redoc", "openapi.json"}
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="ShortLink API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@app.post("/auth/register", response_model=schemas.Token, status_code=201)
def register(body: schemas.Credentials, db: Session = Depends(get_db)):
    user = User(email=body.email.lower(), password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already registered")
    return schemas.Token(access_token=create_token(user.id))


@app.post("/auth/login", response_model=schemas.Token)
def login(body: schemas.Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return schemas.Token(access_token=create_token(user.id))


def _out(link: Link, clicks: int = 0) -> schemas.LinkOut:
    return schemas.LinkOut(
        code=link.code,
        target_url=link.target_url,
        short_url=f"{BASE_URL}/{link.code}",
        created_at=link.created_at,
        clicks=clicks,
    )


@app.post("/links", response_model=schemas.LinkOut, status_code=201)
def create_link(body: schemas.LinkCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.custom_code and body.custom_code.lower() in RESERVED:
        raise HTTPException(400, "Reserved code")
    for _ in range(5):
        code = body.custom_code or "".join(secrets.choice(ALPHABET) for _ in range(7))
        link = Link(code=code, target_url=str(body.url), owner_id=user.id)
        db.add(link)
        try:
            db.commit()
            return _out(link)
        except IntegrityError:
            db.rollback()
            if body.custom_code:
                raise HTTPException(409, "Code already taken")
    raise HTTPException(500, "Could not allocate a short code")


@app.get("/links", response_model=list[schemas.LinkOut])
def list_links(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Link, func.count(Click.id))
        .outerjoin(Click, Click.link_id == Link.id)
        .where(Link.owner_id == user.id)
        .group_by(Link.id)
        .order_by(Link.created_at.desc())
    ).all()
    return [_out(link, n) for link, n in rows]


def _owned(code: str, user: User, db: Session) -> Link:
    link = db.scalar(select(Link).where(Link.code == code, Link.owner_id == user.id))
    if link is None:
        raise HTTPException(404, "Link not found")
    return link


@app.get("/links/{code}/stats", response_model=schemas.Stats)
def stats(code: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    link = _owned(code, user, db)
    day = func.date(Click.clicked_at)
    rows = db.execute(
        select(day, func.count(Click.id)).where(Click.link_id == link.id).group_by(day).order_by(day)
    ).all()
    return schemas.Stats(
        code=code,
        total_clicks=sum(n for _, n in rows),
        per_day=[schemas.DayCount(day=str(d), clicks=n) for d, n in rows],
    )


@app.delete("/links/{code}", status_code=204)
def delete_link(code: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(_owned(code, user, db))
    db.commit()
    return Response(status_code=204)


@app.get("/{code}")
def redirect(code: str, request: Request, db: Session = Depends(get_db)):
    link = db.scalar(select(Link).where(Link.code == code))
    if link is None:
        raise HTTPException(404, "Short link not found")
    db.add(Click(link_id=link.id, user_agent=(request.headers.get("user-agent") or "")[:512]))
    db.commit()
    return RedirectResponse(link.target_url, status_code=307)
