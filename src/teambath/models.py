"""What the library returns: plain dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class ActivityType:
    """A category from the "Activity Type" dropdown, e.g. ("SQUASH", "Squash")."""

    id: str
    name: str


@dataclass
class Activity:
    """Something bookable on a given day.

    kind is "class" for sessions at a fixed time with a number of spaces (swims, fitness
    classes) and "activity" for a grid of resources and time slots (courts, pitches).
    """

    id: str  # e.g. "SQUASHFREE2", "SFIT50MR109544"
    name: str
    kind: str  # "class" | "activity"
    type: str  # the activity type's name, e.g. "Swimming 50m Pool"
    description: str
    status: str | None  # classes only: "Space" or "Full"


@dataclass
class Slot:
    """One bookable time: a class session, or one court at one time."""

    activity_id: str
    start: datetime
    duration: int | None  # minutes (classes only: the court grid doesn't say)
    resource: str | None  # e.g. "Squash Court 1" (activities only)
    available: bool
    spaces: int | None  # spaces left (classes only)
    status: str  # the site's own wording, e.g. "Available", "No Space & No Waiting List"


@dataclass
class Account:
    member_id: str
    first_name: str
    last_name: str
    email: str
    birth_date: date | None
    mobile: str
    address: list[str]  # non-empty address lines, postcode last


@dataclass
class Booking:
    """One of your bookings."""

    activity_id: str
    name: str  # e.g. "Squash Students"
    start: datetime
    duration: int | None  # minutes
    status: str  # e.g. "Confirmed"
