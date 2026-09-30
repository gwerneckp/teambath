"""ASP.NET WebForms plumbing.

The site is a WebForms app: every page is one big <form>, and clicking almost anything
("postback") re-submits that form, hidden __VIEWSTATE included, with __EVENTTARGET naming
what was clicked. A Page holds one response and can produce the next one the way a
browser would.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from .client import TeamBath


class Page:
    POSTBACK = re.compile(r"__doPostBack\('([^']+)'")

    def __init__(self, client: TeamBath, response: requests.Response):
        self.client = client
        self.response = response
        self.url = response.url
        self.soup = BeautifulSoup(response.text, "html.parser")

    def form_data(self) -> dict[str, str]:
        """The fields a browser would submit from this page's form, as it stands."""
        form = self.soup.select_one("form#aspnetForm") or self.soup
        data = {}
        for el in form.select("input[name], select[name], textarea[name]"):
            if el.has_attr("disabled"):
                continue
            name = el["name"]
            if el.name == "select":
                option = el.select_one("option[selected]") or el.select_one("option")
                if option is not None:
                    data[name] = option.get("value", option.get_text())
            elif el.name == "textarea":
                data[name] = el.get_text()
            else:
                kind = (el.get("type") or "text").lower()
                if kind in ("submit", "button", "image", "reset", "file"):
                    continue  # only the clicked button is sent
                if kind in ("checkbox", "radio") and not el.has_attr("checked"):
                    continue
                data[name] = el.get("value", "on" if kind in ("checkbox", "radio") else "")
        return data

    def action(self) -> str:
        form = self.soup.select_one("form#aspnetForm")
        return urljoin(self.url, form.get("action", "") if form else "")

    def postback(self, target: str, argument: str = "", fields: dict | None = None) -> Page:
        """Do what `javascript:__doPostBack(target, argument)` does, after setting `fields`."""
        data = self.form_data()
        data.update(fields or {})
        data["__EVENTTARGET"] = target
        data["__EVENTARGUMENT"] = argument
        return self.client.post(self.action(), data)

    def submission(self, button: str, fields: dict | None = None) -> dict[str, str]:
        """The data sent by clicking the submit button named `button`, after setting `fields`."""
        data = self.form_data()
        data.update(fields or {})
        data[button] = self.soup.select_one(f'[name="{button}"]').get("value", "")
        return data

    def postback_target(self, element) -> str:
        """The __EVENTTARGET behind a `javascript:__doPostBack(...)` link or button."""
        m = self.POSTBACK.search(element.get("href") or element.get("onclick") or "")
        if not m:
            raise ValueError(f"Not a postback control: {element}")
        return m[1]

    def is_login(self) -> bool:
        return "mrmlogin.aspx" in self.url.lower()
