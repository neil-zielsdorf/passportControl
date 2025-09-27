from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Tuple, Optional

def get_expiry_status(expiry_date: date) -> Tuple[str, str]:
    """
    Returns (status_color, status_text) based on expiry date
    Following the 6-month international travel rule
    """
    if not expiry_date:
        return "gray", "No expiry date"

    today = date.today()
    months_until_expiry = relativedelta(expiry_date, today).months + \
                         relativedelta(expiry_date, today).years * 12
    days_until_expiry = (expiry_date - today).days

    if days_until_expiry < 0:
        return "red", "Expired"
    elif days_until_expiry <= 7:
        return "red", "Critical (7 days)"
    elif days_until_expiry <= 30:
        return "red", "Urgent (1 month)"
    elif months_until_expiry <= 3:
        return "orange", "Act Now (3 months)"
    elif months_until_expiry <= 6:
        return "yellow", "Plan Renewal (6 months)"
    else:
        return "green", "Safe"

def days_until_expiry(expiry_date: date) -> int:
    """Returns number of days until expiry (negative if expired)"""
    if not expiry_date:
        return 0
    return (expiry_date - date.today()).days

def format_date_friendly(date_obj: Optional[date]) -> str:
    """Format date in a user-friendly way"""
    if not date_obj:
        return "Not set"
    return date_obj.strftime("%B %d, %Y")

def get_notification_dates(expiry_date: date) -> list:
    """Get list of dates when notifications should be sent"""
    if not expiry_date:
        return []

    notification_days = [180, 90, 30, 14, 7, 1]  # Days before expiry
    notification_dates = []

    for days in notification_days:
        notification_date = expiry_date - timedelta(days=days)
        if notification_date >= date.today():
            notification_dates.append(notification_date)

    return notification_dates