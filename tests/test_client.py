"""The client's flows against mocked HTTP, answered with the real (scrubbed) pages."""

from datetime import date, datetime
from urllib.parse import parse_qs

import pytest
import responses

from teambath import (
    Activity,
    ActivityType,
    Booking,
    LoginError,
    PaidBookingError,
    Slot,
    TeamBath,
    TeamBathError,
)

URL = "https://bookings.teambath.com/Connect/"
HOME, LOGIN = URL + "memberHomePage.aspx", URL + "MRMLogin.aspx"
SEARCH = "ctl00$MainContent$_advanceSearchUserControl$"
RESULTS = "ctl00$MainContent$_advanceSearchResultsUserControl$"


def sent(call) -> dict[str, str]:
    """The form fields of a recorded POST."""
    return {k: v[0] for k, v in parse_qs(call.request.body, keep_blank_values=True).items()}


def posts(rsps) -> list[dict[str, str]]:
    return [sent(c) for c in rsps.calls if c.request.method == "POST"]


@pytest.fixture
def rsps():
    with responses.RequestsMock() as r:
        yield r


@pytest.fixture
def tb():
    return TeamBath("ab123@bath.ac.uk", "1234")


def logged_in(rsps, pages):
    """The home page answers directly: the session is already good."""
    rsps.get(HOME, body=pages.html("home"))


def test_logs_in_on_first_use(rsps, pages, tb):
    rsps.get(HOME, status=302, headers={"Location": LOGIN})
    rsps.get(LOGIN, body=pages.html("login"))
    rsps.post(LOGIN, status=302, headers={"Location": HOME})
    rsps.get(HOME, body=pages.html("home"))

    assert len(tb.activity_types()) == 19
    [form] = posts(rsps)
    assert form["ctl00$MainContent$InputLogin"] == "ab123@bath.ac.uk"
    assert form["ctl00$MainContent$InputPassword"] == "1234"
    assert form["ctl00$MainContent$btnLogin"] == "Login"
    assert "__VIEWSTATE" in form


def test_pin_can_be_an_int():
    assert TeamBath("ab123@bath.ac.uk", 1234).pin == "1234"


def test_repr_hides_the_pin(tb):
    assert "1234" not in repr(tb)


def test_wrong_pin(rsps, pages, tb):
    rsps.get(LOGIN, body=pages.html("login"))
    rsps.post(LOGIN, body=pages.html("login_failed"))
    with pytest.raises(LoginError, match="Invalid Email Address or PIN"):
        tb.login()


def test_login_that_does_not_stick(rsps, pages, tb):
    rsps.get(HOME, status=302, headers={"Location": LOGIN})
    rsps.get(LOGIN, body=pages.html("login"))
    rsps.post(LOGIN, status=302, headers={"Location": HOME})
    rsps.get(HOME, body=pages.html("home"))  # login lands on the home page...
    rsps.get(HOME, status=302, headers={"Location": LOGIN})  # ...but the session is gone again
    with pytest.raises(LoginError, match="Still not logged in"):
        tb.activity_types()


def test_session_expiring_mid_request(rsps, pages, tb):
    logged_in(rsps, pages)
    rsps.post(HOME, status=302, headers={"Location": URL + "mainmessage.aspx"})
    rsps.get(URL + "mainmessage.aspx", status=302, headers={"Location": LOGIN})
    rsps.get(LOGIN, body=pages.html("login"))
    with pytest.raises(LoginError, match="expired"):
        tb.search(date(2026, 10, 1))


def test_site_error_page(rsps, pages, tb):
    logged_in(rsps, pages)
    rsps.post(HOME, status=302, headers={"Location": URL + "mainmessage.aspx"})
    rsps.get(URL + "mainmessage.aspx", body="<html><body>Something went wrong</body></html>")
    with pytest.raises(TeamBathError, match="Something went wrong"):
        tb.search(date(2026, 10, 1))


def test_http_errors_raise(rsps, tb):
    rsps.get(HOME, status=500)
    with pytest.raises(Exception, match="500"):
        tb.activity_types()


def test_search_sends_the_day_and_type(rsps, pages, tb):
    logged_in(rsps, pages)
    rsps.post(HOME, body=pages.html("search_squash"))

    results = tb.search(date(2026, 10, 1), type="squash")  # names match case-insensitively
    assert [a.id for a in results] == ["SQUASHPAY1", "SQUASHSTAFF", "SQUASHFREE2"]
    [form] = posts(rsps)
    assert form["__EVENTTARGET"] == SEARCH + "_searchBtn"
    assert form[SEARCH + "ActivityGroups"] == "SQUASH"
    assert form[SEARCH + "Activities"] == ""
    assert form[SEARCH + "startDate"] == form[SEARCH + "endDate"] == "2026-10-01"


