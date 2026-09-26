"""Every permission a level can hold, grouped the way the Access grid shows
them, and what each level starts with before the founder changes anything."""
from __future__ import annotations

CATALOG = [
    ("Console", [
        ("overview", "Overview dashboard", "Headline numbers, activity and releases."),
        ("overview.demographics", "Age and region breakdowns", "Aggregated charts only, never individuals."),
        ("installs", "Installs list", "Every XOS1 install, its version and health."),
        ("releases", "Releases", "Versions, adoption and update failures."),
        ("support", "Support tickets", "Read what customers sent in."),
        ("support.reply", "Work on tickets", "Change status and priority, add internal notes."),
        ("support.assign", "Assign tickets", "Hand a ticket to a team member."),
        ("audit.view", "Audit log", "What happened, for their level and below."),
    ]),
    ("Customer data", [
        ("cust.name", "Full names", "The name an XOS1 user shared at setup."),
        ("cust.name_partial", "First name and initial", "Enough to recognise, not to identify."),
        ("cust.age", "Exact age", "Worked out from the date of birth."),
        ("cust.dob", "Date of birth", "The full date."),
        ("cust.age_band", "Age band", "18-24, 25-34 and so on."),
        ("cust.region", "Region and time zone", "Where the install is."),
        ("cust.fingerprints", "Hardware and key fingerprints", "The machine's identity."),
        ("installs.erase", "Erase an install's data", "Honour a deletion request."),
    ]),
    ("People", [
        ("people.directory", "Team directory", "Names, titles, departments and the org chart."),
        ("people.profiles", "Full employee profiles", "Everything filled in when they joined."),
        ("people.approve", "Approve join requests", "For levels below their own."),
        ("people.manage", "Change level, title, department", "For levels below their own."),
        ("people.fire", "Deactivate people", "Remove access for levels below their own."),
        ("people.reset", "Reset passwords", "For levels below their own."),
    ]),
    ("AI keys", [
        ("keys.view", "See AI key status", "Which provider keys are set, and who last changed each. Never a key."),
        ("keys.replace", "Replace AI keys", "Swap a provider's key. It's tested first, needs their password, and is logged."),
        ("keys.reveal", "Read an AI key in full", "Show the whole key on screen. Needs their password again, and every read is logged."),
    ]),
    ("Home feed", [
        ("feed.post", "Post to the feed", "Share an announcement, achievement or event with the whole company."),
    ]),
    ("Finance", [
        ("finance.view", "See product finance", "Revenue, costs and the P&L, for the products they're on."),
        ("finance.manage", "Log finance entries", "Add and remove revenue and cost entries."),
    ]),
    ("Careers", [
        ("careers.manage", "Post and close roles", "Open a role to the public, close it, and see who applied."),
    ]),
    ("Workplace", [
        ("workplace", "The Workplace area", "File leave, expenses, asset requests and helpdesk tickets of their own."),
        ("leave.approve", "Decide leave", "Approve or decline leave for levels below their own."),
        ("expenses.approve", "Decide expense claims", "Approve or decline claims for levels below their own."),
        ("assets.approve", "Decide asset requests", "Approve or decline hardware requests for levels below their own."),
        ("helpdesk.work", "Work the helpdesk queue", "See every ticket, reply, assign and close."),
        ("pay.all", "See everyone's payslips", "Payroll for the whole company, not only their own."),
    ]),
    ("Codebase", [
        ("code.map", "See the folder map", "Every folder and file name. Code opens only where they have access."),
        ("code.request", "Send change requests", "Edit what they were given, and send it for review."),
        ("code.read_all", "Read all code", "Every file, without being given it."),
        ("code.grant", "Give access in their areas", "In what they own; a reviewer only to their own team."),
        ("code.grant_all", "Give access anywhere", "Any folder, file, function, lines or feature."),
        ("code.owners", "Choose owners and reviewers", "Who answers for each folder, file or feature."),
        ("code.merge_all", "Approve and merge anything", "Not only in their own areas."),
        ("code.access_view", "See who can access what", "Grants and owners, without the code."),
        ("code.revoke", "Take access away", "From anyone below them, anywhere. For people leaving."),
    ]),
]
KEYS = [key for _, perms in CATALOG for key, _, _ in perms]

# Held by the founder alone and not shown in the grid: the grid itself, the
# whole audit trail, demo data, previewing other levels, and connecting code.
FOUNDER_ONLY = {"access.manage", "audit.all", "demo.manage", "preview", "products.manage", "code.connect"}

_CONSOLE = {"overview", "overview.demographics", "installs", "releases", "support", "support.reply",
            "support.assign", "audit.view"}
_PEOPLE = {"people.directory", "people.profiles", "people.approve", "people.manage", "people.fire", "people.reset"}
_CODE_ALL = {"code.map", "code.request", "code.read_all", "code.grant", "code.grant_all", "code.owners",
             "code.merge_all", "code.access_view", "code.revoke"}
# Everyone files their own leave, expenses and tickets; deciding them is a power.
_DECIDE_ALL = {"leave.approve", "expenses.approve", "assets.approve"}

DEFAULTS: dict[str, set[str]] = {
    "vp": _CONSOLE | _PEOPLE | _CODE_ALL | _DECIDE_ALL | {"cust.name", "cust.age", "cust.age_band", "cust.region",
                                                          "installs.erase", "keys.view", "workplace",
                                                          "helpdesk.work", "pay.all", "feed.post",
                                                          "finance.view", "finance.manage", "careers.manage",
                                                          "keys.replace", "keys.reveal"},
    "director": _CONSOLE | _DECIDE_ALL | {"cust.name_partial", "cust.age_band", "cust.region", "people.directory",
                                          "people.profiles", "people.approve", "people.manage", "people.fire",
                                          "code.map", "code.request", "code.grant", "code.access_view",
                                          "workplace", "helpdesk.work", "feed.post", "finance.view",
                                          "careers.manage"},
    "hr": {"overview", "support", "support.reply", "code.access_view", "code.revoke",
           "workplace", "pay.all", "feed.post", "careers.manage",
           "keys.view", "keys.reveal"} | _PEOPLE | _DECIDE_ALL,
    "manager": {"overview", "overview.demographics", "installs", "releases", "support", "support.reply",
                "support.assign", "cust.name_partial", "cust.age_band", "people.directory", "people.approve",
                "code.map", "code.request", "code.grant", "workplace", "leave.approve", "expenses.approve",
                "helpdesk.work"},
    "employee": {"overview", "installs", "releases", "support", "support.reply", "people.directory",
                 "code.map", "code.request", "workplace"},
    "intern": {"overview", "releases", "support", "people.directory", "code.map", "code.request", "workplace"},
}


def as_groups() -> list[dict]:
    return [{"name": name, "perms": [{"key": k, "label": label, "hint": hint} for k, label, hint in perms]}
            for name, perms in CATALOG]
