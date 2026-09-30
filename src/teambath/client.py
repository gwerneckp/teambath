"""Team Bath booking site client (bookings.teambath.com, a Gladstone Connect site).

There's no API: we log in with the member's email and PIN like the login form does, then
drive the same pages a browser would. Each public method starts from a fresh page and
walks to what it needs, so calls never depend on each other.
"""

from __future__ import annotations

from datetime import date

import requests

from .models import Account, Activity, ActivityType, Booking, Slot
from .page import Page
from .parse import RESULTS, Parse

USER_AGENT = "Mozilla/5.0 (compatible; teambath)"
SEARCH_FORM = "ctl00$MainContent$_advanceSearchUserControl$"  # form field name prefix


class TeamBathError(Exception):
    """The site didn't do what we expected."""


class LoginError(TeamBathError):
    """Wrong email or PIN, or the site refused the login."""


class PaidBookingError(TeamBathError):
    """The booking costs money. Paid bookings aren't supported, so nothing was done."""


class TeamBath:
    """A logged-in Team Bath member.

    >>> tb = TeamBath("abc123@bath.ac.uk", "1234")
    >>> tb.search(date(2026, 10, 1), type="squash")

    Logs in on first use, and again by itself whenever the session has expired.
    url: the site's Connect root, for other Gladstone Connect sites (untested).
    """

    DEFAULT_URL = "https://bookings.teambath.com/Connect/"
    HOME = "memberHomePage.aspx"
    BOOKINGS = "mrmViewMyBookings.aspx?showOption=1"

    def __init__(self, email: str, pin: str, *, url: str | None = None, timeout: float = 30):
        self.email = email
        self.pin = str(pin)
        self.url = (url or self.DEFAULT_URL).rstrip("/") + "/"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

    def __repr__(self) -> str:
        return f"TeamBath({self.email!r})"

    # ------------------------------------------------------------------ auth

    def login(self) -> None:
        """Log in now (otherwise it happens on first use). Raises LoginError."""
        form = self.fetch("MRMLogin.aspx", login=False)
        data = form.submission("ctl00$MainContent$btnLogin", {
            "ctl00$MainContent$InputLogin": self.email,
            "ctl00$MainContent$InputPassword": self.pin,
            "ctl00$MainContent$JavascriptEnabled": "1",
        })
        page = Page(self, self.request("POST", form.action(), data=data))
        if page.is_login():
            raise LoginError(Parse.login_error(page.soup) or "Login failed.")

    # ------------------------------------------------------------- low level

    def fetch(self, path: str, login: bool = True) -> Page:
        """GET a page (relative to the Connect root), logging in first if needed."""
        page = Page(self, self.request("GET", self.url + path))
        if login and page.is_login():
            self.login()
            page = Page(self, self.request("GET", self.url + path))
            if page.is_login():
                raise LoginError(f"Still not logged in after logging in, fetching {path}.")
        return page

    def post(self, url: str, data: dict) -> Page:
        """POST a form. Used by Page for postbacks, rarely needed directly."""
        page = Page(self, self.request("POST", url, data=data))
        if page.is_login():
            raise LoginError("The session expired in the middle of a request: try again.")
        if "mainmessage.aspx" in page.url.lower():
            raise TeamBathError(f"The site returned an error page: {Parse.text(page.soup.body)}")
        return page

    def request(self, method: str, url: str, **kw) -> requests.Response:
        r = self.session.request(method, url, timeout=self.timeout, **kw)
        r.raise_for_status()
        return r

    # ------------------------------------------------------------ high level

    def activity_types(self) -> list[ActivityType]:
        """All activity types, e.g. ("SQUASH", "Squash"), ("SWIMMING", "Swimming 50m Pool")."""
        return Parse.activity_types(self.fetch(self.HOME).soup)

    def search(self, day: date | None = None, type: ActivityType | str | None = None
               ) -> list[Activity]:
        """What's on on `day` (default today), optionally of one activity type
        (an ActivityType, its id like "SQUASH", or its name like "squash")."""
        return Parse.search_results(self.search_page(day, type).soup)

    def availability(self, activity: Activity | str, day: date | None = None) -> list[Slot]:
        """The bookable times of an activity (an Activity or its id) on `day` (default today):
        the sessions of a class, or every resource x time slot of a court-type activity."""
        kind, page = self.availability_page(activity, day)
        return Parse.class_slots(page.soup) if kind == "class" else Parse.activity_slots(page.soup)

    def book(self, slot: Slot) -> Booking:
        """Book a free slot from availability(): a court at a time, or a class session.

        Checks the price on the site's confirmation page first. If it isn't £0.00 it
        backs out and raises PaidBookingError: paid bookings aren't supported.
        Anything the site refuses (not eligible, one booking per day...) raises
        TeamBathError with the site's message.
        """
        kind, page = self.availability_page(slot.activity_id, slot.start.date())
        cells = Parse.class_cells(page.soup) if kind == "class" else Parse.activity_cells(page.soup)
        current, button = next(((s, el) for s, el in cells if (s.start, s.resource) ==
                                (slot.start, slot.resource)), (None, None))
        if current is None or not current.available:
            raise TeamBathError(f"{self.describe(slot)} isn't available"
                                f"{f' ({current.status})' if current else ''}.")
        fields = {}
        if kind == "class":  # "include me": what the page's JavaScript sets before booking
            fields[button["name"].replace("btnBook", "hMemberIncluded")] = "true"
        confirm = page.click(button["name"], fields)
        if error := Parse.error(confirm.soup):
            raise TeamBathError(f"{self.describe(slot)}: {error}")
        prices = Parse.prices(confirm.soup)
        if not prices:
            raise TeamBathError(f"{self.describe(slot)}: no booking confirmation page.")
        if not all(Parse.is_free(p) for p in prices):
            confirm.click("ctl00$MainContent$btnCancel")
            raise PaidBookingError(f"{self.describe(slot)} costs {', '.join(prices)}. "
                                   "Paid bookings aren't supported.")
        name, duration = Parse.confirmation(confirm.soup)
        done = confirm.postback("ctl00$MainContent$btnBasket")
        if "mrmbookingconfirmed.aspx" not in done.url.lower():
            raise TeamBathError(f"{self.describe(slot)}: "
                                f"{Parse.error(done.soup) or 'the booking did not go through.'}")
        return Booking(activity_id=slot.activity_id, name=name, start=slot.start,
                       duration=duration or slot.duration, status="Confirmed")

    def bookings(self) -> list[Booking]:
        """Your upcoming bookings."""
        return Parse.bookings(self.fetch(self.BOOKINGS).soup)

    def cancel(self, booking: Booking) -> None:
        """Cancel one of your bookings (from bookings() or book()).

        Only free bookings: cancelling a paid one raises PaidBookingError, without
        cancelling, since refunds aren't supported.
        """
        page = self.fetch(self.BOOKINGS)
        link = next((el for b, el in Parse.booking_rows(page.soup)
                     if (b.activity_id, b.start) == (booking.activity_id, booking.start)), None)
        if link is None:
            raise TeamBathError(f"No booking of {booking.name} at {booking.start:%a %d %b %H:%M}.")
        confirm = page.postback(page.postback_target(link))
        prices = Parse.prices(confirm.soup)
        if not prices or not confirm.soup.select_one('[name="ctl00$MainContent$btnConfirm"]'):
            raise TeamBathError(Parse.error(confirm.soup) or "No cancellation page.")
        if not all(Parse.is_free(p) for p in prices):
            raise PaidBookingError(f"{booking.name} cost {', '.join(prices)}. "
                                   "Cancelling paid bookings isn't supported.")
        confirm.click("ctl00$MainContent$btnConfirm")
        if any((b.activity_id, b.start) == (booking.activity_id, booking.start)
               for b in self.bookings()):
            raise TeamBathError(f"{booking.name} at {booking.start:%a %d %b %H:%M} "
                                "is still booked after cancelling.")

    def account(self) -> Account:
        """Your member details (My Account > General Details)."""
        return Parse.account(self.fetch("MemberManagement/EditMemberDetails.aspx").soup)

    # --------------------------------------------------------------- helpers

    def search_page(self, day: date | None = None, type: ActivityType | str | None = None) -> Page:
        """The results page of the home page's advanced search, for one day."""
        home = self.fetch(self.HOME)
        iso = (day or date.today()).isoformat()
        return home.postback(SEARCH_FORM + "_searchBtn", fields={
            SEARCH_FORM + "ActivityGroups": self.type_id(home, type),
            SEARCH_FORM + "Activities": "",
            SEARCH_FORM + "startDate": iso,
            SEARCH_FORM + "endDate": iso,
        })

    def availability_page(self, activity: Activity | str, day: date | None = None
                          ) -> tuple[str, Page]:
        """("class", the class page) or ("activity", the grid page) for an activity on a day."""
        day = day or date.today()
        activity_id = activity.id if isinstance(activity, Activity) else activity
        page = self.search_page(day)
        link = next((a for a in page.soup.select(f"a[id^={RESULTS}][id$=lnkActivitySelect_lg]")
                     if Parse.qa(a).get("ActivityID") == activity_id), None)
        if link is None:
            raise TeamBathError(f"{activity_id} isn't on the site's list for {day:%a %d %b %Y}.")
        kind = Parse.kind(link)
        if kind == "class":
            button = page.soup.find(id=link["id"].replace("lnkActivitySelect", "btnAvailability"))
            return kind, page.postback(page.postback_target(button))
        if kind == "activity":
            return kind, page.postback(page.postback_target(link))
        raise TeamBathError(f"Don't know how to read availability for {kind!r} ({activity_id}).")

    @staticmethod
    def describe(slot: Slot) -> str:
        where = f" {slot.resource}" if slot.resource else ""
        return f"{slot.activity_id}{where} at {slot.start:%a %d %b %H:%M}"

    @staticmethod
    def type_id(home: Page, type: ActivityType | str | None) -> str:
        """The dropdown value for an activity type given as an ActivityType, id or name."""
        if type is None:
            return ""
        if isinstance(type, ActivityType):
            return type.id
        key = type.strip().lower()
        types = Parse.activity_types(home.soup)
        for t in types:
            if key in (t.id.lower(), t.name.lower()):
                return t.id
        names = ", ".join(t.name for t in types)
        raise TeamBathError(f"No activity type {type!r}. Known types: {names}")
