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

    connection = sqlite3.connect(
        str(DATABASE_PATH)
    )

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# CREATE TABLES
# =========================================================

def create_tables():

    connection = get_connection()

    cursor = connection.cursor()

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            role TEXT DEFAULT 'student',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    # -----------------------------------------------------
    # TICKETS
    # -----------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            ticket_id TEXT UNIQUE NOT NULL,

            question TEXT NOT NULL,

            intent TEXT DEFAULT 'general',

            department TEXT DEFAULT '-',

            status TEXT DEFAULT 'open',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    # -----------------------------------------------------
    # CHATS
    # -----------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            question TEXT NOT NULL,

            answer TEXT NOT NULL,

            intent TEXT DEFAULT 'general',

            agent_type TEXT DEFAULT 'general',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    # -----------------------------------------------------
    # FACULTY
    # -----------------------------------------------------

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

    connection.commit()

    connection.close()


# =========================================================
# INITIALIZE DATABASE
# =========================================================

create_tables()


# =========================================================
# HELPER
# =========================================================

def row_to_dict(row):

    if row is None:
        return None

    return dict(row)


def rows_to_dict(rows):

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# USERS
# =========================================================

def save_user(
    name,
    email,
    role="student"
):

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            """,
            (email,)
        )

        existing = cursor.fetchone()

        if existing:

            return None

        cursor.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                role
            )
            VALUES
            (
                ?,
                ?,
                ?
            )
            """,
            (
                name,
                email,
                role
            )
        )

        connection.commit()

        return cursor.lastrowid

    finally:

        connection.close()


# =========================================================
# GET USERS
# =========================================================

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

        rows = cursor.fetchall()

        return rows_to_dict(rows)

    finally:

        connection.close()


# =========================================================
# GET USER BY EMAIL
# =========================================================

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
            WHERE email = ?
            """,
            (email,)
        )

        row = cursor.fetchone()

        return row_to_dict(row)

    finally:

        connection.close()


# =========================================================
# GET SINGLE USER
# =========================================================

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

        row = cursor.fetchone()

        return row_to_dict(row)

    finally:

        connection.close()


# =========================================================
# SAVE CHAT
# =========================================================

def save_chat(
    question,
    answer,
    intent="general",
    agent_type="general"
):

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO chats
            (
                question,
                answer,
                intent,
                agent_type
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
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


# =========================================================
# GET CHAT HISTORY
# =========================================================

def get_chat_history():

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                question,
                answer,
                intent,
                agent_type,
                created_at
            FROM chats
            ORDER BY id DESC
            """
        )

        rows = cursor.fetchall()

        return rows_to_dict(rows)

    finally:

        connection.close()


# =========================================================
# SAVE TICKET
# =========================================================

def save_ticket(
    question,
    intent="general",
    department="-"
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
                question,
                intent,
                department,
                status
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                ticket_id,
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


# =========================================================
# CREATE TICKET ALIAS
# =========================================================

def create_ticket_record(
    question,
    intent="general",
    department="-"
):

    return save_ticket(
        question=question,
        intent=intent,
        department=department
    )


# =========================================================
# GET ALL TICKETS
# =========================================================

def get_tickets():

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                ticket_id,
                question,
                intent,
                department,
                status,
                created_at,
                updated_at
            FROM tickets
            ORDER BY id DESC
            """
        )

        rows = cursor.fetchall()

        return rows_to_dict(rows)

    finally:

        connection.close()


# =========================================================
# GET SINGLE TICKET
# =========================================================

def get_ticket(ticket_id):

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                ticket_id,
                question,
                intent,
                department,
                status,
                created_at,
                updated_at
            FROM tickets
            WHERE ticket_id = ?
            """,
            (ticket_id,)
        )

        row = cursor.fetchone()

        return row_to_dict(row)

    finally:

        connection.close()


# =========================================================
# UPDATE TICKET STATUS
# =========================================================

def update_ticket_status(
    ticket_id,
    status
):

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
            (
                status,
                ticket_id
            )
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:

        connection.close()


# =========================================================
# FACULTY INFORMATION
# =========================================================

def save_faculty_information(
    category,
    title,
    content
):

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
            VALUES
            (
                ?,
                ?,
                ?
            )
            """,
            (
                category,
                title,
                content
            )
        )

        connection.commit()

        return cursor.lastrowid

    finally:

        connection.close()


# =========================================================
# GET FACULTY INFORMATION
# =========================================================

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

        rows = cursor.fetchall()

        return rows_to_dict(rows)

    finally:

        connection.close()


# =========================================================
# UPDATE FACULTY INFORMATION
# =========================================================

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


# =========================================================
# DELETE FACULTY INFORMATION
# =========================================================

def delete_faculty_information(
    information_id
):

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            DELETE FROM faculty
            WHERE id = ?
            """,
            (information_id,)
        )

        connection.commit()

        return cursor.rowcount > 0

    finally:

        connection.close()


# =========================================================
# GET SINGLE FACULTY INFORMATION
# =========================================================

def get_faculty_information_by_id(
    information_id
):

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

        row = cursor.fetchone()

        return row_to_dict(row)

    finally:

        connection.close()


# =========================================================
# DATABASE TEST
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
            """
        ).fetchall()

        return [
            row["name"]
            for row in tables
        ]

    finally:

        connection.close()