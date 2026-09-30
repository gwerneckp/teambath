"""WebForms form handling: what gets submitted, like a browser would."""

from types import SimpleNamespace

import pytest

from teambath.page import Page

FORM = """<form method="post" action="./next.aspx" id="aspnetForm">
<input type="hidden" name="__VIEWSTATE" value="vs">
<input type="hidden" name="__EVENTTARGET" value="">
<input type="text" name="name" value="Alex">
<input type="text" name="empty">
<input type="text" name="off" value="x" disabled="disabled">
<input type="checkbox" name="on" value="1" checked="checked">
<input type="checkbox" name="unticked" value="1">
<input type="radio" name="r" value="a"><input type="radio" name="r" value="b" checked>
<select name="pick"><option value="1">One</option><option value="2" selected>Two</option></select>
<select name="first"><option value="">Any</option><option value="z">Z</option></select>
<textarea name="note">hi</textarea>
<input type="submit" name="go" value="Go">
<a id="lnk" href="javascript:__doPostBack('ctl00$Main$lnk','')">link</a>
</form>"""


class Recorder:
    """Stands in for TeamBath: records posts and answers with the same form."""

    def __init__(self):
        self.posts = []

    def post(self, url, data):
        self.posts.append((url, data))
        return "next page"


@pytest.fixture
def page():
    client = Recorder()
    response = SimpleNamespace(url="https://site.test/Connect/here.aspx", text=FORM)
    return Page(client, response)


def test_form_data_like_a_browser(page):
    assert page.form_data() == {"__VIEWSTATE": "vs", "__EVENTTARGET": "", "name": "Alex",
                                "empty": "", "on": "1", "r": "b", "pick": "2", "first": "",
                                "note": "hi"}


def test_postback(page):
    assert page.postback("ctl00$Main$lnk", fields={"name": "Sam"}) == "next page"
    [(url, data)] = page.client.posts
    assert url == "https://site.test/Connect/next.aspx"
    assert data["__EVENTTARGET"] == "ctl00$Main$lnk" and data["__EVENTARGUMENT"] == ""
    assert (data["name"], data["__VIEWSTATE"]) == ("Sam", "vs")
    assert "go" not in data


def test_submission_includes_only_the_clicked_button(page):
    data = page.submission("go", {"name": "Sam"})
    assert data["go"] == "Go" and data["name"] == "Sam"


def test_postback_target(page):
    assert page.postback_target(page.soup.find(id="lnk")) == "ctl00$Main$lnk"
    with pytest.raises(ValueError):
        page.postback_target(page.soup.select_one("textarea"))


def test_is_login():
    assert Page(Recorder(), SimpleNamespace(url="https://s/Connect/MRMLogin.aspx",
                                            text="")).is_login()

