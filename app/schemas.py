from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class Credentials(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LinkCreate(BaseModel):
    url: HttpUrl
    custom_code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{3,32}$")


class LinkOut(BaseModel):
    code: str
    target_url: str
    short_url: str
    created_at: datetime
    clicks: int = 0


class DayCount(BaseModel):
    day: str
    clicks: int


class Stats(BaseModel):
    code: str
    total_clicks: int
    per_day: list[DayCount]
