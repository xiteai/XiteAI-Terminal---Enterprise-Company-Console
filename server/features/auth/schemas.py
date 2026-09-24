from __future__ import annotations

from pydantic import BaseModel, Field


class LoginBody(BaseModel):
    email: str = Field(max_length=160)
    password: str = Field(max_length=200)
    code: str = Field(default="", max_length=12)
