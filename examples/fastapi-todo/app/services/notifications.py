import logging
import time
from datetime import datetime

from ..config import REMINDER_FROM

log = logging.getLogger("taskly.notifications")


def send_reminder(email: str, title: str, due_at: datetime) -> None:
    """Pretend to send an email reminder. A real SMTP call would go here."""
    time.sleep(2)  # simulates a slow SMTP server
    log.info("reminder from %s to %s: %r due %s", REMINDER_FROM, email, title, due_at.isoformat())
