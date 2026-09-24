"""The choices the sign-up flow offers. One place to add a department or title."""
from __future__ import annotations

DEPARTMENTS = ["Engineering", "Product", "Design", "Data & AI", "Marketing", "Sales", "Customer Success",
               "People & HR", "Finance", "Operations", "Legal", "Leadership"]

EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Intern", "Contract"]

TITLES = {
    "Engineering": ["Software Engineer (SDE I)", "Software Engineer (SDE II)", "Senior Software Engineer",
                    "Staff Engineer", "Engineering Manager", "QA Engineer", "DevOps Engineer"],
    "Product": ["Associate Product Manager", "Product Manager", "Senior Product Manager", "Head of Product"],
    "Design": ["Product Designer", "Senior Product Designer", "UX Researcher", "Design Lead"],
    "Data & AI": ["Data Analyst", "Data Scientist", "ML Engineer", "AI Research Engineer"],
    "Marketing": ["Marketing Associate", "Content Writer", "Growth Marketer", "Head of Marketing"],
    "Sales": ["Sales Associate", "Account Executive", "Sales Manager"],
    "Customer Success": ["Support Specialist", "Customer Success Manager"],
    "People & HR": ["HR Associate", "HR Business Partner", "Talent Acquisition", "Head of People"],
    "Finance": ["Accountant", "Finance Associate", "Finance Manager"],
    "Operations": ["Operations Associate", "Operations Manager"],
    "Legal": ["Legal Counsel"],
    "Leadership": ["Vice President", "Director"],
}

GENDERS = ["Woman", "Man", "Non-binary", "Prefer not to say"]
RELATIONSHIPS = ["Parent", "Spouse or partner", "Sibling", "Friend", "Other"]
QUALIFICATIONS = ["High school", "Diploma", "Bachelor's degree", "Master's degree", "Doctorate", "Other"]


def as_dict(joinable: list[dict], domain: str) -> dict:
    return {"domain": domain, "levels": joinable, "departments": DEPARTMENTS, "employment_types": EMPLOYMENT_TYPES,
            "titles": TITLES, "genders": GENDERS, "relationships": RELATIONSHIPS, "qualifications": QUALIFICATIONS}
