import re

from django.conf import settings
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client


class TwilioVerifyError(Exception):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


def is_twilio_configured():
    return bool(
        settings.TWILIO_ACCOUNT_SID
        and settings.TWILIO_AUTH_TOKEN
        and settings.TWILIO_VERIFY_SERVICE_SID
    )


def normalize_indian_mobile(mobile):
    digits = re.sub(r"\D", "", str(mobile).strip())
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) != 10 or not digits.isdigit():
        raise TwilioVerifyError("Enter a valid 10-digit Indian mobile number.")
    if digits[0] not in "6789":
        raise TwilioVerifyError("Enter a valid Indian mobile number.")
    return digits


def to_e164(mobile):
    local = normalize_indian_mobile(mobile)
    return f"+91{local}"


def get_client():
    if not is_twilio_configured():
        raise TwilioVerifyError(
            "SMS verification is not configured. Add Twilio credentials to your .env file."
        )
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_verification_code(mobile):
    phone = to_e164(mobile)
    try:
        client = get_client()
        verification = (
            client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID)
            .verifications.create(to=phone, channel="sms")
        )
        return {
            "phone": phone,
            "status": verification.status,
        }
    except TwilioRestException as exc:
        raise TwilioVerifyError(_friendly_twilio_error(exc), code=exc.code) from exc


def check_verification_code(mobile, code):
    phone = to_e164(mobile)
    otp = str(code).strip()
    if not re.fullmatch(r"\d{4,8}", otp):
        raise TwilioVerifyError("Enter the verification code sent to your phone.")
    try:
        client = get_client()
        result = (
            client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID)
            .verification_checks.create(to=phone, code=otp)
        )
        if result.status != "approved":
            raise TwilioVerifyError("Invalid or expired verification code. Please try again.")
        return result.status
    except TwilioRestException as exc:
        if exc.code == 20404:
            raise TwilioVerifyError("Verification code expired. Request a new code.") from exc
        raise TwilioVerifyError(_friendly_twilio_error(exc), code=exc.code) from exc


def _friendly_twilio_error(exc):
    if exc.code == 60200:
        return "Invalid phone number format."
    if exc.code == 60203:
        return "Too many attempts. Please wait a few minutes and try again."
    if exc.code == 60212:
        return "Too many verification requests. Please try again later."
    return exc.msg or "Unable to send verification code. Please try again."
