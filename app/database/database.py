import sqlite3
from pathlib import Path
from datetime import datetime
import uuid


# =========================================================
# DATABASE PATH
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_PATH = BASE_DIR / "student_helpdesk.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    connection = sqlite3.connect(str(DATABASE_PATH))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# =========================================================
# DATABASE HELPERS
# =========================================================

def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def rows_to_dict(rows):
    return [dict(row) for row in rows]


def add_column_if_missing(cursor, table_name, column_name, column_definition):
    columns = [
        row["name"]
        for row in cursor.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    ]

    if column_name not in columns:
        cursor.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_definition}"
        )


# =========================================================
# CREATE TABLES
# =========================================================

def create_tables():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                role TEXT DEFAULT 'student',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                user_id INTEGER,
                question TEXT NOT NULL,
                intent TEXT DEFAULT 'general',
                department TEXT DEFAULT '-',
                status TEXT DEFAULT 'open',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                intent TEXT DEFAULT 'general',
                agent_type TEXT DEFAULT 'general',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ticket_replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL,
                faculty_user_id INTEGER,
                reply TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON DELETE CASCADE,
                FOREIGN KEY (faculty_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticket_id TEXT,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS faculty (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Old database ko delete kiye bina new columns add karega.
        add_column_if_missing(
            cursor,
            "users",
            "password_hash",
            "password_hash TEXT"
        )

        add_column_if_missing(
            cursor,
            "tickets",
            "user_id",
            "user_id INTEGER"
        )

        add_column_if_missing(
            cursor,
            "chats",
            "user_id",
            "user_id INTEGER"
        )

        add_column_if_missing(
            cursor,
            "ticket_replies",
            "approval_status",
            "approval_status TEXT DEFAULT 'pending'"
        )

        add_column_if_missing(
            cursor,
            "ticket_replies",
            "approved_by",
            "approved_by INTEGER"
        )

        add_column_if_missing(
            cursor,
            "ticket_replies",
            "approved_at",
            "approved_at TEXT"
        )

        add_column_if_missing(
            cursor,
            "ticket_replies",
            "knowledge_id",
            "knowledge_id INTEGER"
        )

        connection.commit()

    finally:
        connection.close()


# =========================================================
# USERS
# =========================================================

def save_user(
    name,
    email,
    role="student",
    password_hash=None
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        email = email.strip().lower()

        cursor.execute(
            "SELECT id FROM users WHERE lower(email) = lower(?)",
            (email,)
        )

        if cursor.fetchone():
            return None

        cursor.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                password_hash,
                role
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                email,
                password_hash,
                role
            )
        )

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def get_users():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                role,
                created_at
            FROM users
            ORDER BY id DESC
            """
        )

        return rows_to_dict(cursor.fetchall())

    finally:
        connection.close()


def get_user_by_email(email):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                role,
                created_at
            FROM users
            WHERE lower(email) = lower(?)
            """,
            (email.strip(),)
        )

        return row_to_dict(cursor.fetchone())

    finally:
        connection.close()


def get_login_user_by_email(email):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                password_hash,
                role,
                created_at
            FROM users
            WHERE lower(email) = lower(?)
            """,
            (email.strip(),)
        )

        return row_to_dict(cursor.fetchone())

    finally:
        connection.close()


def get_user(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                role,
                created_at
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        )

        return row_to_dict(cursor.fetchone())

    finally:
        connection.close()


def update_user_password(user_id, password_hash):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
            """,
            (password_hash, user_id)
        )

        connection.commit()
        return cursor.rowcount > 0

    finally:
        connection.close()


# =========================================================
# LOGIN SESSIONS
# =========================================================

def save_session(token_hash, user_id, expires_at):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO sessions
            (
                token_hash,
                user_id,
                expires_at
            )
            VALUES (?, ?, ?)
            """,
            (token_hash, user_id, expires_at)
        )

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def get_user_by_session(token_hash, current_time):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                users.id,
                users.name,
                users.email,
                users.role,
                users.created_at
            FROM sessions
            JOIN users
                ON users.id = sessions.user_id
            WHERE sessions.token_hash = ?
              AND sessions.expires_at > ?
            """,
            (token_hash, current_time)
        )

        return row_to_dict(cursor.fetchone())

    finally:
        connection.close()


