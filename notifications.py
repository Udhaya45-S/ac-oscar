import os

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_FROM_NUMBER = os.environ.get('TWILIO_FROM_NUMBER')

# If Twilio isn't configured, notifications are silently skipped instead of
# crashing the booking flow — a booking should still succeed even if SMS fails.
_twilio_client = None
_twilio_enabled = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER)

if _twilio_enabled:
    try:
        from twilio.rest import Client
        _twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    except ImportError:
        print("WARNING: twilio package not installed but TWILIO_* env vars are set. "
              "Run: pip install twilio")
        _twilio_enabled = False


def send_booking_confirmation_sms(phone, customer_name, tracking_code):
    """
    Sends an SMS to the customer's booking phone number confirming their
    tracking code. Returns True if sent, False if skipped/failed.
    Never raises — a notification failure must not break the booking flow.
    """
    if not _twilio_enabled:
        print(f"[SMS skipped - Twilio not configured] Would notify {phone}: "
              f"tracking code {tracking_code}")
        return False

    to_number = _format_indian_number(phone)
    if not to_number:
        print(f"[SMS skipped - invalid phone] {phone}")
        return False

    message_body = (
        f"Hi {customer_name}, your Oscar Air Care booking is confirmed. "
        f"Tracking code: {tracking_code}. Track status at our website."
    )

    try:
        _twilio_client.messages.create(
            body=message_body,
            from_=TWILIO_FROM_NUMBER,
            to=to_number,
        )
        return True
    except Exception as e:
        print(f"ERROR sending SMS to {to_number}: {e}")
        return False


def send_status_update_sms(phone, tracking_code, new_status):
    """Sends an SMS when an admin updates a booking's status."""
    if not _twilio_enabled:
        print(f"[SMS skipped - Twilio not configured] Would notify {phone}: "
              f"{tracking_code} is now {new_status}")
        return False

    to_number = _format_indian_number(phone)
    if not to_number:
        return False

    message_body = (
        f"Oscar Air Care update: booking {tracking_code} status changed to '{new_status}'."
    )

    try:
        _twilio_client.messages.create(
            body=message_body,
            from_=TWILIO_FROM_NUMBER,
            to=to_number,
        )
        return True
    except Exception as e:
        print(f"ERROR sending SMS to {to_number}: {e}")
        return False


def _format_indian_number(phone):
    """Normalizes a 10-digit Indian phone number to E.164 (+91XXXXXXXXXX)."""
    if not phone:
        return None
    digits = ''.join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith('91'):
        return f"+{digits}"
    if phone.startswith('+'):
        return phone
    return None
