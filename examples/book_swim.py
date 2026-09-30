"""Book the earliest free swim on a day (default: this Friday). Safe to run again and again.

    TEAMBATH_EMAIL=... TEAMBATH_PIN=... uv run python examples/book_swim.py
    ... book_swim.py --date 2026-10-09 --lane fast --dry-run

Idempotent: if you already have a swim booked that day, it says so and books nothing.
"""

import argparse
import os
import re
from datetime import date, timedelta

from teambath import PaidBookingError, TeamBath, TeamBathError

today = date.today()
parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--date", type=date.fromisoformat,
                    default=today + timedelta(days=(4 - today.weekday()) % 7),
                    help="YYYY-MM-DD (default: this Friday)")
parser.add_argument("--lane", choices=["fast", "med", "slow"], help="only this lane speed")
parser.add_argument("--dry-run", action="store_true", help="show what it would book")
args = parser.parse_args()

tb = TeamBath(os.environ["TEAMBATH_EMAIL"], os.environ["TEAMBATH_PIN"])
swims = [a for a in tb.search(args.date, type="SWIMMING") if a.kind == "class"]

# Already booked a swim that day (any lane)? Then there's nothing to do.
ids, names = {a.id for a in swims}, {a.name for a in swims}
booked = [b for b in tb.bookings()
          if b.start.date() == args.date and (b.activity_id in ids or b.name in names)]
if booked:
    print(f"Already booked: {booked[0].name} at {booked[0].start:%a %d %b %H:%M}. Nothing to do.")
    raise SystemExit(0)

# Names carry the time ("Swimfit/fri/07.00/fast"), so try the earliest first.
swims = [a for a in swims if a.status == "Space"
         and (not args.lane or a.name.endswith(f"/{args.lane}"))]
swims.sort(key=lambda a: re.search(r"/(\d\d\.\d\d)", a.name + "/99.99")[1])
if not swims:
    print(f"No swim with space on {args.date:%a %d %b} (maybe not released yet).")
    raise SystemExit(1)

for swim in swims:
    for slot in (s for s in tb.availability(swim, args.date) if s.available):
        if args.dry_run:
            print(f"Would book {swim.name} at {slot.start:%a %d %b %H:%M} ({slot.spaces} spaces).")
            raise SystemExit(0)
        try:
            booking = tb.book(slot)
        except PaidBookingError as e:
            print(f"Skipping {swim.name}: {e}")
            continue
        except TeamBathError as e:
            print(f"Couldn't book {swim.name}: {e}")
            continue
        print(f"Booked {booking.name} at {booking.start:%a %d %b %H:%M}.")
        raise SystemExit(0)
print("Tried every swim with space; none could be booked.")
raise SystemExit(1)
