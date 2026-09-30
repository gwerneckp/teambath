"""Parsers against real (scrubbed) pages from the site."""

from datetime import date, datetime

from bs4 import BeautifulSoup

from teambath import Account, ActivityType, Booking
from teambath.parse import Parse


def test_qa_pairs_with_spaces_and_empty_values():
    el = BeautifulSoup('<td data-qa-id="button-ActivityID=SQUASHFREE2 ResourceID=0 '
                       'Date=2026/10/1 Time= Availability= Not Available Court=Squash Court 1">'
                       "</td>", "html.parser").td
    assert Parse.qa(el) == {"ActivityID": "SQUASHFREE2", "ResourceID": "0", "Date": "2026/10/1",
                            "Time": "", "Availability": "Not Available",
                            "Court": "Squash Court 1"}


def test_qa_value_with_ampersand_and_time():
    el = BeautifulSoup('<input data-qa-id="button-ActivityID=X ResourceID=1 Duration=60 '
                       'Status=No Space &amp; No Waiting List Date=30/09/2026 18:00:00">',
                       "html.parser").input
    qa = Parse.qa(el)
    assert qa["Status"] == "No Space & No Waiting List"
    assert qa["Date"] == "30/09/2026 18:00:00"


def test_login_error(pages):
    assert Parse.login_error(pages.soup("login_failed")) == \
        "Invalid Email Address or PIN. Please try again"
    assert Parse.login_error(pages.soup("login")) is None


def test_activity_types(pages):
    types = Parse.activity_types(pages.soup("home"))
    assert len(types) == 19  # "Any" is not a type
    assert types[0] == ActivityType("BADMINTON", "Badminton")
    assert ActivityType("SQUASH", "Squash") in types
    assert ActivityType("SWIMMING", "Swimming 50m Pool") in types


def test_search_results_classes_then_activities(pages):
    results = Parse.search_results(pages.soup("home"))
    assert len(results) == 60
    kinds = [a.kind for a in results]
    assert kinds == ["class"] * 6 + ["activity"] * 54
    swim = results[0]
    assert (swim.id, swim.name, swim.type, swim.status) == (
        "SFIT50MR109544", "Swimfit/weds/18.00/fast", "Swimming 50m Pool", "Space")
    assert swim.description.startswith("Student, staff and public 1hr Swimfit")
    assert results[1].status == "Full"


def test_search_results_activity(pages):
    squash = Parse.search_results(pages.soup("search_squash"))
    assert [(a.id, a.name) for a in squash] == [
        ("SQUASHPAY1", "Squash P.A.Y.G"), ("SQUASHSTAFF", "Squash Staff"),
        ("SQUASHFREE2", "Squash Students")]
    assert all(a.kind == "activity" and a.type == "Squash" and a.status is None for a in squash)
    assert "45min" in squash[2].description


def test_search_no_results(pages):
    assert Parse.search_results(pages.soup("search_empty")) == []


def test_class_with_space(pages):
    [slot] = Parse.class_slots(pages.soup("class"))
    assert slot.activity_id == "SFIT50MR18897"
    assert slot.start == datetime(2026, 10, 1, 18, 0)
    assert (slot.duration, slot.available, slot.spaces, slot.status) == (60, True, 5, "Available")
    assert slot.resource is None


def test_class_full(pages):
    [slot] = Parse.class_slots(pages.soup("class_full"))
    assert slot.start == datetime(2026, 9, 30, 18, 0)
    assert (slot.available, slot.spaces, slot.status) == (
        False, 0, "No Space & No Waiting List")


def test_activity_grid(pages):
    slots = Parse.activity_slots(pages.soup("activity_grid"))
    assert len(slots) == 80  # 20 times x 4 courts, taken ones included
    assert {s.resource for s in slots} == {f"Squash Court {n}" for n in range(1, 5)}
    assert {s.start.date() for s in slots} == {date(2026, 10, 1)}
    assert len({s.start for s in slots}) == 20
    assert sum(s.available for s in slots) == 51
    first, last = slots[0], slots[-1]
    assert (first.start, first.resource, first.available) == (
        datetime(2026, 10, 1, 7, 0), "Squash Court 1", True)
    assert (last.start, last.resource, last.available) == (
        datetime(2026, 10, 1, 21, 15), "Squash Court 4", False)
    at_1045 = [s for s in slots if s.start == datetime(2026, 10, 1, 10, 45)]
    assert [s.available for s in at_1045] == [False, True, True, True]
    assert {s.status for s in slots} == {"Available", "Not Available"}
    assert all(s.duration is None and s.spaces is None for s in slots)


def test_account(pages):
    assert Parse.account(pages.soup("account")) == Account(
        member_id="1000001", first_name="Alex", last_name="Example", email="ab123@bath.ac.uk",
        birth_date=date(2000, 1, 1), mobile="7700900000",
        address=["Flat 1", "1 Test Street", "Testville", "Bath", "BA1 1AA"])


def test_activity_grid_with_a_single_unnamed_resource():
    # e.g. basketball: each activity is one resource, so the site leaves Court= empty
    soup = BeautifulSoup('<table id="ctl00_MainContent_grdResourceView"><tr>'
                         '<td class="itemnotavailable" data-qa-id="button-ActivityID=B1 '
                         'ResourceID=0 Date=2026/10/1 Time= Availability= Not Available Court=">'
                         '<div>08:00</div></td></tr><tr><td class="itemavailable"><input '
                         'type="submit" value="09:00" data-qa-id="button-ActivityID=B1 '
                         'ResourceID=0 Date=2026/10/1 Time=09:00 Availability= Available Court=">'
                         "</td></tr></table>", "html.parser")
    a, b = Parse.activity_slots(soup)
    assert (a.start, a.resource, a.available) == (datetime(2026, 10, 1, 8, 0), None, False)
    assert (b.start, b.resource, b.available) == (datetime(2026, 10, 1, 9, 0), None, True)


def test_bookings(pages):
    [booking] = Parse.bookings(pages.soup("bookings"))
    assert booking == Booking(activity_id="SQUASHFREE2", name="Squash Students",
                              start=datetime(2026, 10, 5, 10, 45), duration=45, status="Confirmed")
    assert Parse.bookings(pages.soup("bookings_empty")) == []


def test_booking_confirmation_pages(pages):
    assert Parse.prices(pages.soup("confirm_free")) == ["£0.00"]
    assert Parse.confirmation(pages.soup("confirm_free")) == ("Squash Students", 45)
    assert Parse.prices(pages.soup("confirm_paid")) == ["£9.50"]
    assert Parse.prices(pages.soup("confirm_refused")) == []
    assert Parse.error(pages.soup("confirm_refused")) == \
        "Sorry, you are not permitted to book at the time selected."
    assert Parse.error(pages.soup("confirm_free")) is None


def test_cancel_confirmation_page(pages):
    assert Parse.prices(pages.soup("cancel_confirm")) == ["Total £0.00"]
    assert Parse.error(pages.soup("cancel_confirm")) is None


def test_is_free():
    assert Parse.is_free("£0.00") and Parse.is_free("Total £0.00")
    assert not Parse.is_free("£9.50") and not Parse.is_free("Total £0.50")
    assert not Parse.is_free("")  # no price shown: don't assume free


def test_cells_pair_slots_with_their_buttons(pages):
    for slot, el in Parse.activity_cells(pages.soup("activity_grid")):
        assert (el.name == "input") == slot.available  # only free cells can be clicked
    [(slot, button)] = Parse.class_cells(pages.soup("class"))
    assert button["name"] == "ctl00$MainContent$ClassStatus$ctrl0$btnBook"
