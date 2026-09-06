"""Secure email-code password recovery using the existing SQLite database."""

import hashlib
import logging
import re
import secrets
import time
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.auth import COOKIE_NAME, hash_password, verify_password
from app.database.database import get_connection
from app.email_service import (
    email_is_configured,
    send_password_changed_email,
    send_password_reset_code_email,
)

router = APIRouter()
logger = logging.getLogger(__name__)

RESET_MINUTES = 10
MAX_CODE_ATTEMPTS = 5
PAGE = Path(__file__).resolve().parent / "frontend" / "password-reset.html"

GENERIC_MESSAGE = (
    "If an eligible account exists for this email, a 6-digit verification "
    "code will be sent. Check your inbox and spam folder. The code expires "
    "in 10 minutes."
)
INVALID_CODE = "The verification code is invalid or expired. Request a new code."


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class ResetPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


def normalize_email(value):
    email = value.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(400, "Please enter a valid email address.")
    return email


def recovery_connection():
    connection = get_connection()
    try:
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_codes (
                user_id INTEGER PRIMARY KEY,
                code_hash TEXT NOT NULL,
                password_hash_at_issue TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                attempts_remaining INTEGER NOT NULL DEFAULT 5,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_limits (
                identifier TEXT NOT NULL,
                bucket INTEGER NOT NULL,
                requests INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (identifier, bucket)
            )
        """)
        connection.commit()
        return connection
    except Exception:
        connection.close()
        raise


def rate_limit(request, email=None, purpose="forgot"):
    now = int(time.time())
    bucket = now // 3600
    ip = request.client.host if request.client else "unknown"

    if purpose == "forgot":
        keys = [(f"forgot:ip:{ip}", 20)]
        if email is not None:
            email_hash = hashlib.sha256(email.encode("utf-8")).hexdigest()
            keys.append((f"forgot:email:{email_hash}", 5))
            keys.append(("forgot:global", 100))
    else:
        keys = [(f"reset:ip:{ip}", 30)]

    connection = recovery_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "DELETE FROM password_reset_limits WHERE bucket < ?",
            (bucket,),
        )
        connection.execute(
            "DELETE FROM password_reset_codes WHERE expires_at <= ?",
            (now,),
        )

        for key, maximum in keys:
            row = connection.execute(
                """
                SELECT requests
                FROM password_reset_limits
                WHERE identifier = ? AND bucket = ?
                """,
                (key, bucket),
            ).fetchone()
            if row is not None and row["requests"] >= maximum:
                raise HTTPException(
                    429,
                    "Too many requests. Please try again later.",
                    headers={"Retry-After": str(3600 - now % 3600)},
                )

        for key, _ in keys:
            connection.execute("""
                INSERT INTO password_reset_limits (identifier, bucket, requests)
                VALUES (?, ?, 1)
                ON CONFLICT(identifier, bucket)
                DO UPDATE SET requests = requests + 1
            """, (key, bucket))

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def issue_reset_code(email):
    """Background task. Never log the email address, code or email body."""
    user_id = None
    code_hash = None

    try:
        code = f"{secrets.randbelow(1_000_000):06d}"
        code_hash = hash_password(code)

        connection = recovery_connection()
        try:
            connection.execute("BEGIN IMMEDIATE")
            user = connection.execute(
                """
                SELECT id, email, password_hash
                FROM users
                WHERE lower(email) = ?
                """,
                (email,),
            ).fetchone()

            # Legacy /users records without a password cannot claim an account.
            if user is None or not user["password_hash"]:
                connection.rollback()
                return

            user_id = user["id"]
            recipient = user["email"]

            connection.execute("""
                INSERT INTO password_reset_codes (
                    user_id,
                    code_hash,
                    password_hash_at_issue,
                    expires_at,
                    attempts_remaining
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    code_hash = excluded.code_hash,
                    password_hash_at_issue = excluded.password_hash_at_issue,
                    expires_at = excluded.expires_at,
                    attempts_remaining = excluded.attempts_remaining
            """, (
                user_id,
                code_hash,
                user["password_hash"],
                int(time.time()) + RESET_MINUTES * 60,
                MAX_CODE_ATTEMPTS,
            ))
            connection.commit()
        finally:
            connection.close()

        if not send_password_reset_code_email(recipient, code, RESET_MINUTES):
            connection = recovery_connection()
            try:
                connection.execute(
                    "DELETE FROM password_reset_codes WHERE user_id = ? AND code_hash = ?",
                    (user_id, code_hash),
                )
                connection.commit()
            finally:
                connection.close()
            logger.warning("Password reset code was not accepted by the mail service.")

    except Exception as exc:
        logger.error("Password recovery background task failed (%s).", type(exc).__name__)


@router.get("/forgot-password", include_in_schema=False)
@router.get("/reset-password", include_in_schema=False)
def recovery_page():
    return FileResponse(PAGE, headers={
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": (
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        ),
    })


@router.post("/auth/forgot-password", status_code=202)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
):
    response.headers["Cache-Control"] = "no-store"
    email = normalize_email(payload.email)

    if not email_is_configured():
        raise HTTPException(
            503,
            "Password recovery email is not configured. Please contact support.",
        )

    rate_limit(request, email=email, purpose="forgot")

    # Known and unknown addresses receive the same HTTP response.
    background_tasks.add_task(issue_reset_code, email)
    return {"status": "accepted", "message": GENERIC_MESSAGE}


@router.post("/auth/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
):
    response.headers["Cache-Control"] = "no-store"
    email = normalize_email(payload.email)
    code = payload.code.strip()

    if payload.password != payload.confirm_password:
        raise HTTPException(400, "Passwords do not match.")

    rate_limit(request, purpose="reset")

    # Password hashing happens outside the SQLite write lock.
    new_password_hash = hash_password(payload.password)
    connection = recovery_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")
        record = connection.execute("""
            SELECT
                c.user_id,
                c.code_hash,
                c.attempts_remaining,
                u.email
            FROM password_reset_codes AS c
            JOIN users AS u ON u.id = c.user_id
            WHERE lower(u.email) = ?
              AND c.expires_at > ?
              AND c.password_hash_at_issue = u.password_hash
        """, (email, int(time.time()))).fetchone()

        if record is None:
            connection.rollback()
            raise HTTPException(400, INVALID_CODE)

        if not verify_password(code, record["code_hash"]):
            remaining = max(0, record["attempts_remaining"] - 1)

            if remaining == 0:
                connection.execute(
                    "DELETE FROM password_reset_codes WHERE user_id = ?",
                    (record["user_id"],),
                )
            else:
                connection.execute("""
                    UPDATE password_reset_codes
                    SET attempts_remaining = ?
                    WHERE user_id = ?
                """, (remaining, record["user_id"]))

            connection.commit()

            if remaining == 0:
                raise HTTPException(400, INVALID_CODE)
            raise HTTPException(
                400,
                f"Incorrect verification code. {remaining} attempts remaining.",
            )

        connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_password_hash, record["user_id"]),
        )
        connection.execute(
            "DELETE FROM sessions WHERE user_id = ?",
            (record["user_id"],),
        )
        connection.execute(
            "DELETE FROM password_reset_codes WHERE user_id = ?",
            (record["user_id"],),
        )
        recipient = record["email"]
        connection.commit()

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    response.delete_cookie(COOKIE_NAME, path="/")
    background_tasks.add_task(send_password_changed_email, recipient)

    return {
        "status": "success",
        "message": (
            "Password updated. Please sign in with your new password. "
            "All previous sessions have been signed out."
        ),
    }
