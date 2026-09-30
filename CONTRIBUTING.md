# Contributing

Thanks for your interest! teambath is made for **Team Bath's booking site**, and that's the only site it's tested against. Contributions are welcome with that in mind.

## Using it on another Gladstone Connect site

Many leisure centres and universities run the same booking software, so teambath may partly work on yours with `TeamBath(email, pin, url="https://your-site/Connect/")`. You can:

- **Fork it** and adapt it to your site. This is usually the quickest route. Everything about the markup is in `src/teambath/parse.py`, and the login and search form field names are in `src/teambath/client.py`.
- **Open an issue** saying what worked and what didn't, with anything personal removed.
- **Send a PR** if your change is general and doesn't change behaviour at Team Bath. I can only test against Team Bath, so I may not be able to accept changes I can't verify.

## When the site changes

1. Run the live tests to see what broke: `TEAMBATH_EMAIL=... TEAMBATH_PIN=... uv run pytest -m live`.
2. Refresh the saved pages with `TEAMBATH_EMAIL=... TEAMBATH_PIN=... uv run python tests/capture_fixtures.py`. It replaces your personal details, and other people's, with fake ones, and it refuses to save a page if any of yours survive.
3. Fix `parse.py`, then update the expected values in `tests/test_parse.py` and `tests/test_client.py`. They're specific to the day the pages were captured.
4. **Before committing, check the fixtures by eye** for anything personal the scrubber doesn't know about, such as new staff names or phone numbers in descriptions.

## Ground rules

- **Never commit real personal details**: not yours, not other members', not staff's. Fixtures go through `capture_fixtures.py`.
- **Never commit a PIN**, not even in a test. Live tests read it from the environment.
- Keep it simple: no feature bloat. Prefer extending the `TeamBath` class over adding layers, and new dependencies need a good reason.
- Helpers go in a class: a private method or staticmethod on the class that uses them. No loose module-level `_functions`.
- Keep calls stateless: each public method starts from a fresh page.
- Nothing that books, cancels or pays runs in the default test suite.

## Setup

```bash
uv sync
uv run pytest
uv run ruff check src tests
```

The default tests are offline: HTTP is mocked with [responses](https://github.com/getsentry/responses) and answered with the saved pages.