@pytest.mark.parametrize("given", ["SWIMMING", "Swimming 50m Pool",
                                   ActivityType("SWIMMING", "Swimming 50m Pool")])
def test_type_by_id_name_or_object(rsps, pages, tb, given):
    logged_in(rsps, pages)
    rsps.post(HOME, body=pages.html("search_empty"))
    assert tb.search(date(2026, 11, 29), type=given) == []
    assert posts(rsps)[0][SEARCH + "ActivityGroups"] == "SWIMMING"


def test_search_defaults_to_any_type_today(rsps, pages, tb):
    logged_in(rsps, pages)
    rsps.post(HOME, body=pages.html("home"))
    assert len(tb.search()) == 60
    form = posts(rsps)[0]
    assert form[SEARCH + "ActivityGroups"] == ""
    assert form[SEARCH + "startDate"] == date.today().isoformat()


def test_unknown_type(rsps, pages, tb):
    logged_in(rsps, pages)
    with pytest.raises(TeamBathError, match="No activity type 'Quidditch'.*Squash"):
        tb.search(type="Quidditch")


def test_availability_of_a_class(rsps, pages, tb):
    logged_in(rsps, pages)
    rsps.post(HOME, body=pages.html("home"))  # search results
    rsps.post(HOME, body=pages.html("class"))

    [slot] = tb.availability("SFIT50MR109544", date(2026, 10, 1))
    assert (slot.spaces, slot.duration) == (5, 60)
    search, click = posts(rsps)
    assert search[SEARCH + "startDate"] == "2026-10-01"
    assert click["__EVENTTARGET"] == RESULTS + "Classes$ctrl0$btnAvailability_lg"


def test_availability_of_an_activity(rsps, pages, tb):
    logged_in(rsps, pages)
    rsps.post(HOME, body=pages.html("home"))
    rsps.post(HOME, body=pages.html("activity_grid"))

    squash = Activity("SQUASHFREE2", "Squash Students", "activity", "Squash", "", None)
    slots = tb.availability(squash, date(2026, 10, 1))
    assert len(slots) == 80
    click = posts(rsps)[1]
    assert click["__EVENTTARGET"].startswith(RESULTS + "Activities$ctrl")
    assert click["__EVENTTARGET"].endswith("$lnkActivitySelect_lg")


def test_availability_of_something_not_listed(rsps, pages, tb):
    logged_in(rsps, pages)
    rsps.post(HOME, body=pages.html("search_empty"))
    with pytest.raises(TeamBathError, match="NOPE isn't on the site's list for Thu 01 Oct 2026"):
        tb.availability("NOPE", date(2026, 10, 1))


def test_account(rsps, pages, tb):
    rsps.get(URL + "MemberManagement/EditMemberDetails.aspx", body=pages.html("account"))
    assert tb.account().member_id == "1000001"


def test_other_site_url():
    tb = TeamBath("a@b.c", "1", url="https://leisure.example.com/Connect")
    assert tb.url == "https://leisure.example.com/Connect/"


# ---------------------------------------------------------------- booking

GRID, CLASS = URL + "mrmProductStatus.aspx", URL + "mrmClassStatus.aspx"
CONFIRM, BOOKED = URL + "mrmConfirmBooking.aspx", URL + "mrmBookingConfirmed.aspx"
BOOKINGS, CANCEL = URL + "mrmViewMyBookings.aspx?showOption=1", URL + "mrmConfirmMove.aspx"
COURT = Slot("SQUASHFREE2", datetime(2026, 10, 1, 7, 0), None, "Squash Court 1", True, None,
             "Available")
SWIM = Slot("SFIT50MR109544", datetime(2026, 10, 1, 18, 0), 60, None, True, 5, "Available")
BOOKING = Booking("SQUASHFREE2", "Squash Students", datetime(2026, 10, 5, 10, 45), 45,
                  "Confirmed")


def open_grid(rsps, pages):
    """Home -> search -> the squash grid for 1 Oct."""
    logged_in(rsps, pages)
    rsps.post(HOME, body=pages.html("home"))
    rsps.post(HOME, body=pages.html("activity_grid"))


