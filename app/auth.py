import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status

from app.database.database import (
    delete_expired_sessions,
    delete_session,
    get_user_by_session,
    save_session
)


# =========================================================
# AUTH SETTINGS
# =========================================================

COOKIE_NAME = "student_helpdesk_session"
SESSION_HOURS = 8
PASSWORD_ITERATIONS = 260000


# =========================================================
# PASSWORD HASHING
# =========================================================

def hash_password(password):

    salt = secrets.token_bytes(16)

    password_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS
    )

    salt_text = base64.urlsafe_b64encode(
        salt
    ).decode("utf-8")

    digest_text = base64.urlsafe_b64encode(
        password_digest
    ).decode("utf-8")

    return (
        "pbkdf2_sha256"
        + "$"
        + str(PASSWORD_ITERATIONS)
        + "$"
        + salt_text
        + "$"
        + digest_text
    )


def verify_password(password, stored_password_hash):

    if not stored_password_hash:
        return False

    try:

        parts = stored_password_hash.split("$")

        if len(parts) != 4:
            return False

        algorithm = parts[0]
        iterations = int(parts[1])
        salt = base64.urlsafe_b64decode(parts[2])
        expected_digest = base64.urlsafe_b64decode(parts[3])

        if algorithm != "pbkdf2_sha256":
            return False

        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations
        )

        return hmac.compare_digest(
            actual_digest,
            expected_digest
        )

    except Exception:
        return False


# =========================================================
# SESSION TOKEN
# =========================================================

def hash_session_token(token):

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def create_login_session(user_id):

    current_time = datetime.now(
        timezone.utc
    )

    delete_expired_sessions(
        current_time.isoformat()
    )

    token = secrets.token_urlsafe(32)

    token_hash = hash_session_token(
        token
    )

    expires_at = (
        current_time
        + timedelta(hours=SESSION_HOURS)
    ).isoformat()

    save_session(
        token_hash=token_hash,
        user_id=user_id,
        expires_at=expires_at
    )

    return token


def logout_session(token):

    if not token:
        return False

    token_hash = hash_session_token(
        token
    )

    return delete_session(
        token_hash
    )


# =========================================================
# CURRENT LOGGED-IN USER
# =========================================================

def get_current_user(request: Request):

    token = request.cookies.get(
        COOKIE_NAME
    )

    if not token:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please login first."
        )

    token_hash = hash_session_token(
        token
    )

    current_time = datetime.now(
        timezone.utc
    ).isoformat()

    user = get_user_by_session(
        token_hash=token_hash,
        current_time=current_time
    )

    if not user:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please login again."
        )

    return user


# =========================================================
# ROLE PERMISSION
# =========================================================

def require_roles(*allowed_roles):

    allowed_roles = [
        role.lower()
        for role in allowed_roles
    ]

    def role_checker(
        current_user=Depends(get_current_user)
    ):

        user_role = str(
            current_user.get(
                "role",
                "student"
            )
        ).lower()

        if user_role not in allowed_roles:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission for this action."
            )

        return current_user

    return role_checker
