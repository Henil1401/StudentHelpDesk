import os
import smtplib
from email.message import EmailMessage


SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_ADDRESS = os.getenv("STUDENT_HELPDESK_EMAIL")
EMAIL_PASSWORD = os.getenv("STUDENT_HELPDESK_EMAIL_PASSWORD")


def send_email(to_email: str, subject: str, message: str):

    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("EMAIL WARNING: Email credentials are not configured.")
        return False

    try:
        email = EmailMessage()

        email["From"] = EMAIL_ADDRESS
        email["To"] = to_email
        email["Subject"] = subject

        email.set_content(message)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()

            server.login(
                EMAIL_ADDRESS,
                EMAIL_PASSWORD
            )

            server.send_message(email)

        print("EMAIL SENT TO:", to_email)

        return True

    except Exception as e:

        print("EMAIL ERROR:", e)

        return False


def send_ticket_created_email(
    to_email: str,
    ticket_id: str,
    question: str,
    department: str
):

    subject = f"Student Help Desk - Ticket {ticket_id} Created"

    message = f"""
Hello,

Your support ticket has been created successfully.

Ticket ID: {ticket_id}

Question / Issue:
{question}

Department:
{department}

Status:
Open

The concerned department will review your issue.

Regards,
AI Student Help Desk
"""

    return send_email(
        to_email,
        subject,
        message
    )


def send_ticket_status_email(
    to_email: str,
    ticket_id: str,
    status: str
):

    readable_status = status.replace(
        "_",
        " "
    ).title()

    subject = f"Student Help Desk - Ticket {ticket_id} Updated"

    message = f"""
Hello,

Your support ticket status has been updated.

Ticket ID:
{ticket_id}

New Status:
{readable_status}

You can check the Student Help Desk for more information.

Regards,
AI Student Help Desk
"""

    return send_email(
        to_email,
        subject,
        message
    )