# Roadmap

teambath is built around **Team Bath's booking site**. New features come from what Bath students actually do on it, and are tested there. The guiding rule is **stay small**: one `TeamBath` class, plain dataclasses, two dependencies. The foundations come first (a clean read-only library with real-page tests), and only then the things built on top of them.

## Now (0.1): read-only, working at Team Bath

- [x] Log in with email and PIN, and log in again automatically when the session expires
- [x] Activity types, and search by day and type
- [x] Availability: class sessions with spaces left, and court × time grids
- [x] Account details
- [x] Offline tests against real, scrubbed pages from the site, plus opt-in live tests
- [x] A capture script to refresh the test pages when the site changes

## Next (0.2): your bookings, then booking

- [ ] **`bookings()`**: your upcoming bookings. The page needs a real booking before its markup can be captured, so this is first.
- [ ] **Book** a court slot or a class session (`book(slot)`), with clear errors for the site's rules: full, outside the booking window, one session per day, not eligible.
- [ ] **Cancel** a booking.
- [ ] Live tests for booking and cancelling that clean up after themselves, e.g. book a free student slot and cancel it straight away. They'd be opt-in, since they change real state.

## Then (0.3): CLI and MCP

- [ ] A `teambath` command, e.g. `teambath search squash --date tomorrow`, `teambath slots SQUASHFREE2 thu`, `teambath bookings`, with `--json` for scripts and agents
- [ ] An optional MCP server (`[mcp]` extra) with read-only tools first, and booking and cancelling as separate, explicit tools

## Later

- [ ] Find when the booking windows open (midnight, or a rolling window) and document it per activity
- [ ] Watch a slot and tell you, or book it, when it's released or someone cancels, within the site's rules
- [ ] Export your bookings to a calendar (`.ics`)
- [ ] `availability()` for courses and holiday camps (`kind="courses"`)
- [ ] Basket and invoices, read-only

## Maybe / needs thought

- Making it easier to point at other Gladstone Connect sites. It's a fork away today; only worth it if people ask.
- Changing PIN and contact preferences. Rarely needed, and risky to automate.

## Not planned

- Paying for anything. Payments stay in the browser.
- Getting around Team Bath's rules (booking limits, eligibility, windows) or grabbing slots faster than a person could.
- Crawling the site or hammering it with requests.
