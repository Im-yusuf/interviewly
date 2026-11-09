import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./taskly.db")
API_KEYS = {k.strip() for k in os.environ.get("API_KEYS", "").split(",") if k.strip()}
REMINDER_FROM = os.environ.get("REMINDER_FROM", "reminders@taskly.local")
