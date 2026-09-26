from __future__ import annotations

from pydantic import BaseModel, Field


class PersonPatch(BaseModel):
    level: str | None = None
    title: str | None = Field(default=None, max_length=80)
    department: str | None = Field(default=None, max_length=60)
    employment_type: str | None = Field(default=None, max_length=20)
    reports_to: int | None = None
    pf_number: str | None = Field(default=None, max_length=30)
    uan_number: str | None = Field(default=None, max_length=20)


class NoteBody(BaseModel):
    note: str = Field(default="", max_length=500)
