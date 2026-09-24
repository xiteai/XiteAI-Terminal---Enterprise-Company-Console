"""The raw material for demo data. Names are invented; emails use example.com
(reserved for exactly this) or the company domain for demo team members."""
from __future__ import annotations

FIRST = ["Aarav", "Vivaan", "Aditya", "Arjun", "Reyansh", "Ishaan", "Kabir", "Rohan", "Aryan", "Dhruv", "Ananya",
         "Diya", "Saanvi", "Aadhya", "Isha", "Kavya", "Meera", "Riya", "Priya", "Neha", "Tanvi", "Nisha", "Pooja",
         "Sneha", "Rahul", "Vikram", "Karan", "Siddharth", "Nikhil", "Manav", "Zoya", "Sara", "Aisha", "Fatima",
         "Imran", "Arnav", "Yash", "Varun", "Harsh", "Ira", "Mira", "Anika", "Tara", "Kiaan", "Advik", "Myra",
         "Navya", "Parth"]
FIRST_ABROAD = ["Noah", "Liam", "Emma", "Olivia", "Lucas", "Mia", "Ethan", "Sofia", "Daniel", "Hana", "Omar",
                "Layla", "Wei", "Yuki", "Lena", "Jonas", "Amelia", "Leo"]
LAST = ["Sharma", "Verma", "Gupta", "Singh", "Patel", "Reddy", "Iyer", "Nair", "Menon", "Das", "Bose", "Chatterjee",
        "Mehta", "Shah", "Joshi", "Kulkarni", "Rao", "Pillai", "Khan", "Siddiqui", "Kapoor", "Malhotra", "Agarwal",
        "Bansal", "Chopra", "Saxena", "Mishra", "Pandey", "Tiwari", "Yadav", "Fernandes", "D'Souza"]
LAST_ABROAD = ["Smith", "Brown", "Wilson", "Müller", "Tan", "Lim", "Wong", "Haddad", "Rossi", "Novak", "Sato", "Ahmed"]

REGIONS_IN = ["Maharashtra", "Delhi", "Karnataka", "Uttar Pradesh", "Tamil Nadu", "Telangana", "West Bengal",
              "Gujarat", "Rajasthan", "Kerala", "Punjab", "Haryana"]
ABROAD = [("United Arab Emirates", "Asia/Dubai", "en-AE", 4.0), ("United Kingdom", "Europe/London", "en-GB", 1.0),
          ("United States", "America/New_York", "en-US", -4.0), ("Singapore", "Asia/Singapore", "en-SG", 8.0),
          ("Canada", "America/Toronto", "en-CA", -4.0), ("Germany", "Europe/Berlin", "de-DE", 2.0)]

TOOLS = ["get_weather", "set_alarm", "edit_note", "play_song", "media_pause", "get_news", "show_market_data",
         "start_timer", "web_search", "get_today_schedule", "add_event", "open_game", "add_task", "get_watchlist",
         "web_research", "asset_write", "get_joke", "volume_up"]
TOOL_WEIGHTS = [14, 11, 10, 12, 8, 7, 9, 6, 9, 6, 5, 4, 5, 4, 3, 3, 2, 5]

# The demo's own rollout: (version, released N days before today).
RELEASES = [("1.0.12", 70), ("1.0.13", 34), ("1.0.14", 10), ("1.0.15", 8), ("1.0.16", 6), ("1.0.17", 2)]
HOUR_WEIGHTS = [2, 1, 1, .5, .5, 1, 2, 4, 6, 8, 8, 7, 6, 6, 6, 6, 7, 8, 10, 12, 13, 12, 9, 5]
PROFILES = {  # daily chance of use, check-ins per active day, share of installs
    "power": (0.90, (2, 4), 0.24),
    "regular": (0.62, (1, 3), 0.40),
    "casual": (0.30, (1, 2), 0.26),
    "churned": (0.70, (1, 2), 0.10),
}
AGE_BANDS = [((16, 17), 4), ((18, 24), 38), ((25, 34), 34), ((35, 44), 15), ((45, 54), 6), ((55, 62), 3)]