def delete_session(token_hash):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM sessions WHERE token_hash = ?",
            (token_hash,)
        )

        connection.commit()
        return cursor.rowcount > 0

    finally:
        connection.close()


def delete_expired_sessions(current_time):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM sessions WHERE expires_at <= ?",
            (current_time,)
        )

        connection.commit()
        return cursor.rowcount

    finally:
        connection.close()


# =========================================================
# CHATS
# =========================================================

def save_chat(
    question,
    answer,
    intent="general",
    agent_type="general",
    user_id=None
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO chats
            (
                user_id,
                question,
                answer,
                intent,
                agent_type
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                question,
                answer,
                intent,
                agent_type
            )
        )

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def get_chat_history(user_id=None):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        query = """
            SELECT
                chats.id,
                chats.user_id,
                chats.question,
                chats.answer,
                chats.intent,
                chats.agent_type,
                chats.created_at,
                users.name AS student_name,
                users.email AS student_email
            FROM chats
            LEFT JOIN users
                ON users.id = chats.user_id
        """

        values = ()

        if user_id is not None:
            query += " WHERE chats.user_id = ?"
            values = (user_id,)

        query += " ORDER BY chats.id DESC"

        cursor.execute(query, values)
        return rows_to_dict(cursor.fetchall())

    finally:
        connection.close()


# =========================================================
# TICKETS
# =========================================================

