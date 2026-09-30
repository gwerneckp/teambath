"""The client's flows against mocked HTTP, answered with the real (scrubbed) pages."""

from datetime import date
from urllib.parse import parse_qs

import pytest
import responses

from teambath import Activity, ActivityType, LoginError, TeamBath, TeamBathError

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
