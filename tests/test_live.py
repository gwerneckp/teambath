"""Against the real site, read-only. Skipped unless TEAMBATH_EMAIL and TEAMBATH_PIN are set:

    TEAMBATH_EMAIL=... TEAMBATH_PIN=... uv run pytest -m live

These check the site still looks the way the parsers expect, whatever is on today.
They never book or cancel anything, and never try a wrong PIN (that could lock the account).
"""

import os
from datetime import date, timedelta

import pytest

from teambath import TeamBath

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not (os.environ.get("TEAMBATH_EMAIL") and os.environ.get("TEAMBATH_PIN")),
                       reason="set TEAMBATH_EMAIL and TEAMBATH_PIN to run live tests"),
]
TOMORROW = date.today() + timedelta(days=1)


@pytest.fixture(scope="module")
def tb():
    client = TeamBath(os.environ["TEAMBATH_EMAIL"], os.environ["TEAMBATH_PIN"])
    client.login()
    return client


def test_account(tb):
    account = tb.account()
    assert account.email.lower() == tb.email.lower()
    assert account.member_id.isdigit() and account.first_name


def test_bookings(tb):
    assert all(b.activity_id and b.start and b.status for b in tb.bookings())


def test_activity_types(tb):
    ids = {t.id for t in tb.activity_types()}
    assert {"SQUASH", "SWIMMING", "BADMINTON"} <= ids


def test_search(tb):
    results = tb.search(TOMORROW, type="SQUASH")
    assert results and all(a.kind == "activity" and a.type == "Squash" for a in results)


def test_court_grid(tb):
    squash = next(a for a in tb.search(TOMORROW, type="SQUASH") if "Student" in a.name)
    slots = tb.availability(squash, TOMORROW)
    assert slots and all(s.start.date() == TOMORROW and s.resource for s in slots)
    assert all(s.activity_id == squash.id for s in slots)


def test_class_sessions(tb):
    classes = [a for a in tb.search(TOMORROW) if a.kind == "class"]
    if not classes:
        pytest.skip("no classes listed for tomorrow")
    slots = tb.availability(classes[0], TOMORROW)
    assert slots and all(s.start.date() == TOMORROW and s.duration for s in slots)
    assert all((s.spaces or 0) >= 0 and s.status for s in slots)