def save_ticket(
    question,
    intent="general",
    department="-",
    user_id=None
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        ticket_id = (
            "TKT-"
            + datetime.now().strftime("%Y%m%d")
            + "-"
            + uuid.uuid4().hex[:6].upper()
        )

        cursor.execute(
            """
            INSERT INTO tickets
            (
                ticket_id,
                user_id,
                question,
                intent,
                department,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                user_id,
                question,
                intent,
                department,
                "open"
            )
        )

        connection.commit()
        return ticket_id

    finally:
        connection.close()


def create_ticket_record(
    question,
    intent="general",
    department="-",
    user_id=None
):
    return save_ticket(
        question=question,
        intent=intent,
        department=department,
        user_id=user_id
    )


def get_tickets(user_id=None):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        query = """
            SELECT
                tickets.id,
                tickets.ticket_id,
                tickets.user_id,
                tickets.question,
                tickets.intent,
                tickets.department,
                tickets.status,
                tickets.created_at,
                tickets.updated_at,
                users.name AS student_name,
                users.email AS student_email,
                (
                    SELECT ticket_replies.reply
                    FROM ticket_replies
                    WHERE ticket_replies.ticket_id = tickets.ticket_id
                    ORDER BY ticket_replies.id DESC
                    LIMIT 1
                ) AS faculty_reply,
                (
                    SELECT ticket_replies.created_at
                    FROM ticket_replies
                    WHERE ticket_replies.ticket_id = tickets.ticket_id
                    ORDER BY ticket_replies.id DESC
                    LIMIT 1
                ) AS reply_created_at,
                (
                    SELECT ticket_replies.id
                    FROM ticket_replies
                    WHERE ticket_replies.ticket_id = tickets.ticket_id
                    ORDER BY ticket_replies.id DESC
                    LIMIT 1
                ) AS faculty_reply_id,
                (
                    SELECT ticket_replies.approval_status
                    FROM ticket_replies
                    WHERE ticket_replies.ticket_id = tickets.ticket_id
                    ORDER BY ticket_replies.id DESC
                    LIMIT 1
                ) AS reply_approval_status,
                (
                    SELECT ticket_replies.approved_at
                    FROM ticket_replies
                    WHERE ticket_replies.ticket_id = tickets.ticket_id
                    ORDER BY ticket_replies.id DESC
                    LIMIT 1
                ) AS reply_approved_at
            FROM tickets
            LEFT JOIN users
                ON users.id = tickets.user_id
        """

        values = ()

        if user_id is not None:
            query += " WHERE tickets.user_id = ?"
            values = (user_id,)

        query += " ORDER BY tickets.id DESC"

        cursor.execute(query, values)
        return rows_to_dict(cursor.fetchall())

    finally:
        connection.close()


def get_ticket(ticket_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                tickets.id,
                tickets.ticket_id,
                tickets.user_id,
                tickets.question,
                tickets.intent,
                tickets.department,
                tickets.status,
                tickets.created_at,
                tickets.updated_at,
                users.name AS student_name,
                users.email AS student_email,
                (
                    SELECT ticket_replies.reply
                    FROM ticket_replies
                    WHERE ticket_replies.ticket_id = tickets.ticket_id
                    ORDER BY ticket_replies.id DESC
                    LIMIT 1
                ) AS faculty_reply,
                (
                    SELECT ticket_replies.created_at
                    FROM ticket_replies
                    WHERE ticket_replies.ticket_id = tickets.ticket_id
                    ORDER BY ticket_replies.id DESC
                    LIMIT 1
                ) AS reply_created_at,
                (
                    SELECT ticket_replies.id
                    FROM ticket_replies
                    WHERE ticket_replies.ticket_id = tickets.ticket_id
                    ORDER BY ticket_replies.id DESC
                    LIMIT 1
                ) AS faculty_reply_id,
                (
                    SELECT ticket_replies.approval_status
                    FROM ticket_replies
                    WHERE ticket_replies.ticket_id = tickets.ticket_id
                    ORDER BY ticket_replies.id DESC
                    LIMIT 1
                ) AS reply_approval_status,
                (
                    SELECT ticket_replies.approved_at
                    FROM ticket_replies
                    WHERE ticket_replies.ticket_id = tickets.ticket_id
                    ORDER BY ticket_replies.id DESC
                    LIMIT 1
                ) AS reply_approved_at
            FROM tickets
            LEFT JOIN users
                ON users.id = tickets.user_id
            WHERE tickets.ticket_id = ?
            """,
            (ticket_id,)
        )

        return row_to_dict(cursor.fetchone())

    finally:
        connection.close()


def assign_ticket_to_user(ticket_id, user_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE tickets
            SET
                user_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE ticket_id = ?
            """,
            (user_id, ticket_id)
        )

        connection.commit()
        return cursor.rowcount > 0

    finally:
        connection.close()


def update_ticket_status(ticket_id, status):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE tickets
            SET
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE ticket_id = ?
            """,
            (status, ticket_id)
        )

        connection.commit()
        return cursor.rowcount > 0

    finally:
        connection.close()


def save_ticket_reply(ticket_id, faculty_user_id, reply):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO ticket_replies
            (
                ticket_id,
                faculty_user_id,
                reply
            )
            VALUES (?, ?, ?)
            """,
            (ticket_id, faculty_user_id, reply)
        )

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def get_ticket_replies(ticket_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                ticket_replies.id,
                ticket_replies.ticket_id,
                ticket_replies.faculty_user_id,
                ticket_replies.reply,
                ticket_replies.created_at,
                ticket_replies.approval_status,
                ticket_replies.approved_by,
                ticket_replies.approved_at,
                ticket_replies.knowledge_id,
                users.name AS faculty_name,
                users.email AS faculty_email
            FROM ticket_replies
            LEFT JOIN users
                ON users.id = ticket_replies.faculty_user_id
            WHERE ticket_replies.ticket_id = ?
            ORDER BY ticket_replies.id DESC
            """,
            (ticket_id,)
        )

        return rows_to_dict(cursor.fetchall())

    finally:
        connection.close()


