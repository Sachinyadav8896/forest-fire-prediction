"""
alert_service.py
Fires alerts when a prediction's probability crosses MODEL.alert_probability_threshold.
Email is sent via SMTP (configured through environment variables). Browser
notifications aren't "sent" server-side — this returns a payload the
frontend polls/subscribes to and renders as a native Notification.
"""

from __future__ import annotations

import os
import smtplib
import sys
from email.mime.text import MIMEText
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import MODEL
from backend.utils.logger import get_logger
from backend.utils import db

logger = get_logger(__name__)

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ALERT_FROM_EMAIL = os.environ.get("ALERT_FROM_EMAIL", SMTP_USER)


def should_alert(probability: float) -> bool:
    return probability >= MODEL.alert_probability_threshold


def send_email_alert(recipient: str, city_name: str, probability: float, risk_level: str) -> bool:
    if not (SMTP_HOST and SMTP_USER and SMTP_PASSWORD):
        logger.warning("SMTP not configured; email alert skipped.")
        return False

    subject = f"\U0001F525 FIRE RISK ALERT: {risk_level} ({probability*100:.1f}%) near {city_name}"
    body = (
        f"A wildfire risk prediction for {city_name} has reached {risk_level} risk "
        f"with a {probability*100:.1f}% probability, exceeding the alert threshold "
        f"of {MODEL.alert_probability_threshold*100:.0f}%.\n\n"
        f"Please check the dashboard for the full explanation and recommended actions."
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = ALERT_FROM_EMAIL
    msg["To"] = recipient

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(ALERT_FROM_EMAIL, [recipient], msg.as_string())
        logger.info(f"Email alert sent to {recipient} for {city_name} ({risk_level}).")
        return True
    except Exception as e:
        logger.error(f"Failed to send email alert to {recipient}: {e}")
        return False


def dispatch_alerts(prediction_id: int, city_name: str, probability: float,
                     risk_level: str, email_recipient: Optional[str] = None) -> dict:
    """
    Called right after a prediction is persisted. Creates alert rows and
    attempts delivery. Always creates a 'browser' alert row (delivered via
    the frontend polling /api/alerts/recent), and an 'email' row if a
    recipient was provided.
    Returns a summary dict for the API response.
    """
    result = {"alerted": False, "channels": []}

    if not should_alert(probability):
        return result

    result["alerted"] = True

    browser_alert_id = db.insert_alert(prediction_id, "browser", recipient=None, status="sent")
    db.mark_alert_sent(browser_alert_id)
    result["channels"].append("browser")

    if email_recipient:
        email_alert_id = db.insert_alert(prediction_id, "email", email_recipient, status="pending")
        sent = send_email_alert(email_recipient, city_name, probability, risk_level)
        if sent:
            db.mark_alert_sent(email_alert_id)
            result["channels"].append("email")

    logger.info(f"Alert dispatched for prediction {prediction_id}: channels={result['channels']}")
    return result
