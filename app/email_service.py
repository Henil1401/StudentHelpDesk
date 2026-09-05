import json
import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def email_is_configured():
    sender = os.getenv("STUDENT_HELPDESK_EMAIL", "").strip()
    provider = os.getenv("EMAIL_PROVIDER", "smtp").strip().lower()
    if not sender:
        return False
    if provider == "brevo":
        return bool(os.getenv("BREVO_API_KEY", "").strip())
    if provider == "smtp":
        # Render Free blocks SMTP; fail promptly rather than waiting on port 587.
        return os.getenv("RENDER") != "true" and bool(
            os.getenv("STUDENT_HELPDESK_EMAIL_PASSWORD", "").strip()
        )
    return False


def send_email(to_email, subject, message):
    if not email_is_configured():
        print("EMAIL WARNING: Email delivery is not configured for this environment.")
        return False

    sender = os.getenv("STUDENT_HELPDESK_EMAIL", "").strip()
    provider = os.getenv("EMAIL_PROVIDER", "smtp").strip().lower()

    try:
        if provider == "brevo":
            payload = {
                "sender": {"name": "AI Student Help Desk", "email": sender},
                "to": [{"email": to_email}],
                "subject": subject,
                "textContent": message,
                # Do not rewrite password reset links for marketing tracking.
                "headers": {"X-Mailin-Track-Click": "0", "X-Mailin-Track-Open": "0"},
            }
            request = Request(
                "https://api.brevo.com/v3/smtp/email",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "api-key": os.environ["BREVO_API_KEY"].strip(),
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            with urlopen(request, timeout=15) as response:
                result = json.loads(response.read().decode("utf-8"))
                accepted = response.status == 201 and bool(result.get("messageId"))
            if accepted:
                print("EMAIL: Accepted by Brevo for delivery.")
            return accepted

        email = EmailMessage()
        email["From"] = sender
        email["To"] = to_email
        email["Subject"] = subject
        email.set_content(message)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(sender, os.environ["STUDENT_HELPDESK_EMAIL_PASSWORD"])
            refused = server.send_message(email)
        if refused:
            print("EMAIL WARNING: SMTP recipient was refused.")
            return False
        print("EMAIL: Accepted by SMTP server for delivery.")
        return True
    except HTTPError as exc:
        # Never print provider response bodies, API keys, message bodies or reset links.
        print("EMAIL API ERROR: HTTP", exc.code)
        return False
    except Exception as exc:
        print("EMAIL ERROR:", type(exc).__name__)
        return False


def send_ticket_created_email(to_email, ticket_id, question, department):
    subject = f"Student Help Desk - Ticket Created {ticket_id}"
    message = f"""
Hello Student,

Your support ticket has been created successfully.

Ticket ID: {ticket_id}

Problem:
{question}

Department:
{department}

Status:
Open

The concerned department will review your request.

Thank you,
AI Student Help Desk
"""
    return send_email(to_email, subject, message)


def send_ticket_status_email(to_email, ticket_id, status):
    readable_status = status.replace("_", " ").title()
    subject = f"Student Help Desk - Ticket {ticket_id} Updated"
    message = f"""
Hello Student,

Your support ticket status has been updated.

Ticket ID: {ticket_id}

New Status:
{readable_status}

You can check your ticket from the Student Help Desk.

Thank you,
AI Student Help Desk
"""
    return send_email(to_email, subject, message)


def send_faculty_reply_email(to_email, ticket_id, reply, faculty_name):
    sender_name = faculty_name or "Faculty Support Team"
    subject = f"Student Help Desk - Reply for Ticket {ticket_id}"
    message = f"""
Hello Student,

The faculty team has replied to your support ticket.

Ticket ID: {ticket_id}

Reply from {sender_name}:
{reply}

Please login to the Student Help Desk to view the latest ticket status.

Thank you,
AI Student Help Desk
"""
    return send_email(to_email, subject, message)


def send_password_reset_email(to_email, reset_link, expires_minutes=20):
    return send_email(
        to_email,
        "AI Student Help Desk - Reset your password",
        f"""Hello,

We received a request to reset your AI Student Help Desk password.

Open this link to choose a new password:
{reset_link}

This link expires in {expires_minutes} minutes and can only be used once.
Do not share this link. If you did not request this, ignore this email;
your password has not changed.

AI Student Help Desk
""",
    )


def send_password_changed_email(to_email):
    return send_email(
        to_email,
        "AI Student Help Desk - Your password was changed",
        "Your AI Student Help Desk password was changed successfully.\n"
        "All previous login sessions have been signed out.\n"
        "If you did not make this change, contact your help desk administrator immediately.\n"
        "Never send anyone your password or reset link.",
    )
