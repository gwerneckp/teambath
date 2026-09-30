# Changelog

## 0.2.0 (unreleased)

- `book(slot)`, `bookings()` and `cancel(booking)` for free bookings, courts and classes alike
- `PaidBookingError`: `book()` checks the price on the site's confirmation page and backs out of anything that isn't £0.00; `cancel()` won't cancel a paid booking
- The site's own refusal messages ("Sorry, you are not permitted to book at the time selected.") come through as `TeamBathError`

## 0.1.0 (unreleased)

First version: read-only, built and tested against Team Bath's booking site.

- `TeamBath(email, pin)` client: logs in on first use and again when the session expires; `LoginError` with the site's message on a wrong PIN
- `activity_types()`, `search(day, type)`, `availability(activity, day)` for class sessions and court grids, `account()`
- Offline tests against real pages from the site, scrubbed of personal details, plus opt-in live tests
- `tests/capture_fixtures.py` to refresh those pages when the site changes
- `examples/basketball.py`
