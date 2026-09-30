# Roadmap

teambath is built around **Team Bath's booking site**. New features come from what Bath students actually do on it, and are tested there. The guiding rule is **stay small**: one `TeamBath` class, plain dataclasses, two dependencies. The foundations come first (a clean read-only library with real-page tests), and only then the things built on top of them.

## Done (0.1): read-only, working at Team Bath

- [x] Log in with email and PIN, and log in again automatically when the session expires
- [x] Activity types, and search by day and type
- [x] Availability: class sessions with spaces left, and court × time grids
- [x] Account details
- [x] Offline tests against real, scrubbed pages from the site, plus opt-in live tests
- [x] A capture script to refresh the test pages when the site changes

## Now (0.2): free bookings

- [x] **`bookings()`**: your upcoming bookings
- [x] **`book(slot)`** for a court slot or a class session. It checks the price first and refuses anything that isn't free (`PaidBookingError`), and passes the site's refusals through (not eligible, one per day...)
- [x] **`cancel(booking)`** for free bookings

## Next (0.3): CLI and MCP

- [ ] A `teambath` command, e.g. `teambath search squash --date tomorrow`, `teambath slots SQUASHFREE2 thu`, `teambath bookings`, with `--json` for scripts and agents
- [ ] An optional MCP server (`[mcp]` extra) with read-only tools first, and booking and cancelling as separate, explicit tools

## 1.0: stable release

- [ ] A stable, documented API
- [ ] Published on PyPI

## Not in scope

- Paid bookings, the basket and payments. They stay on the website.
