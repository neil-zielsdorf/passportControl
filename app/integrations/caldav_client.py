import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import date, datetime, timedelta
from urllib.parse import urljoin
import caldav
from caldav.lib import error
from icalendar import Calendar, Event
from app.database.models import get_database, Document, Person
from app.utils.date_utils import get_notification_dates

logger = logging.getLogger(__name__)

class CalDAVClient:
    """
    CalDAV calendar integration with graceful degradation
    Creates renewal reminder events in Nextcloud/other CalDAV servers
    """

    def __init__(self):
        self.db = get_database()
        self.enabled = self._check_configuration()
        self.config = self._get_config()
        self.client = None
        self.calendar = None

        if self.enabled:
            self._initialize_client()

    def _get_config(self) -> Dict[str, Any]:
        """Get CalDAV configuration from database"""
        return self.db.get_setting('caldav', {
            'enabled': False,
            'caldav_url': '',
            'username': '',
            'password': '',
            'calendar_name': 'Passport Renewals',
            'auto_discovery': True
        })

    def _check_configuration(self) -> bool:
        """Check if CalDAV is properly configured"""
        config = self._get_config()
        return (
            config.get('enabled', False) and
            config.get('caldav_url', '').strip() != '' and
            config.get('username', '').strip() != '' and
            config.get('password', '').strip() != ''
        )

    def _initialize_client(self) -> bool:
        """Initialize CalDAV client connection"""
        if not self.enabled:
            return False

        try:
            config = self.config

            # Create CalDAV client
            self.client = caldav.DAVClient(
                url=config['caldav_url'],
                username=config['username'],
                password=config['password']
            )

            # Get principal and calendars
            principal = self.client.principal()
            calendars = principal.calendars()

            # Find or create the passport renewals calendar
            calendar_name = config.get('calendar_name', 'Passport Renewals')

            # Look for existing calendar
            self.calendar = None
            for cal in calendars:
                if cal.name == calendar_name:
                    self.calendar = cal
                    break

            # Create calendar if it doesn't exist
            if not self.calendar:
                logger.info(f"Creating CalDAV calendar: {calendar_name}")
                self.calendar = principal.make_calendar(name=calendar_name)

            logger.info("CalDAV client initialized successfully")
            return True

        except Exception as e:
            logger.error(f"CalDAV initialization failed: {e}")
            self.enabled = False
            self.client = None
            self.calendar = None
            return False

    def test_connection(self) -> Tuple[bool, str]:
        """Test CalDAV connection and return (success, message)"""
        if not self.enabled:
            return False, "CalDAV not enabled or configured"

        try:
            # Reinitialize to test current config
            if self._initialize_client():
                # Try to list calendars
                principal = self.client.principal()
                calendars = principal.calendars()
                calendar_count = len(calendars)

                return True, f"Connection successful. Found {calendar_count} calendar(s)."
            else:
                return False, "Failed to initialize CalDAV client"

        except Exception as e:
            logger.error(f"CalDAV connection test failed: {e}")
            return False, f"Connection failed: {str(e)}"

    def discover_caldav_url(self, server_url: str, username: str) -> Optional[str]:
        """
        Auto-discover CalDAV URL from server
        Useful for Nextcloud and other servers
        """
        try:
            # Common CalDAV paths to try
            paths = [
                '/remote.php/dav/calendars/{username}/',  # Nextcloud
                '/caldav/calendars/{username}/',           # Generic
                '/dav/calendars/{username}/',              # Some servers
                '/calendars/{username}/'                   # Simple path
            ]

            for path in paths:
                try:
                    caldav_url = urljoin(server_url, path.format(username=username))

                    # Test the URL
                    test_client = caldav.DAVClient(url=caldav_url)
                    principal = test_client.principal()

                    # If we can get principal, the URL works
                    if principal:
                        logger.info(f"Auto-discovered CalDAV URL: {caldav_url}")
                        return caldav_url

                except Exception:
                    continue

            return None

        except Exception as e:
            logger.error(f"CalDAV auto-discovery failed: {e}")
            return None

    def create_renewal_reminder(self, document: Document, person: Person) -> bool:
        """Create calendar event for document renewal reminder"""
        if not self.enabled or not self.calendar:
            logger.debug("CalDAV not available, skipping calendar event")
            return False

        try:
            # Calculate reminder date (6 months before expiry)
            reminder_date = document.expiry_date - timedelta(days=180)

            # Don't create events for past dates
            if reminder_date < date.today():
                logger.debug(f"Reminder date {reminder_date} is in the past, skipping")
                return False

            # Format document type
            doc_type = document.type.replace('_', ' ').title()

            # Create iCalendar event
            cal = Calendar()
            event = Event()

            # Event details
            event.add('uid', f'passport-renewal-{document.id}-{datetime.now().isoformat()}')
            event.add('dtstart', reminder_date)
            event.add('dtend', reminder_date)
            event.add('summary', f'Renew {person.name}\'s {doc_type}')

            description = f"""Document Renewal Reminder

Holder: {person.name}
Document: {doc_type}
Country: {document.country}
Current Expiry: {document.expiry_date.strftime('%B %d, %Y')}
Document Number: {document.document_number}

This document expires in 6 months. Start the renewal process now to avoid travel restrictions.

Status: {document.status}
"""
            if document.notes:
                description += f"\nNotes: {document.notes}"

            event.add('description', description)
            event.add('location', f'{document.country} - {doc_type} Renewal')

            # Add alarm for 1 week before the reminder date
            from icalendar import Alarm
            alarm = Alarm()
            alarm.add('action', 'DISPLAY')
            alarm.add('description', f'Reminder: Start renewal for {person.name}\'s {doc_type}')
            alarm.add('trigger', timedelta(days=-7))
            event.add_component(alarm)

            cal.add_component(event)

            # Save to CalDAV server
            event_data = cal.to_ical()
            self.calendar.save_event(event_data)

            logger.info(f"Created CalDAV renewal reminder for {person.name}'s {doc_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to create CalDAV event: {e}")
            return False

    def create_expiry_warning(self, document: Document, person: Person, days_remaining: int) -> bool:
        """Create urgent calendar event for documents expiring soon"""
        if not self.enabled or not self.calendar:
            return False

        try:
            # Create event for today (urgent reminder)
            event_date = date.today()

            # Format document type
            doc_type = document.type.replace('_', ' ').title()

            # Create iCalendar event
            cal = Calendar()
            event = Event()

            # Event details
            event.add('uid', f'passport-urgent-{document.id}-{datetime.now().isoformat()}')
            event.add('dtstart', event_date)
            event.add('dtend', event_date)

            if days_remaining > 0:
                event.add('summary', f'🚨 URGENT: {person.name}\'s {doc_type} expires in {days_remaining} days')
            else:
                expired_days = abs(days_remaining)
                event.add('summary', f'🚨 EXPIRED: {person.name}\'s {doc_type} expired {expired_days} days ago')

            description = f"""URGENT Document Expiry Alert

Holder: {person.name}
Document: {doc_type}
Country: {document.country}
Expiry Date: {document.expiry_date.strftime('%B %d, %Y')}
Days Remaining: {days_remaining}

{'IMMEDIATE ACTION REQUIRED' if days_remaining <= 7 else 'URGENT RENEWAL NEEDED'}

Consider expedited processing if travel is planned.
"""

            event.add('description', description)
            event.add('priority', 9)  # High priority

            cal.add_component(event)

            # Save to CalDAV server
            event_data = cal.to_ical()
            self.calendar.save_event(event_data)

            logger.info(f"Created urgent CalDAV alert for {person.name}'s {doc_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to create urgent CalDAV event: {e}")
            return False

    def update_renewal_status(self, document: Document, person: Person) -> bool:
        """Update calendar events when renewal status changes"""
        if not self.enabled or not self.calendar:
            return False

        try:
            # For now, we'll create a status update event
            # In the future, we could find and update existing events

            event_date = date.today()
            doc_type = document.type.replace('_', ' ').title()

            cal = Calendar()
            event = Event()

            event.add('uid', f'passport-status-{document.id}-{datetime.now().isoformat()}')
            event.add('dtstart', event_date)
            event.add('dtend', event_date)

            if document.status == 'application_submitted':
                event.add('summary', f'✅ {person.name}\'s {doc_type} renewal application submitted')
                description = f"""Renewal Application Submitted

Holder: {person.name}
Document: {doc_type}
Country: {document.country}
Submission Date: {document.submission_date.strftime('%B %d, %Y') if document.submission_date else 'Today'}
Processing Estimate: {document.processing_estimate or 'Not specified'}

Application is in progress. Monitor for updates.
"""
            elif document.status == 'received_new':
                event.add('summary', f'🎉 {person.name} received new {doc_type}')
                description = f"""New Document Received

Holder: {person.name}
Document: {doc_type}
Country: {document.country}
New Expiry Date: {document.expiry_date.strftime('%B %d, %Y')}

Remember to update the passport manager with the new document details.
"""
            else:
                return True  # No event needed for 'current' status

            event.add('description', description)
            cal.add_component(event)

            # Save to CalDAV server
            event_data = cal.to_ical()
            self.calendar.save_event(event_data)

            logger.info(f"Created CalDAV status update for {person.name}'s {doc_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to create CalDAV status update: {e}")
            return False

    def get_calendar_info(self) -> Dict[str, Any]:
        """Get information about the connected calendar"""
        if not self.enabled or not self.calendar:
            return {}

        try:
            return {
                'calendar_name': self.calendar.name,
                'calendar_url': str(self.calendar.url),
                'events_count': len(list(self.calendar.events())),
                'connected': True
            }
        except Exception as e:
            logger.error(f"Failed to get calendar info: {e}")
            return {'connected': False, 'error': str(e)}


# Global CalDAV client instance
_caldav_client = None

def get_caldav_client() -> CalDAVClient:
    """Get global CalDAV client instance"""
    global _caldav_client
    if _caldav_client is None:
        _caldav_client = CalDAVClient()
    return _caldav_client

def test_caldav_connection() -> Tuple[bool, str]:
    """Test CalDAV connection - helper function for settings UI"""
    client = get_caldav_client()
    return client.test_connection()

def discover_caldav_url(server_url: str, username: str) -> Optional[str]:
    """Auto-discover CalDAV URL - helper function for settings UI"""
    client = get_caldav_client()
    return client.discover_caldav_url(server_url, username)