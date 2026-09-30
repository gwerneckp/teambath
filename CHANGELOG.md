# Changelog

## 0.1.0 (unreleased)

First version: read-only, built and tested against Team Bath's booking site.

- `TeamBath(email, pin)` client: logs in on first use and again when the session expires; `LoginError` with the site's message on a wrong PIN
- `activity_types()`, `search(day, type)`, `availability(activity, day)` for class sessions and court grids, `account()`
- Offline tests against real pages from the site, scrubbed of personal details, plus opt-in live tests
- `tests/capture_fixtures.py` to refresh those pages when the site changes
- `examples/basketball.py`
