"""Use Team Bath's sports booking site (bookings.teambath.com) from Python."""

from .client import LoginError, PaidBookingError, TeamBath, TeamBathError
from .models import Account, Activity, ActivityType, Booking, Slot

__all__ = ["Account", "Activity", "ActivityType", "Booking", "LoginError", "PaidBookingError",
           "Slot", "TeamBath", "TeamBathError"]
__version__ = "0.2.0"