def test_book_a_free_court(rsps, pages, tb):
    open_grid(rsps, pages)
    rsps.post(GRID, body=pages.html("confirm_free"))
    rsps.post(CONFIRM, status=302, headers={"Location": BOOKED})
    rsps.get(BOOKED, body=pages.html("booked"))

    booking = tb.book(COURT)
    assert booking == Booking("SQUASHFREE2", "Squash Students", datetime(2026, 10, 1, 7, 0), 45,
                              "Confirmed")
    click, book = posts(rsps)[2:]
    assert click["ctl00$MainContent$grdResourceView$ctl02$ctl00"] == "07:00"  # Court 1, 07:00
    assert book["__EVENTTARGET"] == "ctl00$MainContent$btnBasket"


def test_book_refuses_a_paid_slot_and_backs_out(rsps, pages, tb):
    logged_in(rsps, pages)
    rsps.post(HOME, body=pages.html("home"))
    rsps.post(HOME, body=pages.html("class"))
    rsps.post(CLASS, body=pages.html("confirm_paid"))
    rsps.post(CONFIRM, body=pages.html("home"))  # the Cancel button

    with pytest.raises(PaidBookingError, match="costs £9.50"):
        tb.book(SWIM)
    click, back_out = posts(rsps)[2:]
    assert click["ctl00$MainContent$ClassStatus$ctrl0$btnBook"] == "Book"
    assert click["ctl00$MainContent$ClassStatus$ctrl0$hMemberIncluded"] == "true"
    assert back_out["ctl00$MainContent$btnCancel"] == "Cancel"
    assert "ctl00$MainContent$btnBasket" not in (back_out["__EVENTTARGET"], *back_out)


def test_book_passes_on_the_sites_refusal(rsps, pages, tb):
    open_grid(rsps, pages)
    rsps.post(GRID, body=pages.html("confirm_refused"))
    with pytest.raises(TeamBathError, match="not permitted to book"):
        tb.book(COURT)


def test_book_a_taken_slot(rsps, pages, tb):
    open_grid(rsps, pages)
    taken = Slot("SQUASHFREE2", datetime(2026, 10, 1, 10, 45), None, "Squash Court 1", True,
                 None, "Available")  # it was free when we looked, but not any more
    with pytest.raises(TeamBathError, match="isn't available .Not Available."):
        tb.book(taken)
    assert len(posts(rsps)) == 2  # searched and opened the grid, clicked nothing


def test_book_that_does_not_go_through(rsps, pages, tb):
    open_grid(rsps, pages)
    rsps.post(GRID, body=pages.html("confirm_free"))
    rsps.post(CONFIRM, body=pages.html("confirm_free"))  # back on the confirm page
    with pytest.raises(TeamBathError, match="did not go through"):
        tb.book(COURT)


def test_bookings(rsps, pages, tb):
    rsps.get(BOOKINGS, body=pages.html("bookings"))
    assert tb.bookings() == [BOOKING]


def test_cancel(rsps, pages, tb):
    rsps.get(BOOKINGS, body=pages.html("bookings"))
    rsps.post(BOOKINGS, body=pages.html("cancel_confirm"))
    rsps.post(CANCEL, status=302, headers={"Location": BOOKINGS})
    rsps.get(BOOKINGS, body=pages.html("bookings_empty"))

    tb.cancel(BOOKING)
    click, confirm = posts(rsps)
    assert click["__EVENTTARGET"] == "ctl00$MainContent$rptMain$ctl01$gvBookings$ctl02$ctl01"
    assert confirm["ctl00$MainContent$btnConfirm"] == "Confirm"


def test_cancel_something_not_booked(rsps, pages, tb):
    rsps.get(BOOKINGS, body=pages.html("bookings_empty"))
    with pytest.raises(TeamBathError, match="No booking of Squash Students at Mon 05 Oct 10:45"):
        tb.cancel(BOOKING)


def test_cancel_refuses_a_paid_booking(rsps, pages, tb):
    rsps.get(BOOKINGS, body=pages.html("bookings"))
    rsps.post(BOOKINGS, body=pages.html("cancel_confirm").replace("Total £0.00", "Total £9.50"))
    with pytest.raises(PaidBookingError, match="£9.50"):
        tb.cancel(BOOKING)
    assert len(posts(rsps)) == 1  # never confirmed


def test_cancel_that_does_not_stick(rsps, pages, tb):
    rsps.get(BOOKINGS, body=pages.html("bookings"))
    rsps.post(BOOKINGS, body=pages.html("cancel_confirm"))
    rsps.post(CANCEL, body=pages.html("bookings"))
    with pytest.raises(TeamBathError, match="still booked"):
        tb.cancel(BOOKING)