def approve_latest_ticket_reply(ticket_id, admin_user_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            """
            SELECT
                ticket_replies.id AS reply_id,
                ticket_replies.reply,
                ticket_replies.approval_status,
                ticket_replies.knowledge_id,
                tickets.question,
                tickets.intent,
                tickets.department
            FROM ticket_replies
            INNER JOIN tickets
                ON tickets.ticket_id = ticket_replies.ticket_id
            WHERE ticket_replies.ticket_id = ?
            ORDER BY ticket_replies.id DESC
            LIMIT 1
            """,
            (ticket_id,)
        )

        reply_record = cursor.fetchone()

        if reply_record is None:
            connection.rollback()
            return None

        reply_data = row_to_dict(reply_record)

        if (
            reply_data.get("approval_status") == "approved"
            and reply_data.get("knowledge_id") is not None
        ):
            connection.commit()
            reply_data["already_approved"] = True
            return reply_data

        category = str(
            reply_data.get("intent") or "general"
        ).strip().title()

        cursor.execute(
            """
            INSERT INTO faculty
            (
                category,
                title,
                content
            )
            VALUES (?, ?, ?)
            """,
            (
                category,
                reply_data["question"],
                reply_data["reply"]
            )
        )

        knowledge_id = cursor.lastrowid

        cursor.execute(
            """
            UPDATE ticket_replies
            SET
                approval_status = 'approved',
                approved_by = ?,
                approved_at = CURRENT_TIMESTAMP,
                knowledge_id = ?
            WHERE id = ?
            """,
            (
                admin_user_id,
                knowledge_id,
                reply_data["reply_id"]
            )
        )

        cursor.execute(
            """
            UPDATE tickets
            SET
                status = 'resolved',
                updated_at = CURRENT_TIMESTAMP
            WHERE ticket_id = ?
            """,
            (ticket_id,)
        )

        connection.commit()

        reply_data["approval_status"] = "approved"
        reply_data["knowledge_id"] = knowledge_id
        reply_data["already_approved"] = False

        return reply_data

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_approved_answer(question):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                faculty.content AS answer,
                faculty.id AS knowledge_id,
                tickets.intent,
                tickets.department,
                ticket_replies.ticket_id
            FROM ticket_replies
            INNER JOIN tickets
                ON tickets.ticket_id = ticket_replies.ticket_id
            INNER JOIN faculty
                ON faculty.id = ticket_replies.knowledge_id
            WHERE ticket_replies.approval_status = 'approved'
              AND LOWER(TRIM(tickets.question)) = LOWER(TRIM(?))
            ORDER BY ticket_replies.approved_at DESC
            LIMIT 1
            """,
            (question,)
        )

        return row_to_dict(cursor.fetchone())

    finally:
        connection.close()


def save_notification(user_id, ticket_id, message):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO notifications
            (
                user_id,
                ticket_id,
                message,
                is_read
            )
            VALUES (?, ?, ?, 0)
            """,
            (user_id, ticket_id, message)
        )

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def get_notifications(user_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                user_id,
                ticket_id,
                message,
                is_read,
                created_at
            FROM notifications
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        )

        return rows_to_dict(cursor.fetchall())

    finally:
        connection.close()


# =========================================================
# FACULTY INFORMATION
# =========================================================

def save_faculty_information(category, title, content):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO faculty
            (
                category,
                title,
                content
            )
            VALUES (?, ?, ?)
            """,
            (category, title, content)
        )

        connection.commit()
        return cursor.lastrowid

    finally:
        connection.close()


def get_faculty_information():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                category,
                title,
                content,
                created_at,
                updated_at
            FROM faculty
            ORDER BY id DESC
            """
        )

        return rows_to_dict(cursor.fetchall())

    finally:
        connection.close()


def update_faculty_information(
    information_id,
    category,
    title,
    content
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE faculty
            SET
                category = ?,
                title = ?,
                content = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                category,
                title,
                content,
                information_id
            )
        )

        connection.commit()
        return cursor.rowcount > 0

    finally:
        connection.close()


def delete_faculty_information(information_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM faculty WHERE id = ?",
            (information_id,)
        )

        connection.commit()
        return cursor.rowcount > 0

    finally:
        connection.close()


def get_faculty_information_by_id(information_id):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                category,
                title,
                content,
                created_at,
                updated_at
            FROM faculty
            WHERE id = ?
            """,
            (information_id,)
        )

        return row_to_dict(cursor.fetchone())

    finally:
        connection.close()


# =========================================================
# DATABASE STATUS
# =========================================================

def database_status():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        tables = cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        return [row["name"] for row in tables]

    finally:
        connection.close()


# =========================================================
# INITIALIZE DATABASE
# =========================================================

create_tables()
