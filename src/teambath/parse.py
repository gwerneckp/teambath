"""Turn the site's HTML into models. Everything site-specific about the markup lives here.

Most useful facts are in `data-qa-id` attributes (the site's own test hooks), e.g.
"...ActivityID=SQUASHFREE2 ResourceID=0 Date=2026/10/1 Time=07:00 Availability= Available
Court=Squash Court 1", which are steadier than the visible text.
"""

from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from .models import Account, Activity, ActivityType, Slot

SEARCH = "ctl00_MainContent__advanceSearchUserControl_"
RESULTS = "ctl00_MainContent__advanceSearchResultsUserControl_"
KINDS = {"classes": "class", "activity": "activity"}


class Parse:
    # A data-qa-id is "prefix-Key=value Key=value ...", where values may contain spaces
    # ("Court=Squash Court 1") and may be empty ("Time= Availability= Not Available").
    QA_PAIR = re.compile(r"(\w+)=(.*?)(?=\s+\w+=|$)")

    @staticmethod
    def qa(el: Tag) -> dict[str, str]:
        """The Key=value pairs of an element's data-qa-id."""
        return {k: v.strip() for k, v in Parse.QA_PAIR.findall(el.get("data-qa-id", ""))}

    @staticmethod
    def text(el: Tag | None) -> str:
        return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""

    @staticmethod
    def login_error(soup: BeautifulSoup) -> str | None:
        """The message the login page shows after a failed attempt, if any."""
        return Parse.text(soup.select_one("#ctl00_MainContent_errorbox")) or None

    @staticmethod
    def activity_types(soup: BeautifulSoup) -> list[ActivityType]:
        return [ActivityType(o["value"], Parse.text(o))
                for o in soup.select(f"#{SEARCH}ActivityGroups option") if o.get("value")]

    @staticmethod
    def search_results(soup: BeautifulSoup) -> list[Activity]:
        """Activities listed on a search results page, classes first, in page order."""
        out = []
        for link in soup.select(f"a[id^={RESULTS}][id$=lnkActivitySelect_lg]"):
            qa = Parse.qa(link)
            row = link.find_parent("div", class_="div-row")
            raw_kind = qa.get("ActivityType", "")
            out.append(Activity(
                id=qa["ActivityID"],
                name=Parse.text(link),
                kind=KINDS.get(raw_kind.lower(), raw_kind.lower()),
                type=Parse.text(row.select_one(".greysurround")),
                description=Parse.text(row.select_one(".flexible-comment-text")),
                status=qa.get("StatusClass") or None,
            ))
        return out

    @staticmethod
    def no_results(soup: BeautifulSoup) -> bool:
        return "No results were found" in soup.get_text()

    @staticmethod
    def class_slots(soup: BeautifulSoup) -> list[Slot]:
        """Sessions on a class page (mrmClassStatus.aspx)."""
        out = []
        for book in soup.select("input[id^=ctl00_MainContent_ClassStatus_][id$=_btnBook]"):
            qa = Parse.qa(book)
            spaces_btn = soup.find(id=book["id"].replace("_btnBook", "_btnAvaliable"))
            spaces_text = spaces_btn.get("value", "") if spaces_btn else ""
            m = re.search(r"(\d+)\s+spaces?", spaces_text)
            status = qa.get("Status", "")
            out.append(Slot(
                activity_id=qa["ActivityID"],
                start=datetime.strptime(qa["Date"], "%d/%m/%Y %H:%M:%S"),
                duration=int(qa["Duration"]) if qa.get("Duration", "").isdigit() else None,
                resource=None,
                available=status == "Available",
                spaces=int(m[1]) if m else (0 if "full" in spaces_text.lower() else None),
                status=status,
            ))
        return out

    @staticmethod
    def activity_slots(soup: BeautifulSoup) -> list[Slot]:
        """The resource x time grid on an activity page (mrmProductStatus.aspx), row by row."""
        out = []
        for cell in soup.select("#ctl00_MainContent_grdResourceView td[data-qa-id], "
                                "#ctl00_MainContent_grdResourceView td > input[data-qa-id]"):
            qa = Parse.qa(cell)
            td = cell if cell.name == "td" else cell.parent
            classes = td.get("class", [])
            day = datetime.strptime(qa["Date"], "%Y/%m/%d")
            hhmm = qa.get("Time") or Parse.text(cell) or cell.get("value", "")
            hour, minute = (int(x) for x in hhmm.split(":"))
            out.append(Slot(
                activity_id=qa["ActivityID"],
                start=day.replace(hour=hour, minute=minute),
                duration=None,
                resource=qa.get("Court") or None,
                available="itemavailable" in classes,
                spaces=None,
                status=qa.get("Availability", ""),
            ))
        return out

    @staticmethod
    def account(soup: BeautifulSoup) -> Account:
        """The General Details tab of My Account."""
        fields = {}
        for label in soup.select("label.editDetailsLabel[for]"):
            box = soup.find(id=label["for"])
            if box is not None:
                fields[Parse.text(label)] = (box.get("value") or "").strip()
        birth = fields.get("Birth Date", "")
        address = [fields.get(k, "") for k in ("Home Property Name", "Home Street", "Home Locality",
                                               "Home Town", "Home Region", "Home Post Code")]
        return Account(
            member_id=fields.get("ID", ""),
            first_name=fields.get("First Names", ""),
            last_name=fields.get("Last Name", ""),
            email=fields.get("Home Email", ""),
            birth_date=datetime.strptime(birth, "%d/%m/%Y").date() if birth else None,
            mobile=fields.get("Mobile Phone", ""),
            address=[line for line in address if line],
        )
