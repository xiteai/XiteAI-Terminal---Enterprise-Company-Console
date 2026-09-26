from __future__ import annotations

from pydantic import BaseModel, Field


class EmailCheck(BaseModel):
    local: str = Field(max_length=40)


class JoinBody(BaseModel):
    # account
    local: str = Field(max_length=40)
    password: str = Field(max_length=200)
    full_name: str = Field(min_length=2, max_length=80)
    preferred_name: str = Field(default="", max_length=40)
    # the role
    level: str
    title: str = Field(min_length=2, max_length=80)
    department: str
    employment_type: str
    start_date: str = Field(default="", max_length=10)
    # about you
    photo: str = Field(default="", max_length=400_100)
    dob: str = Field(max_length=10)
    gender: str = Field(default="", max_length=30)
    phone: str = Field(max_length=24)
    personal_email: str = Field(max_length=160)
    city: str = Field(max_length=80)
    address: str = Field(default="", max_length=300)
    # emergency contact
    emergency_name: str = Field(max_length=80)
    emergency_relation: str = Field(max_length=40)
    emergency_phone: str = Field(max_length=24)
    # background
    qualification: str = Field(default="", max_length=40)
    institution: str = Field(default="", max_length=120)
    graduation_year: str = Field(default="", max_length=4)
    experience_years: str = Field(default="", max_length=4)
    previous_company: str = Field(default="", max_length=120)
    skills: str = Field(default="", max_length=400)
    linkedin: str = Field(default="", max_length=200)
    portfolio: str = Field(default="", max_length=200)
    about: str = Field(default="", max_length=1000)
    # agreement
    agree_accurate: bool = False
    agree_storage: bool = False
    website: str = Field(default="", max_length=200)   # honeypot: people never see this field
