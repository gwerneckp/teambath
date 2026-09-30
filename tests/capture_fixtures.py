"""Refresh tests/fixtures/ from the real site, with personal details scrubbed.

    TEAMBATH_EMAIL=... TEAMBATH_PIN=... uv run python tests/capture_fixtures.py

Run it when the site changes, then update the expectations in the tests.

Everything that identifies the member (name, email, member id, birth date, phone, address)
is replaced by fake values, and so are other people's details (email addresses, coaches'
names and bios). Hidden form state (__VIEWSTATE, which can encode personal details too) is
blanked, and inline scripts are dropped to keep the files small.
It makes one deliberately failed login, with PIN 0000, to capture the error page.

It never books. The booking pages (confirm_*, booked, bookings, cancel_confirm,
bookings_empty) were captured once, on 30 Sep 2026, by booking a free squash court and
cancelling it straight away, and scrubbed with Capture.save.
"""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from teambath import TeamBath

OUT = Path(__file__).parent / "fixtures"
FAKE = {"member_id": "1000001", "first_name": "Alex", "last_name": "Example",
        "email": "ab123@bath.ac.uk", "mobile": "7700900000", "birth_date": "01/01/2000",
        "address": ["Flat 1", "1 Test Street", "Testville", "Bath", "BA1 1AA"]}


class Capture:
    def __init__(self, email: str, pin: str):
        self.tb = TeamBath(email, pin)
        account = self.tb.account()
        pairs = [
            (f"{account.first_name} {account.last_name}", f"{FAKE['first_name']} "
                                                          f"{FAKE['last_name']}"),
            (account.email, FAKE["email"]), (email, FAKE["email"]),
            (account.member_id, FAKE["member_id"]), (account.first_name, FAKE["first_name"]),
            (account.last_name, FAKE["last_name"]), (account.mobile, FAKE["mobile"]),
        ]
        if account.birth_date:
            pairs.append((f"{account.birth_date:%d/%m/%Y}", FAKE["birth_date"]))
        # Longest first, so the full name goes before its parts.
        self.pairs = sorted(((a, b) for a, b in pairs if a), key=lambda p: -len(p[0]))
        # Address lines can be common words ("Bath"), so only replace them as field values.
        fake_lines = FAKE["address"] + [""] * len(account.address)
        self.fields = list(zip(account.address, fake_lines, strict=False))

    def scrub(self, html: str) -> str:
        html = re.sub(r'(id="__(?:VIEWSTATE|EVENTVALIDATION)" value=")[^"]*', r"\1", html)
        html = re.sub(r"<script(?![^>]*\bsrc=)[^>]*>.*?</script>", "", html, flags=re.S)
        for real, fake in self.pairs:
            html = re.sub(re.escape(real), fake, html, flags=re.I)
        for real, fake in self.fields:
            html = html.replace(f'value="{real}"', f'value="{fake}"')
        html = self.scrub_coaches(html)
        # Other people's emails (e.g. coaches' contact details in activity descriptions).
        return re.sub(r"[\w.+-]+@(?!example\.)[\w-]+(\.[\w-]+)+",
                      lambda m: m[0] if m[0] == FAKE["email"] else "someone@example.com", html)

    @staticmethod
    def scrub_coaches(html: str) -> str:
        """Coaching activities are named after the coach ("X Jane Doe 1hr") and described
        with their bio: rename them "X Coach N 1hr" and drop the bios."""
        soup = BeautifulSoup(html, "html.parser")
        renames = {}
        for link in soup.select("a[id*=lnkActivitySelect]"):
            name = link.get_text(strip=True)
            if not re.fullmatch(r"X (?!X ).+ 1hr", name):
                continue
            renames.setdefault(name, f"X Coach {len(renames) + 1} 1hr")
            row = link.find_parent("div", class_="div-row")
            for bio in row.select(".flexible-comment-text, .togglecomments"):
                bio.string = "Coach bio removed." if bio.get_text(strip=True) else ""
        if not renames:
            return html
        html = str(soup)
        for real, fake in renames.items():
            html = html.replace(real, fake)
        return html

    def save(self, name: str, response: requests.Response) -> None:
        html = self.scrub(response.text)
        for real, _ in self.pairs:
            assert real.lower() not in html.lower(), f"{real!r} survived scrubbing in {name}"
        for real, fake in self.fields:
            assert real == fake or f'value="{real}"' not in html, f"{real!r} survived in {name}"
        (OUT / f"{name}.html").write_text(html)
        print(f"  {name}.html  {len(html) // 1024} KB  ({response.url})")

    def run(self) -> None:
        OUT.mkdir(exist_ok=True)
        tb, tomorrow = self.tb, date.today() + timedelta(days=1)
        self.save("login", requests.get(tb.url + "MRMLogin.aspx"))
        failed = TeamBath(tb.email, "0000")
        form = failed.fetch("MRMLogin.aspx", login=False)
        self.save("login_failed", failed.request("POST", form.action(), data=form.submission(
            "ctl00$MainContent$btnLogin", {"ctl00$MainContent$InputLogin": tb.email,
                                           "ctl00$MainContent$InputPassword": "0000"})))

        self.save("home", tb.fetch(tb.HOME).response)
        self.save("account", tb.fetch("MemberManagement/EditMemberDetails.aspx").response)
        self.save("search_squash", tb.search_page(tomorrow, "SQUASH").response)
        self.save("search_empty", tb.search_page(date.today() + timedelta(days=60),
                                                 "SWIMMING").response)
        squash = next(a for a in tb.search(tomorrow, "SQUASH") if a.name == "Squash Students")
        self.save("activity_grid", tb.availability_page(squash, tomorrow)[1].response)
        classes = [a for a in tb.search(tomorrow, "SWIMMING") if a.kind == "class"]
        with_space = next(a for a in classes if a.status == "Space")
        self.save("class", tb.availability_page(with_space, tomorrow)[1].response)
        full = next((a for a in tb.search() if a.kind == "class" and a.status == "Full"), None)
        if full:
            self.save("class_full", tb.availability_page(full)[1].response)
        else:
            print("  (no full class today: class_full.html left as it was)")


if __name__ == "__main__":
    Capture(os.environ["TEAMBATH_EMAIL"], os.environ["TEAMBATH_PIN"]).run()
