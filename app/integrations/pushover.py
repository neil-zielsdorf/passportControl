import requests
import json
import logging
from typing import Optional, Dict, Any
from datetime import date
from app.database.models import get_database, Document, Person
from app.utils.date_utils import get_expiry_status, days_until_expiry

logger = logging.getLogger(__name__)

class PushoverClient:
    """
    Pushover notification client with optional configuration
    Gracefully degrades when not configured or when errors occur
    """

    def __init__(self):
        self.db = get_database()
        self.api_url = "https://api.pushover.net/1/messages.json"
        self.enabled = self._check_configuration()
        self.config = self._get_config()

    def _get_config(self) -> Dict[str, Any]:
        """Get Pushover configuration from database"""
        return self.db.get_setting('pushover', {
            'enabled': False,
            'user_key': '',
            'api_token': '',
            'device': '',
            'sound': 'pushover'
        })

    def _check_configuration(self) -> bool:
        """Check if Pushover is properly configured"""
        config = self._get_config()
        return (
            config.get('enabled', False) and
            config.get('user_key', '').strip() != '' and
            config.get('api_token', '').strip() != ''
        )

    def test_connection(self) -> tuple[bool, str]:
        """Test Pushover connection and return (success, message)"""
        if not self.enabled:
            return False, "Pushover not enabled or configured"

        try:
            response = self._send_notification(
                message="Test notification from Family Passport Manager",
                title="Connection Test",
                priority=0
            )

            if response:
                return True, "Connection successful"
            else:
                return False, "Failed to send test notification"

        except Exception as e:
            logger.error(f"Pushover connection test failed: {e}")
            return False, f"Connection failed: {str(e)}"

    def _send_notification(self, message: str, title: str = None,
                          priority: int = 0, url: str = None,
                          url_title: str = None) -> bool:
        """
        Send notification via Pushover API
        Returns True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug("Pushover not enabled, skipping notification")
            return False

        config = self.config

        payload = {
            'token': config['api_token'],
            'user': config['user_key'],
            'message': message,
            'priority': priority,
            'sound': config.get('sound', 'pushover')
        }

        if title:
            payload['title'] = title

        if config.get('device'):
            payload['device'] = config['device']

        if url:
            payload['url'] = url
            if url_title:
                payload['url_title'] = url_title

        try:
            response = requests.post(self.api_url, data=payload, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 1:
                    logger.info("Pushover notification sent successfully")
                    return True
                else:
                    logger.error(f"Pushover API error: {result.get('errors', 'Unknown error')}")
                    return False
            else:
                logger.error(f"Pushover HTTP error: {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Pushover request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Pushover notification error: {e}")
            return False

    def send_document_expiry_notification(self, document: Document, person: Person,
                                        days_remaining: int) -> bool:
        """Send document expiry notification"""
        if not self.enabled:
            return False

        status_color, status_text = get_expiry_status(document.expiry_date)

        # Determine priority and messaging based on urgency
        if days_remaining <= 7:
            priority = 2  # Emergency - bypasses quiet hours
            urgency = "🚨 CRITICAL"
            action = "Immediate action required"
        elif days_remaining <= 30:
            priority = 1  # High priority
            urgency = "🔴 URGENT"
            action = "Consider expedited processing"
        elif days_remaining <= 90:
            priority = 0  # Normal priority
            urgency = "🟠 ACTION NEEDED"
            action = "Start renewal process now"
        else:
            priority = -1  # Low priority
            urgency = "🟡 PLAN AHEAD"
            action = "Plan for renewal"

        # Format document type for display
        doc_type = document.type.replace('_', ' ').title()

        # Create message
        if days_remaining > 0:
            message = f"{urgency}: {person.name}'s {doc_type} ({document.country}) expires in {days_remaining} days ({document.expiry_date.strftime('%B %d, %Y')}). {action}."
        else:
            expired_days = abs(days_remaining)
            message = f"{urgency}: {person.name}'s {doc_type} ({document.country}) expired {expired_days} days ago. Immediate renewal required."

        title = f"Document Expiry Alert - {person.name}"

        # Add deep link URL (when we have web access)
        url = f"http://localhost:8270"  # TODO: Make this configurable
        url_title = "View Document"

        return self._send_notification(
            message=message,
            title=title,
            priority=priority,
            url=url,
            url_title=url_title
        )

    def send_renewal_reminder(self, document: Document, person: Person) -> bool:
        """Send renewal process reminder"""
        if not self.enabled:
            return False

        doc_type = document.type.replace('_', ' ').title()

        if document.status == "application_submitted":
            message = f"📋 Reminder: {person.name}'s {doc_type} renewal application is in progress."
            if document.processing_estimate:
                message += f" Estimated processing time: {document.processing_estimate}."
            if document.submission_date:
                days_since = (date.today() - document.submission_date).days
                message += f" Application submitted {days_since} days ago."
        else:
            message = f"📋 Reminder: Time to start the renewal process for {person.name}'s {doc_type} ({document.country})."

        title = f"Renewal Reminder - {person.name}"

        return self._send_notification(
            message=message,
            title=title,
            priority=0
        )

    def send_family_summary(self, urgent_count: int, warning_count: int) -> bool:
        """Send daily family document summary"""
        if not self.enabled:
            return False

        if urgent_count == 0 and warning_count == 0:
            message = "✅ All family documents are current. No action needed."
            title = "Daily Document Summary"
            priority = -1
        else:
            message = f"📊 Family Document Summary:\n"
            if urgent_count > 0:
                message += f"🚨 {urgent_count} urgent document(s) need immediate attention\n"
            if warning_count > 0:
                message += f"⚠️ {warning_count} document(s) need renewal planning\n"
            message += "Check the app for details."

            title = "Family Document Alert"
            priority = 1 if urgent_count > 0 else 0

        return self._send_notification(
            message=message,
            title=title,
            priority=priority
        )


# Global Pushover client instance
_pushover_client = None

def get_pushover_client() -> PushoverClient:
    """Get global Pushover client instance"""
    global _pushover_client
    if _pushover_client is None:
        _pushover_client = PushoverClient()
    return _pushover_client

def send_test_notification() -> tuple[bool, str]:
    """Send a test notification - helper function for settings UI"""
    client = get_pushover_client()
    return client.test_connection()