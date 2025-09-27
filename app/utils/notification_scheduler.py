import logging
import threading
import time
from datetime import date, datetime, timedelta
from typing import List, Dict, Any
from database.models import get_database, Document, Person
from utils.date_utils import days_until_expiry, get_expiry_status
from integrations.pushover import get_pushover_client
from integrations.caldav_client import get_caldav_client

logger = logging.getLogger(__name__)

class NotificationScheduler:
    """
    Background notification scheduler
    Checks for document expiries and sends notifications via configured channels
    """

    def __init__(self):
        self.db = get_database()
        self.pushover = get_pushover_client()
        self.caldav = get_caldav_client()
        self.running = False
        self.thread = None
        self.check_interval = 3600  # Check every hour
        self.last_daily_check = None

    def start(self):
        """Start the notification scheduler"""
        if self.running:
            logger.warning("Notification scheduler already running")
            return

        logger.info("Starting notification scheduler")
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the notification scheduler"""
        if not self.running:
            return

        logger.info("Stopping notification scheduler")
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                self._check_notifications()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Notification scheduler error: {e}")
                time.sleep(60)  # Wait a minute before retrying

    def _check_notifications(self):
        """Check for documents needing notifications"""
        logger.debug("Checking for notification triggers")

        # Get all documents and people
        documents = self.db.get_documents()
        people = self.db.get_people()

        if not documents or not people:
            return

        # Create person lookup
        person_lookup = {p.id: p for p in people}

        # Check each document
        urgent_count = 0
        warning_count = 0
        notifications_sent = 0

        for doc in documents:
            person = person_lookup.get(doc.holder_id)
            if not person:
                continue

            days_left = days_until_expiry(doc.expiry_date)
            status_color, _ = get_expiry_status(doc.expiry_date)

            # Count documents by urgency
            if status_color == 'red':
                urgent_count += 1
            elif status_color in ['orange', 'yellow']:
                warning_count += 1

            # Check if notification is needed
            if self._should_send_notification(doc, days_left):
                # Send Pushover notification
                if self.pushover.send_document_expiry_notification(doc, person, days_left):
                    notifications_sent += 1
                    logger.info(f"Sent expiry notification for {person.name}'s {doc.type}")

                # Create/update calendar events
                if days_left <= 30:  # Urgent calendar event
                    self.caldav.create_expiry_warning(doc, person, days_left)
                elif days_left <= 180:  # Standard renewal reminder
                    self.caldav.create_renewal_reminder(doc, person)

                # Record that we sent this notification
                self._record_notification_sent(doc.id, days_left)

        # Send daily summary if it's a new day
        if self._should_send_daily_summary():
            if self.pushover.send_family_summary(urgent_count, warning_count):
                logger.info("Sent daily family summary")
            self.last_daily_check = date.today()

        if notifications_sent > 0:
            logger.info(f"Sent {notifications_sent} notifications")

    def _should_send_notification(self, document: Document, days_left: int) -> bool:
        """Determine if we should send a notification for this document"""
        # Get notification schedule from settings
        schedule = self.db.get_setting('notification_schedule', [180, 90, 30, 14, 7, 1])

        # Check if this day count is in our notification schedule
        if days_left not in schedule:
            return False

        # Check if we've already sent a notification for this threshold
        last_notification = self._get_last_notification(document.id)

        if last_notification:
            # Don't send if we've already notified for this threshold
            if last_notification.get('days_left') == days_left:
                return False

            # For urgent notifications (7 days or less), send daily
            if days_left <= 7:
                last_sent = datetime.fromisoformat(last_notification.get('timestamp', '1970-01-01'))
                if (datetime.now() - last_sent).days < 1:
                    return False

        return True

    def _should_send_daily_summary(self) -> bool:
        """Check if we should send the daily family summary"""
        # Only send once per day
        if self.last_daily_check == date.today():
            return False

        # Check if daily summaries are enabled
        summary_enabled = self.db.get_setting('daily_summary_enabled', True)
        if not summary_enabled:
            return False

        # Send at 8 AM local time
        now = datetime.now()
        if now.hour != 8:
            return False

        return True

    def _record_notification_sent(self, document_id: int, days_left: int):
        """Record that we sent a notification"""
        notifications = self.db.get_setting('notification_history', {})

        notifications[str(document_id)] = {
            'days_left': days_left,
            'timestamp': datetime.now().isoformat()
        }

        self.db.set_setting('notification_history', notifications)

    def _get_last_notification(self, document_id: int) -> Dict[str, Any]:
        """Get the last notification sent for a document"""
        notifications = self.db.get_setting('notification_history', {})
        return notifications.get(str(document_id), {})

    def check_now(self) -> Dict[str, Any]:
        """Manually trigger notification check and return results"""
        logger.info("Manual notification check triggered")

        documents = self.db.get_documents()
        people = self.db.get_people()

        if not documents or not people:
            return {
                'success': True,
                'message': 'No documents or people to check',
                'notifications_sent': 0,
                'urgent_count': 0,
                'warning_count': 0
            }

        person_lookup = {p.id: p for p in people}
        urgent_count = 0
        warning_count = 0
        notifications_sent = 0

        for doc in documents:
            person = person_lookup.get(doc.holder_id)
            if not person:
                continue

            days_left = days_until_expiry(doc.expiry_date)
            status_color, _ = get_expiry_status(doc.expiry_date)

            if status_color == 'red':
                urgent_count += 1
            elif status_color in ['orange', 'yellow']:
                warning_count += 1

            # For manual check, send notifications for urgent items regardless of history
            if days_left <= 30:
                if self.pushover.send_document_expiry_notification(doc, person, days_left):
                    notifications_sent += 1

                # Update calendar
                if days_left <= 7:
                    self.caldav.create_expiry_warning(doc, person, days_left)
                else:
                    self.caldav.create_renewal_reminder(doc, person)

        # Send summary
        if self.pushover.send_family_summary(urgent_count, warning_count):
            notifications_sent += 1

        return {
            'success': True,
            'message': f'Manual check complete',
            'notifications_sent': notifications_sent,
            'urgent_count': urgent_count,
            'warning_count': warning_count
        }

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status information"""
        return {
            'running': self.running,
            'check_interval_minutes': self.check_interval // 60,
            'last_daily_check': self.last_daily_check.isoformat() if self.last_daily_check else None,
            'pushover_enabled': self.pushover.enabled,
            'caldav_enabled': self.caldav.enabled
        }


# Global scheduler instance
_notification_scheduler = None

def get_notification_scheduler() -> NotificationScheduler:
    """Get global notification scheduler instance"""
    global _notification_scheduler
    if _notification_scheduler is None:
        _notification_scheduler = NotificationScheduler()
    return _notification_scheduler

def start_notification_scheduler():
    """Start the global notification scheduler"""
    scheduler = get_notification_scheduler()
    scheduler.start()

def stop_notification_scheduler():
    """Stop the global notification scheduler"""
    scheduler = get_notification_scheduler()
    scheduler.stop()