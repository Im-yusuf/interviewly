"""No real person's details in the repo: examples, tests and fixtures use only the fictional samples.

Scans every file git would commit (tracked, plus untracked files that aren't ignored) for email
addresses outside reserved or project domains, home-folder paths other than the sample user's,
and phone numbers written with a leading +. A deliberate exception goes in ALLOWED.
"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EMAIL_DOMAINS = ("example.com", "example.org", "example.invalid")
# Allowed elsewhere: Claude's co-author address, and GitHub noreply addresses for Copilot or a fictional `-example`
# handle (sam-rivera-example). Any other noreply address names a real GitHub account. (A bot's `name[bot]@` never
# matches EMAIL.)
ALLOWED_EMAIL = re.compile(r"noreply@anthropic\.com|(?:\d+\+)?(?:[A-Za-z0-9-]+-example|Copilot)@users\.noreply\.github\.com",
                           re.I)
RESERVED_TLDS = ("example", "invalid", "test", "localhost", "local")   # RFC 2606 and mDNS: never a real mailbox
HOME_USERS = ("sam",)                                                  # /Users/sam, /home/sam, C:\Users\sam
EMAIL = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})")
HOME_PATH = re.compile(r"(?:/Users/|/home/|[A-Za-z]:\\{1,2}Users\\{1,2})([A-Za-z0-9._-]+)")
PHONE = re.compile(r"(?<![\w+])\+\d[\d ().-]{6,18}\d")
FICTIONAL_PHONE = re.compile(r"\+44[ .-]?(?:7700[ .-]?900|20[ .-]?7946[ .-]?0)\d{3}")   # Ofcom's drama ranges
# Deliberate exceptions, matched exactly. Keep this list short.
ALLOWED = {
    "+33 6 12 34 56 78",   # tests/test_ats_check.py: placeholder number for a fictional French CV
    "+90 555 000 0000",    # tests/test_cv_to_text.py: placeholder number for a fictional Turkish CV
    "bot@users.noreply.github.com",   # tests/test_provenance.py: placeholder address for a bot author
}


def email_ok(local, domain):
    domain = domain.lower()
    return (local == "git"                                             # git@github.com:owner/repo
            or any(domain == d or domain.endswith("." + d) for d in EMAIL_DOMAINS)
            or domain.rsplit(".", 1)[-1] in RESERVED_TLDS
            or bool(ALLOWED_EMAIL.fullmatch(f"{local}@{domain}")))


def problems(text):
    found = []
    for m in EMAIL.finditer(text):
        if not email_ok(m.group(1), m.group(2)) and m.group(0) not in ALLOWED:
            found.append(m.group(0))
    for m in HOME_PATH.finditer(text):
        if m.group(1).lower() not in HOME_USERS and m.group(0) not in ALLOWED:
            found.append(m.group(0))
    for m in PHONE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 8 <= len(digits) <= 15 and not FICTIONAL_PHONE.fullmatch(m.group(0)) and m.group(0) not in ALLOWED:
            found.append(m.group(0))
    return found


def committable_files():
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                         capture_output=True, check=True).stdout.decode("utf-8", "replace")
    return sorted({name for name in out.split("\0") if name})


@unittest.skipUnless(shutil.which("git") and (ROOT / ".git").exists(), "not a git checkout")
class NoPersonalDataTest(unittest.TestCase):
    def test_files_hold_only_fictional_contact_details(self):
        found = {}
        for name in committable_files():
            if name == "tests/test_no_personal_data.py":   # its own examples below
                continue
            path = ROOT / name
            try:
                data = path.read_bytes()
            except OSError:          # deleted in the working tree, or a folder
                continue
            if b"\0" in data[:8192]:  # binary
                continue
            hits = problems(data.decode("utf-8", "replace"))
            if hits:
                found[name] = sorted(set(hits))
        self.assertEqual(found, {}, "Use the fictional samples (sam@example.com, /Users/sam, +44 7700 900123), "
                                    "or add a deliberate exception to ALLOWED in tests/test_no_personal_data.py")

    def test_the_checks_catch_real_looking_details(self):
        self.assertEqual(problems("jo@example.net /Users/jo /home/jo C:\\Users\\jo +1 202 555 0143"),
                         ["jo@example.net", "/Users/jo", "/home/jo", "C:\\Users\\jo", "+1 202 555 0143"])
        self.assertEqual(problems("12345+jo@users.noreply.github.com jo@users.noreply.github.com jo@anthropic.com"),
                         ["12345+jo@users.noreply.github.com", "jo@users.noreply.github.com", "jo@anthropic.com"])
        for fine in ("sam@example.com", "1+Copilot@users.noreply.github.com", "noreply@anthropic.com",
                     "12345+sam-rivera-example@users.noreply.github.com", "dependabot[bot]@users.noreply.github.com",
                     "reminders@taskly.local", "git@github.com:example/taskly", "/Users/sam/code", "/home/sam",
                     "+44 7700 900123", "2026-11-10 10:00", "C++17", "+2 points", "@media (max-width: 600px)"):
            self.assertEqual(problems(fine), [], fine)


if __name__ == "__main__":
    unittest.main()
