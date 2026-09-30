<p align="center">
  <img src="assets/logo.svg" alt="teambath logo" width="128">
</p>

<h1 align="center">teambath</h1>

<p align="center"><b>Find a free court at Team Bath without clicking through the booking site.</b></p>

Want a squash court this week? On [bookings.teambath.com](https://bookings.teambath.com/Connect/memberHomePage.aspx) that means log in, search, open the activity, and check the grid, one day at a time. Then do it all again for badminton.

teambath does that clicking for you, from Python. It can check courts and classes, and book and cancel free slots.

## Install

```bash
pip install git+https://github.com/gwerneckp/teambath
```

Requires Python 3.11+.

## Quick start

```python
from datetime import date, timedelta
from teambath import TeamBath

tb = TeamBath("abc123@bath.ac.uk", "1234")      # the email and PIN you log in with
tomorrow = date.today() + timedelta(days=1)

free = [s for s in tb.availability("SQUASHFREE2", tomorrow) if s.available]
print(free[0].start, free[0].resource)          # 2026-10-01 07:00:00 Squash Court 1

booking = tb.book(free[0])
tb.cancel(booking)                              # changed your mind
```

Use `tb.search(day, type="squash")` to find other activities and their ids, and `tb.bookings()` to see what you've booked. There are more scripts in [`examples/`](examples/).

## Good to know

- **Only free bookings.** If a slot costs anything, `book()` backs out and nothing is booked or charged. P.A.Y.G. courts and some fitness classes are paid.
- **Pick the Students version** of an activity (e.g. `SQUASHFREE2`). That's the free one with your Sports Pass.
- **How far ahead you can book** depends on the activity: 5 days for free student courts and fitness classes, 1–2 days for swimming, weeks for P.A.Y.G. courts.
- "Not Available" means taken *or* not released yet. The site doesn't say which.

## Development

```bash
uv sync
uv run pytest                                               # offline, no account needed
TEAMBATH_EMAIL=... TEAMBATH_PIN=... uv run pytest -m live   # read-only checks against the real site
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
