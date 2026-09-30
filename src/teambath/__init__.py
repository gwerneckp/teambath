"""Use Team Bath's sports booking site (bookings.teambath.com) from Python."""

from .client import LoginError, TeamBath, TeamBathError
from .models import Account, Activity, ActivityType, Slot

__all__ = ["Account", "Activity", "ActivityType", "LoginError", "Slot", "TeamBath",
           "TeamBathError"]
__version__ = "0.1.0"
