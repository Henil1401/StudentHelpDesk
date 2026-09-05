"""Password recovery using the existing SQLite connection and password hashes."""

import hashlib
import logging
import os
import re
import secrets
import time
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.auth import COOKIE_NAME, hash_password
from app.database.database import get_connection
from app.email_service import (
    email_is_configured,
    send_password_reset_email,
    send_password_changed_email,
)

router = APIRouter()
logger = logging.getLogger(__name__)
RESET_MINUTES = 20
PAGE = Path(__file__).resolve().parent / "frontend" / "password-reset.html"
GENERIC_MESSAGE = (
    "If an eligible account exists for this email, a reset link will be sent. "
    "Check your inbox and spam folder. The link expires in 20 minutes."
)
INVALID_LINK = "This reset link is invalid or expired. Please request a new link."


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


def recovery_connection():
    connection = get_connection()
    try:
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                password_hash_at_issue TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
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


def trusted_base_url():
    value = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    try:
        parts = urlsplit(value)
        local_http = (
            parts.scheme == "http"
            and parts.hostname in {"localhost", "127.0.0.1", "::1"}
            and os.getenv("RENDER") != "true"
        )
        valid = (
            bool(parts.hostname)
            and (parts.scheme == "https" or local_http)
            and not parts.username and not parts.password
            and not parts.query and not parts.fragment
            and parts.path in {"", "/"}
        )
    except ValueError:
        valid = False
    if not valid:
        raise HTTPException(503, "Password recovery is not configured. Please contact support.")
    return value


def rate_limit(request, email=None, purpose="forgot"):
    now = int(time.time())
    bucket = now // 3600
    ip = request.client.host if request.client else "unknown"
    keys = [(f"{purpose}:ip:{ip}", 20 if purpose == "forgot" else 30)]
    if email is not None:
        keys.append(("forgot:email:" + hashlib.sha256(email.encode()).hexdigest(), 5))
        keys.append(("forgot:global", 100))
    connection = recovery_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM password_reset_limits WHERE bucket < ?", (bucket,))
        connection.execute("DELETE FROM password_reset_tokens WHERE expires_at <= ?", (now,))
        for key, maximum in keys:
            row = connection.execute(
                "SELECT requests FROM password_reset_limits WHERE identifier = ? AND bucket = ?",
                (key, bucket),
            ).fetchone()
            if row is not None and row["requests"] >= maximum:
                raise HTTPException(
                    429, "Too many requests. Please try again later.",
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


def issue_reset_link(email, base_url):
    """Called in the background; never log the token or the email body."""
    token_hash = None
    try:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        connection = recovery_connection()
        try:
            connection.execute("BEGIN IMMEDIATE")
            user = connection.execute(
                "SELECT id, email, password_hash FROM users WHERE lower(email) = ?",
                (email,),
            ).fetchone()
            # Legacy /users records without a registered password are not eligible.
            if user is None or not user["password_hash"]:
                connection.rollback()
                return
            connection.execute("""
                INSERT INTO password_reset_tokens
                    (token_hash, user_id, password_hash_at_issue, expires_at)
                VALUES (?, ?, ?, ?)
            """, (token_hash, user["id"], user["password_hash"], int(time.time()) + RESET_MINUTES * 60))
            recipient = user["email"]
            connection.commit()
        finally:
            connection.close()
        # A URL fragment is not sent in HTTP requests or normal access logs.
        link = base_url + "/reset-password#token=" + token
        if not send_password_reset_email(recipient, link, RESET_MINUTES):
            connection = recovery_connection()
            try:
                connection.execute("DELETE FROM password_reset_tokens WHERE token_hash = ?", (token_hash,))
                connection.commit()
            finally:
                connection.close()
            logger.warning("Password reset email was not accepted by the mail service.")
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
        "Content-Security-Policy": "frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    })


@router.post("/auth/forgot-password", status_code=202)
def forgot_password(payload: ForgotPasswordRequest, request: Request,
                    response: Response, background_tasks: BackgroundTasks):
    response.headers["Cache-Control"] = "no-store"
    email = payload.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(400, "Please enter a valid email address.")
    base_url = trusted_base_url()
    if not email_is_configured():
        raise HTTPException(503, "Password recovery email is not configured. Please contact support.")
    rate_limit(request, email=email)
    # Same HTTP message and status; user lookup and email happen after the response.
    background_tasks.add_task(issue_reset_link, email, base_url)
    return {"status": "accepted", "message": GENERIC_MESSAGE}


@router.post("/auth/reset-password")
def reset_password(payload: ResetPasswordRequest, request: Request,
                   response: Response, background_tasks: BackgroundTasks):
    response.headers["Cache-Control"] = "no-store"
    if payload.password != payload.confirm_password:
        raise HTTPException(400, "Passwords do not match.")
    rate_limit(request, purpose="reset")
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    # Hash outside the database write lock. The token is validated under the lock.
    password_hash = hash_password(payload.password)
    connection = recovery_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        record = connection.execute("""
            SELECT t.user_id, u.email
            FROM password_reset_tokens AS t
            JOIN users AS u ON u.id = t.user_id
            WHERE t.token_hash = ? AND t.expires_at > ?
              AND t.password_hash_at_issue = u.password_hash
        """, (token_hash, int(time.time()))).fetchone()
        if record is None:
            raise HTTPException(400, INVALID_LINK)
        connection.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, record["user_id"]))
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (record["user_id"],))
        connection.execute("DELETE FROM password_reset_tokens WHERE user_id = ?", (record["user_id"],))
        recipient = record["email"]
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    response.delete_cookie(COOKIE_NAME, path="/")
    background_tasks.add_task(send_password_changed_email, recipient)
    return {"status": "success", "message": "Password updated. Please sign in with your new password. All previous sessions have been signed out."}
