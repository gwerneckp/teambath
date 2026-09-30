"""Every basketball session today and whether it has space.

    TEAMBATH_EMAIL=... TEAMBATH_PIN=... uv run python examples/basketball.py [YYYY-MM-DD]
"""

import os
import sys
from datetime import date

from teambath import TeamBath

tb = TeamBath(os.environ["TEAMBATH_EMAIL"], os.environ["TEAMBATH_PIN"])
day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()

print(f"Basketball on {day:%a %d %b %Y}\n")
for activity in tb.search(day, type="Basketball"):
    slots = tb.availability(activity, day)
    free = [s for s in slots if s.available]
    print(f"{activity.name}  ({len(free)}/{len(slots)} slots free)")
    for s in slots:
        where = f"  {s.resource}" if s.resource else ""
        spaces = f"  {s.spaces} spaces" if s.spaces is not None else ""
        print(f"  {s.start:%H:%M}{where}  {s.status}{spaces}")
    print()