TICKETS = [  # kind, status, priority, subject, message, days ago
    ("support", "open", "high", "Voice cuts off mid-sentence",
     "Since this morning her replies stop halfway through longer sentences. Short answers are fine. Windows 11, XOS1 1.0.16.", 1),
    ("support", "in_progress", "normal", "Second laptop won't join my devices",
     "I typed the nine-digit code on my other laptop but it keeps saying the code expired, even straight after I read it out.", 3),
    ("support", "resolved", "normal", "Update stuck on 'installs next restart'",
     "Restarted three times and it still says the update will install next restart.", 9),
    ("feedback", "open", "low", "Please add a Hindi voice",
     "My parents would use it every day if she could speak Hindi. The English voice is lovely though.", 4),
    ("feedback", "closed", "low", "The new memory is brilliant",
     "She corrected my sister's name on her own after I mentioned it once. That felt like magic.", 12),
    ("data_access", "open", "normal", "What do you store about me?",
     "Before I turn on sharing, can you tell me exactly what leaves my PC?", 2),
    ("data_delete", "open", "high", "Delete my name and age",
     "I turned sharing off in Settings. Please also remove what you already have.", 1),
    ("support", "open", "urgent", "Alarm didn't ring this morning",
     "Set a 6:30 alarm by voice last night, she confirmed it, but nothing rang. Laptop was on charge with the lid open.", 0),
    ("support", "resolved", "normal", "Markets page shows yesterday's prices",
     "The Nifty number on the Markets page matched yesterday's close until I reopened the app.", 14),
    ("support", "in_progress", "normal", "Chess board doesn't load after the update",
     "Tapping chess opens a blank card. Blind Roulette opens fine.", 5),
    ("feedback", "open", "low", "Dark mode for the notes page",
     "Settings has dark mode but the notes page is still bright at night.", 6),
    ("support", "open", "normal", "Microphone not detected",
     "She says she can't hear me, but the mic works in other apps. USB headset.", 2),
    ("data_delete", "resolved", "normal", "Remove my data please",
     "Uninstalled on this PC. Please delete everything linked to it.", 16),
    ("support", "closed", "low", "How do I change her name?",
     "I want to rename my assistant. Is there a setting?", 18),
    ("feedback", "open", "low", "Blind Roulette is addictive",
     "Played it for an hour. Please add a scoreboard across days.", 3),
    ("support", "open", "normal", "High RAM right after start-up",
     "Task Manager shows about 2 GB for the first minute, then it settles. 8 GB laptop.", 7),
]

