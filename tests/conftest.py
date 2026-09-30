from pathlib import Path

import pytest
from bs4 import BeautifulSoup

FIXTURES = Path(__file__).parent / "fixtures"


class Fixtures:
    """Real pages from the site, scrubbed (see capture_fixtures.py). Captured on Wed 30 Sep
    2026; "tomorrow" in them is Thu 1 Oct 2026."""

    @staticmethod
    def html(name: str) -> str:
        return (FIXTURES / f"{name}.html").read_text()

    @staticmethod
    def soup(name: str) -> BeautifulSoup:
        return BeautifulSoup(Fixtures.html(name), "html.parser")


@pytest.fixture
def pages():
    return Fixtures