# The demo team. reports_to names someone earlier in the list; None = the founder.
# status: active | pending | deactivated. days = joined (or asked) this many days ago.
TEAM = [
    ("Ananya Iyer", "vp", "Engineering", "VP of Engineering", None, "active", 120),
    ("Kabir Malhotra", "vp", "Product", "VP of Product", None, "active", 110),
    ("Meera Nair", "director", "Design", "Director of Design", "Kabir Malhotra", "active", 95),
    ("Tanvi Joshi", "hr", "People & HR", "Head of People", None, "active", 90),
    ("Rohan Gupta", "manager", "Engineering", "Engineering Manager", "Ananya Iyer", "active", 80),
    ("Isha Menon", "manager", "Customer Success", "Customer Success Manager", "Kabir Malhotra", "active", 70),
    ("Arjun Rao", "employee", "Engineering", "Software Engineer (SDE II)", "Rohan Gupta", "active", 60),
    ("Diya Kapoor", "employee", "Engineering", "Software Engineer (SDE I)", "Rohan Gupta", "active", 41),
    ("Siddharth Das", "employee", "Data & AI", "ML Engineer", "Ananya Iyer", "active", 38),
    ("Neha Bansal", "employee", "Design", "Product Designer", "Meera Nair", "active", 30),
    ("Karan Shah", "employee", "Customer Success", "Support Specialist", "Isha Menon", "active", 22),
    ("Aadhya Pillai", "intern", "Engineering", "Software Engineer Intern", "Rohan Gupta", "active", 12),
    ("Manav Saxena", "employee", "Marketing", "Content Writer", "Kabir Malhotra", "deactivated", 64),
    ("Vivaan Chopra", "employee", "Engineering", "Software Engineer (SDE I)", None, "pending", 1),
    ("Zoya Siddiqui", "intern", "Design", "Product Designer", None, "pending", 2),
    ("Harsh Agarwal", "manager", "Sales", "Sales Manager", None, "pending", 0),
]
CITIES = ["Noida", "Bengaluru", "Mumbai", "Pune", "Hyderabad", "Gurugram", "Chennai", "Kolkata"]
COLLEGES = ["Amity University", "IIT Delhi", "BITS Pilani", "NIT Trichy", "Delhi University", "VIT Vellore",
            "IIIT Hyderabad", "Manipal Institute of Technology"]
SKILLS = {
    "Engineering": ["Python", "TypeScript", "React", "FastAPI", "PostgreSQL", "Docker", "System design"],
    "Product": ["Roadmapping", "User research", "Analytics", "Writing specs"],
    "Design": ["Figma", "Interaction design", "Prototyping", "Design systems"],
    "Data & AI": ["PyTorch", "LLMs", "Evaluation", "SQL", "Retrieval"],
    "People & HR": ["Hiring", "Onboarding", "Policy", "Culture"],
    "Customer Success": ["Support", "Onboarding", "Zendesk", "Writing"],
    "Marketing": ["Content", "SEO", "Social"],
    "Sales": ["B2B sales", "Negotiation", "CRM"],
}

# ── A second, demo-only product, so the switcher has somewhere to go ──────────
CHAT = {"slug": "xiteai-chat", "name": "XiteAI Chat", "full_name": "XiteAI Chat (demo)", "kind": "web",
        "description": "Chat in the browser, signed in with an XiteAI account.", "website": "https://chat.xiteai.com",
        "logo": "xiteai.png", "latest_version": "2.4.0", "status": "live"}
CHAT_RELEASES = [("2.1.0", 60), ("2.2.0", 31), ("2.3.0", 12), ("2.4.0", 3)]
CHAT_FEATURES = ["new_chat", "web_search", "file_upload", "image_read", "voice_input", "share_link", "code_block",
                 "rename_chat"]
CHAT_FEATURE_WEIGHTS = [20, 9, 6, 5, 4, 3, 7, 2]
CHAT_TICKETS = [
    ("support", "open", "high", "Signed out every few minutes",
     "Since yesterday the site signs me out while I'm typing. Chrome on Windows.", 1),
    ("support", "in_progress", "normal", "Uploaded PDF shows as empty",
     "A 12-page PDF uploads fine but the answer says it has no text.", 4),
    ("feedback", "open", "low", "Folders for chats",
     "I have about 200 chats now. Folders or tags would help a lot.", 6),
    ("data_delete", "open", "normal", "Delete my account",
     "Please delete my account and all chats linked to it.", 2),
    ("support", "resolved", "normal", "Share link opens a blank page",
     "The link I shared with a friend opened a blank page on their phone.", 10),
]

# Who works on what. The first name in each list leads it; the founder owns both.
PRODUCT_TEAMS = {
    "xos1": ["Ananya Iyer", "Rohan Gupta", "Arjun Rao", "Diya Kapoor", "Siddharth Das", "Aadhya Pillai", "Tanvi Joshi"],
    "xiteai-chat": ["Kabir Malhotra", "Meera Nair", "Isha Menon", "Neha Bansal", "Karan Shah"],
}
