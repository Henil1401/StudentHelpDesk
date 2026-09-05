import hmac
import os
import re
from pathlib import Path

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
    status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.rag import search_knowledge
from app.agent import run_agent

from app.database.database import (
    get_tickets,
    get_ticket,
    assign_ticket_to_user,
    update_ticket_status,
    save_ticket_reply,
    get_ticket_replies,
    approve_latest_ticket_reply,
    get_approved_answer,
    save_notification,
    get_notifications,
    save_chat,
    get_chat_history,
    get_users,
    save_user,
    get_user_by_email,
    get_login_user_by_email,
    save_faculty_information,
    get_faculty_information,
    update_faculty_information,
    delete_faculty_information
)

from app.agents.ticket_agent import create_ticket
from app.agents.faculty_agent import route_to_faculty

from app.email_service import (
    send_ticket_created_email,
    send_ticket_status_email,
    send_faculty_reply_email
)

from app.password_reset import router as password_reset_router

from app.auth import (
    COOKIE_NAME,
    SESSION_HOURS,
    create_login_session,
    get_current_user,
    hash_password,
    logout_session,
    require_roles,
    verify_password
)


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="AI Student Help Desk",
    description="Cloud-Based AI Student Help Desk using RAG and Multi-Agent System",
    version="1.2.0"
)


app.include_router(password_reset_router)

# =========================================================
# FRONTEND FILES
# =========================================================

APP_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = APP_DIR / "frontend"


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# =========================================================
# MEMORY
# =========================================================

previous_question = ""


# =========================================================
# REQUEST MODELS
# =========================================================

class QuestionRequest(BaseModel):
    question: str


class TicketRequest(BaseModel):
    question: str
    intent: str = "general"


class TicketStatusRequest(BaseModel):
    status: str


class TicketReplyRequest(BaseModel):
    reply: str


class FacultyInformationRequest(BaseModel):
    category: str
    title: str
    content: str


class UserRequest(BaseModel):
    name: str
    email: str
    role: str = "student"


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "student"
    access_code: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


# =========================================================
# GET STUDENT EMAIL
# =========================================================

def get_student_notification_email():

    try:

        users = get_users()

        for user in users:

            role = str(
                user.get("role", "student")
            ).lower()

            email = str(
                user.get("email", "")
            ).strip()

            if role == "student" and email:
                return email

    except Exception as e:

        print(
            "EMAIL USER LOOKUP ERROR:",
            e
        )

    return None


# =========================================================
# FRONTEND PAGES
# =========================================================

@app.get(
    "/",
    include_in_schema=False
)
def home():

    return FileResponse(
        FRONTEND_DIR / "index.html"
    )


@app.get(
    "/register",
    include_in_schema=False
)
def register_page():

    return FileResponse(
        FRONTEND_DIR / "register.html"
    )


@app.get(
    "/student-dashboard",
    include_in_schema=False
)
def student_dashboard(
    current_user=Depends(
        require_roles("student")
    )
):

    return FileResponse(
        FRONTEND_DIR / "student.html"
    )


@app.get(
    "/faculty-dashboard",
    include_in_schema=False
)
def faculty_dashboard(
    current_user=Depends(
        require_roles("faculty")
    )
):

    return FileResponse(
        FRONTEND_DIR / "faculty.html"
    )


@app.get(
    "/admin-dashboard",
    include_in_schema=False
)
def admin_dashboard(
    current_user=Depends(
        require_roles("admin")
    )
):

    return FileResponse(
        FRONTEND_DIR / "admin.html"
    )


@app.get(
    "/style.css",
    include_in_schema=False
)
def frontend_styles():

    return FileResponse(
        FRONTEND_DIR / "style.css",
        media_type="text/css"
    )


@app.get(
    "/script.js",
    include_in_schema=False
)
def frontend_script():

    return FileResponse(
        FRONTEND_DIR / "script.js",
        media_type="application/javascript"
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health_check():

    return {
        "message": "AI Student Help Desk is running",
        "status": "online"
    }


# =========================================================
# ASK QUESTION
# =========================================================

@app.post("/ask")
def ask_question(
    request: QuestionRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(
        require_roles("student")
    )
):

    global previous_question

    question = request.question.strip()

    if not question:

        return {
            "question": "",
            "answer": "Please enter a question.",
            "confidence": 0.0,
            "status": "not_found",
            "source": "system",
            "type": "general",
            "intent": "general",
            "department": "-",
            "ticket_id": None
        }

    try:

        q = question.lower().strip()


        # =================================================
        # ADMIN-APPROVED FACULTY KNOWLEDGE
        # =================================================

        approved_knowledge = get_approved_answer(
            question
        )


        if approved_knowledge:

            answer = approved_knowledge["answer"]

            try:

                save_chat(
                    question=question,
                    answer=answer,
                    intent=approved_knowledge.get(
                        "intent",
                        "general"
                    ),
                    agent_type="approved_faculty_knowledge",
                    user_id=current_user["id"]
                )

            except Exception as history_error:

                print(
                    "CHAT HISTORY ERROR:",
                    history_error
                )


            previous_question = question


            return {
                "question": question,
                "answer": answer,
                "confidence": 1.0,
                "status": "answered",
                "source": "approved_faculty_knowledge",
                "type": "approved_faculty_knowledge",
                "intent": approved_knowledge.get(
                    "intent",
                    "general"
                ),
                "department": approved_knowledge.get(
                    "department",
                    "-"
                ),
                "ticket_id": None,
                "knowledge_id": approved_knowledge.get(
                    "knowledge_id"
                )
            }


        # =================================================
        # PROBLEM WORDS
        # =================================================

        problem_words = [
            "problem",
            "issue",
            "complaint",
            "complain",
            "wrong",
            "incorrect",
            "error",
            "mistake",
            "not correct",
            "not showing",
            "missing",
            "unable",
            "cannot",
            "can't",
            "confusion",
            "confused",
            "mismatch",
            "not working",
            "does not work",
            "doesn't work",
            "not submitting",
            "cannot submit",
            "can't submit",
            "not opening",
            "not loading",
            "not updating",
            "not uploading",
            "failed",
            "stuck",
            "having trouble",
            "facing problem",
            "facing issue"
        ]


        exam_words = [
            "exam",
            "examination",
            "exam timetable",
            "examination timetable",
            "exam schedule",
            "examination schedule",
            "timetable",
            "time table"
        ]


        has_problem_word = any(
            word in q
            for word in problem_words
        )


        has_exam_word = any(
            word in q
            for word in exam_words
        )


        # =================================================
        # STUDENT PROBLEM -> CREATE TICKET
        # =================================================

        if has_problem_word:

            ticket_intent = (
                "exam"
                if has_exam_word
                else "general"
            )

            department = route_to_faculty(
                ticket_intent
            )


            ticket = create_ticket(
                question=question,
                intent=ticket_intent,
                department=department,
                user_id=current_user["id"]
            )


            ticket_id = None


            if isinstance(ticket, dict):

                ticket_id = ticket.get(
                    "ticket_id"
                )

            elif ticket:

                ticket_id = str(ticket)


            if has_exam_word:

                answer = (
                    "Your exam timetable issue has been registered "
                    "successfully. The Examination Department will "
                    "review your ticket."
                )

            else:

                answer = (
                    "Your issue has been registered automatically. "
                    "The concerned department will review your ticket."
                )


            # =================================================
            # SAVE CHAT
            # =================================================

            try:

                save_chat(
                    question=question,
                    answer=answer,
                    intent=ticket_intent,
                    agent_type="ticket_agent",
                    user_id=current_user["id"]
                )

            except Exception as history_error:

                print(
                    "CHAT HISTORY ERROR:",
                    history_error
                )


            # =================================================
            # EMAIL IN BACKGROUND
            # =================================================

            student_email = str(
                current_user.get(
                    "email",
                    ""
                )
            ).strip()


            email_sent = False


            if (
                student_email
                and ticket_id
            ):

                background_tasks.add_task(
                    send_ticket_created_email,
                    to_email=student_email,
                    ticket_id=ticket_id,
                    question=question,
                    department=department
                )

                email_sent = True


            previous_question = ""


            return {
                "question": question,
                "answer": answer,
                "confidence": 1.0,
                "status": "ticket_created",
                "source": "ticket_system",
                "type": "ticket_agent",
                "intent": ticket_intent,
                "department": department,
                "ticket_id": ticket_id,
                "email_sent": email_sent
            }


        # =================================================
        # FOLLOW-UP
        # =================================================

        search_question = question


        follow_up_words = [
            "what time",
            "what is the time",
            "what is the venue",
            "venue",
            "where",
            "which room",
            "room",
            "when is it",
            "when is it?"
        ]


        if (
            previous_question
            and any(
                word in q
                for word in follow_up_words
            )
        ):

            search_question = (
                previous_question
                + " "
                + question
            )


        # =================================================
        # RAG SEARCH
        # =================================================

        results = search_knowledge(
            search_question,
            top_k=1
        )


        # =================================================
        # MULTI AGENT
        # =================================================

        result = run_agent(
            question,
            results,
            previous_question
        )


        # =================================================
        # RESULT
        # =================================================

        answer = result.get(
            "answer",
            "Sorry, this information is not available in the university knowledge base."
        )


        status = result.get(
            "status",
            "not_found"
        )


        source = result.get(
            "source",
            "university_knowledge"
        )


        agent_type = result.get(
            "type",
            "general"
        )


        intent = result.get(
            "intent",
            "general"
        )


        department = result.get(
            "faculty",
            result.get(
                "department",
                "-"
            )
        )


        ticket_id = result.get(
            "ticket_id"
        )


        email_sent = False


        should_create_ticket = (
            not ticket_id
            and (
                has_problem_word
                or status in [
                    "not_found",
                    "error"
                ]
            )
        )


        if should_create_ticket:

            ticket_intent = str(
                intent or "general"
            ).strip().lower()


            if ticket_intent in [
                "",
                "unknown",
                "none"
            ]:

                ticket_intent = "general"


            if has_exam_word:
                ticket_intent = "exam"


            department = route_to_faculty(
                ticket_intent
            )


            automatic_ticket = create_ticket(
                question=question,
                intent=ticket_intent,
                department=department,
                user_id=current_user["id"]
            )


            if isinstance(
                automatic_ticket,
                dict
            ):

                ticket_id = automatic_ticket.get(
                    "ticket_id"
                )

            elif automatic_ticket:

                ticket_id = str(
                    automatic_ticket
                )


            if ticket_id:

                answer = (
                    "AI could not find a confirmed answer, so your "
                    "support ticket has been created automatically. "
                    "The concerned department will review it."
                )

                status = "ticket_created"
                source = "ticket_system"
                agent_type = "ticket_agent"
                intent = ticket_intent


        if ticket_id:

            assign_ticket_to_user(
                ticket_id,
                current_user["id"]
            )


            student_email = str(
                current_user.get(
                    "email",
                    ""
                )
            ).strip()


            if student_email:

                background_tasks.add_task(
                    send_ticket_created_email,
                    to_email=student_email,
                    ticket_id=ticket_id,
                    question=question,
                    department=department
                )

                email_sent = True


        if status == "found":

            confidence = 0.9

        elif status == "ticket_created":

            confidence = 1.0

        else:

            confidence = 0.0


        # =================================================
        # SAVE CHAT
        # =================================================

        try:

            save_chat(
                question=question,
                answer=answer,
                intent=intent,
                agent_type=agent_type,
                user_id=current_user["id"]
            )

        except Exception as history_error:

            print(
                "CHAT HISTORY ERROR:",
                history_error
            )


        previous_question = question


        return {
            "question": question,
            "answer": answer,
            "confidence": confidence,
            "status": status,
            "source": source,
            "type": agent_type,
            "intent": intent,
            "department": department,
            "ticket_id": ticket_id,
            "email_sent": email_sent
        }


    except Exception as e:

        print(
            "ASK ERROR:",
            e
        )

        return {
            "question": question,
            "answer": "Sorry, something went wrong while processing your question.",
            "confidence": 0.0,
            "status": "error",
            "source": "system",
            "type": "error",
            "intent": "general",
            "department": "-",
            "ticket_id": None
        }


# =========================================================
# CHAT HISTORY
# =========================================================

@app.get("/history")
@app.get("/chat-history")
def chat_history(
    current_user=Depends(
        get_current_user
    )
):

    try:

        current_role = str(
            current_user.get(
                "role",
                ""
            )
        ).strip().lower()


        history_user_id = (
            current_user["id"]
            if current_role == "student"
            else None
        )


        history = get_chat_history(
            user_id=history_user_id
        )

        return {
            "status": "success",
            "history": history
        }

    except Exception as e:

        print(
            "CHAT HISTORY ERROR:",
            e
        )

        return {
            "status": "error",
            "history": [],
            "message": str(e)
        }


# =========================================================
# USERS
# =========================================================

@app.get("/users")
def get_all_students(
    current_user=Depends(require_roles("admin"))
):

    try:

        users = get_users()

        students = [
            user
            for user in users
            if str(
                user.get(
                    "role",
                    "student"
                )
            ).lower() == "student"
        ]

        return {
            "status": "success",
            "users": students
        }

    except Exception as e:

        print(
            "GET STUDENTS ERROR:",
            e
        )

        return {
            "status": "error",
            "users": [],
            "message": str(e)
        }


# =========================================================
# CREATE USER
# =========================================================

@app.post("/users")
def create_user(
    request: UserRequest,
    current_user=Depends(require_roles("admin"))
):

    try:

        name = request.name.strip()
        email = request.email.strip().lower()
        role = request.role.strip().lower()


        if not name:

            return {
                "status": "error",
                "message": "Name is required."
            }


        if not email:

            return {
                "status": "error",
                "message": "Email is required."
            }


        existing_user = get_user_by_email(
            email
        )


        if existing_user:

            return {
                "status": "error",
                "message": "User with this email already exists.",
                "user": existing_user
            }


        user_id = save_user(
            name=name,
            email=email,
            role=role
        )


        return {
            "status": "success",
            "message": "User created successfully.",
            "user_id": user_id
        }


    except Exception as e:

        print(
            "CREATE USER ERROR:",
            e
        )

        return {
            "status": "error",
            "message": str(e)
        }


# =========================================================
# GET SINGLE USER
# =========================================================

@app.get("/users/{user_id}")
def get_single_user(
    user_id: int,
    current_user=Depends(require_roles("admin"))
):

    try:

        from app.database.database import (
            get_connection
        )


        connection = get_connection()

        cursor = connection.cursor()


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


        user = cursor.fetchone()

        connection.close()


        if not user:

            return {
                "status": "error",
                "message": "User not found."
            }


        return {
            "status": "success",
            "user": dict(user)
        }


    except Exception as e:

        print(
            "GET USER ERROR:",
            e
        )

        return {
            "status": "error",
            "message": str(e)
        }


# =========================================================
# CREATE TICKET
# =========================================================

@app.post("/create-ticket")
def manual_create_ticket(
    request: TicketRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(
        require_roles("student")
    )
):

    try:

        question = request.question.strip()

        intent = (
            request.intent
            .strip()
            .lower()
        )


        if not question:

            return {
                "status": "error",
                "message": "Question is required."
            }


        department = route_to_faculty(
            intent
        )


        ticket = create_ticket(
            question=question,
            intent=intent,
            department=department,
            user_id=current_user["id"]
        )


        ticket_id = None


        if isinstance(ticket, dict):

            ticket_id = ticket.get(
                "ticket_id"
            )

        elif ticket:

            ticket_id = str(ticket)


        student_email = str(
            current_user.get(
                "email",
                ""
            )
        ).strip()


        email_sent = False


        if (
            student_email
            and ticket_id
        ):

            background_tasks.add_task(
                send_ticket_created_email,
                to_email=student_email,
                ticket_id=ticket_id,
                question=question,
                department=department
            )

            email_sent = True


        return {
            "status": "success",
            "message": "Ticket created successfully.",
            "ticket": ticket,
            "email_sent": email_sent
        }


    except Exception as e:

        print(
            "TICKET ERROR:",
            e
        )

        return {
            "status": "error",
            "message": str(e)
        }


# =========================================================
# GET TICKETS
# =========================================================

@app.get("/tickets")
def get_all_tickets(
    current_user=Depends(
        get_current_user
    )
):

    try:

        current_role = str(
            current_user.get(
                "role",
                ""
            )
        ).strip().lower()


        ticket_user_id = (
            current_user["id"]
            if current_role == "student"
            else None
        )


        tickets = get_tickets(
            user_id=ticket_user_id
        )

        return {
            "status": "success",
            "tickets": tickets
        }

    except Exception as e:

        print(
            "GET TICKETS ERROR:",
            e
        )

        return {
            "status": "error",
            "tickets": [],
            "message": str(e)
        }


# =========================================================
# SINGLE TICKET
# =========================================================

@app.get("/tickets/{ticket_id}")
def get_single_ticket(
    ticket_id: str,
    current_user=Depends(
        get_current_user
    )
):

    try:

        ticket = get_ticket(
            ticket_id.strip()
        )


        if not ticket:

            return {
                "status": "error",
                "message": "Ticket not found."
            }


        current_role = str(
            current_user.get(
                "role",
                ""
            )
        ).strip().lower()


        if (
            current_role == "student"
            and str(ticket.get("user_id"))
            != str(current_user["id"])
        ):

            raise HTTPException(
                status_code=403,
                detail="You can only view your own tickets."
            )


        return {
            "status": "success",
            "ticket": ticket
        }


    except HTTPException:

        raise


    except Exception as e:

        print(
            "GET SINGLE TICKET ERROR:",
            e
        )

        return {
            "status": "error",
            "message": str(e)
        }


# =========================================================
# UPDATE TICKET STATUS
# =========================================================

@app.patch("/tickets/{ticket_id}")
def update_ticket(
    ticket_id: str,
    request: TicketStatusRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(
        get_current_user
    )
):

    current_role = str(
        current_user.get(
            "role",
            ""
        )
    ).strip().lower()


    if current_role not in [
        "faculty",
        "admin"
    ]:

        raise HTTPException(
            status_code=403,
            detail="Only faculty or admin can update ticket status."
        )


    try:

        ticket_id = ticket_id.strip()

        status = (
            request.status
            .lower()
            .strip()
        )


        allowed_statuses = [
            "open",
            "in_progress",
            "resolved"
        ]


        if status not in allowed_statuses:

            return {
                "status": "error",
                "message": "Invalid ticket status. Use: open, in_progress, resolved"
            }


        updated = update_ticket_status(
            ticket_id,
            status
        )


        if not updated:

            return {
                "status": "error",
                "message": "Ticket not found.",
                "ticket_id": ticket_id
            }


        updated_ticket = get_ticket(
            ticket_id
        )


        student_email = str(
            (
                updated_ticket or {}
            ).get(
                "student_email",
                ""
            )
        ).strip()


        email_sent = False


        if student_email:

            background_tasks.add_task(
                send_ticket_status_email,
                to_email=student_email,
                ticket_id=ticket_id,
                status=status
            )

            email_sent = True


        return {
            "status": "success",
            "message": "Ticket status updated successfully.",
            "ticket_id": ticket_id,
            "ticket_status": status,
            "email_sent": email_sent
        }


    except Exception as e:

        print(
            "STATUS UPDATE ERROR:",
            e
        )

        return {
            "status": "error",
            "message": str(e)
        }


# =========================================================
# FACULTY REPLY TO TICKET
# =========================================================

@app.post("/tickets/{ticket_id}/reply")
def reply_to_ticket(
    ticket_id: str,
    request: TicketReplyRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(
        get_current_user
    )
):

    current_role = str(
        current_user.get(
            "role",
            ""
        )
    ).strip().lower()


    if current_role not in [
        "faculty",
        "admin"
    ]:

        raise HTTPException(
            status_code=403,
            detail="Only faculty or admin can reply to tickets."
        )


    ticket_id = ticket_id.strip()
    reply = request.reply.strip()


    if not reply:

        raise HTTPException(
            status_code=400,
            detail="Reply cannot be empty."
        )


    try:

        ticket = get_ticket(
            ticket_id
        )


        if not ticket:

            raise HTTPException(
                status_code=404,
                detail="Ticket not found."
            )


        reply_id = save_ticket_reply(
            ticket_id=ticket_id,
            faculty_user_id=current_user["id"],
            reply=reply
        )


        ticket_status = str(
            ticket.get(
                "status",
                "open"
            )
        ).strip().lower()


        if ticket_status == "open":

            update_ticket_status(
                ticket_id,
                "in_progress"
            )

            ticket_status = "in_progress"


        student_user_id = ticket.get(
            "user_id"
        )


        if student_user_id is not None:

            save_notification(
                user_id=student_user_id,
                ticket_id=ticket_id,
                message=(
                    "A faculty reply was added to ticket "
                    + ticket_id
                    + "."
                )
            )


        student_email = str(
            ticket.get(
                "student_email",
                ""
            )
        ).strip()


        email_sent = False


        if student_email:

            background_tasks.add_task(
                send_faculty_reply_email,
                to_email=student_email,
                ticket_id=ticket_id,
                reply=reply,
                faculty_name=current_user.get(
                    "name",
                    "Faculty Support Team"
                )
            )

            email_sent = True


        return {
            "status": "success",
            "message": "Reply sent to student successfully.",
            "reply_id": reply_id,
            "ticket_id": ticket_id,
            "ticket_status": ticket_status,
            "email_sent": email_sent
        }


    except HTTPException:

        raise


    except Exception as e:

        print(
            "TICKET REPLY ERROR:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to send faculty reply."
        )


# =========================================================
# GET TICKET REPLIES
# =========================================================

@app.get("/tickets/{ticket_id}/replies")
def get_replies_for_ticket(
    ticket_id: str,
    current_user=Depends(
        get_current_user
    )
):

    ticket = get_ticket(
        ticket_id.strip()
    )


    if not ticket:

        raise HTTPException(
            status_code=404,
            detail="Ticket not found."
        )


    current_role = str(
        current_user.get(
            "role",
            ""
        )
    ).strip().lower()


    if (
        current_role == "student"
        and str(ticket.get("user_id"))
        != str(current_user["id"])
    ):

        raise HTTPException(
            status_code=403,
            detail="You can only view replies for your own tickets."
        )


    return {
        "status": "success",
        "replies": get_ticket_replies(
            ticket_id.strip()
        )
    }


# =========================================================
# ADMIN APPROVE FACULTY REPLY
# =========================================================

@app.post("/tickets/{ticket_id}/approve-reply")
def approve_ticket_reply(
    ticket_id: str,
    current_user=Depends(
        require_roles("admin")
    )
):

    ticket_id = ticket_id.strip()


    if not ticket_id:

        raise HTTPException(
            status_code=400,
            detail="Ticket ID is required."
        )


    try:

        approval = approve_latest_ticket_reply(
            ticket_id=ticket_id,
            admin_user_id=current_user["id"]
        )


        if not approval:

            raise HTTPException(
                status_code=404,
                detail="No faculty reply is available for approval."
            )


        already_approved = bool(
            approval.get("already_approved")
        )


        return {
            "status": "success",
            "message": (
                "Faculty reply was already approved."
                if already_approved
                else "Faculty reply approved and added to the knowledge base."
            ),
            "ticket_id": ticket_id,
            "reply_id": approval.get("reply_id"),
            "knowledge_id": approval.get("knowledge_id"),
            "already_approved": already_approved,
            "ticket_status": "resolved"
        }


    except HTTPException:

        raise


    except Exception as e:

        print(
            "REPLY APPROVAL ERROR:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to approve the faculty reply."
        )


# =========================================================
# USER NOTIFICATIONS
# =========================================================

@app.get("/notifications")
def get_current_notifications(
    current_user=Depends(
        get_current_user
    )
):

    return {
        "status": "success",
        "notifications": get_notifications(
            current_user["id"]
        )
    }


# =========================================================
# FACULTY ADD
# =========================================================

@app.post("/faculty-information")
def add_faculty_information(
    request: FacultyInformationRequest
):

    try:

        category = request.category.strip()
        title = request.title.strip()
        content = request.content.strip()


        if not category:

            return {
                "status": "error",
                "message": "Category is required."
            }


        if not title:

            return {
                "status": "error",
                "message": "Title is required."
            }


        if not content:

            return {
                "status": "error",
                "message": "Information is required."
            }


        information_id = (
            save_faculty_information(
                category=category,
                title=title,
                content=content
            )
        )


        return {
            "status": "success",
            "message": "Faculty information saved successfully.",
            "information_id": information_id
        }


    except Exception as e:

        print(
            "FACULTY INFORMATION ERROR:",
            e
        )

        return {
            "status": "error",
            "message": str(e)
        }


# =========================================================
# GET FACULTY
# =========================================================

@app.get("/faculty-information")
def get_all_faculty_information():

    try:

        information = (
            get_faculty_information()
        )


        return {
            "status": "success",
            "information": information
        }


    except Exception as e:

        print(
            "GET FACULTY INFORMATION ERROR:",
            e
        )

        return {
            "status": "error",
            "information": [],
            "message": str(e)
        }


# =========================================================
# UPDATE FACULTY
# =========================================================

@app.put(
    "/faculty-information/{information_id}"
)
def edit_faculty_information(
    information_id: int,
    request: FacultyInformationRequest
):

    try:

        category = request.category.strip()
        title = request.title.strip()
        content = request.content.strip()


        if not category:

            return {
                "status": "error",
                "message": "Category is required."
            }


        if not title:

            return {
                "status": "error",
                "message": "Title is required."
            }


        if not content:

            return {
                "status": "error",
                "message": "Information is required."
            }


        updated = update_faculty_information(
            information_id=information_id,
            category=category,
            title=title,
            content=content
        )


        if not updated:

            return {
                "status": "error",
                "message": "Faculty information not found."
            }


        return {
            "status": "success",
            "message": "Faculty information updated successfully."
        }


    except Exception as e:

        print(
            "UPDATE FACULTY INFORMATION ERROR:",
            e
        )

        return {
            "status": "error",
            "message": str(e)
        }


# =========================================================
# DELETE FACULTY
# =========================================================

@app.delete(
    "/faculty-information/{information_id}"
)
def remove_faculty_information(
    information_id: int
):

    try:

        deleted = (
            delete_faculty_information(
                information_id
            )
        )


        if not deleted:

            return {
                "status": "error",
                "message": "Faculty information not found."
            }


        return {
            "status": "success",
            "message": "Faculty information deleted successfully."
        }


    except Exception as e:

        print(
            "DELETE FACULTY INFORMATION ERROR:",
            e
        )

        return {
            "status": "error",
            "message": str(e)
        }


# =========================================================
# CLEAR MEMORY
# =========================================================

@app.post("/clear-memory")
def clear_memory():

    global previous_question

    previous_question = ""

    return {
        "message": "Conversation memory cleared."
    }


# =========================================================
# AUTH HELPERS
# =========================================================

def get_dashboard_path(role):

    dashboard_paths = {
        "student": "/student-dashboard",
        "faculty": "/faculty-dashboard",
        "admin": "/admin-dashboard"
    }

    return dashboard_paths.get(
        str(role).lower(),
        "/"
    )


# =========================================================
# REGISTER
# =========================================================

@app.post(
    "/auth/register",
    status_code=status.HTTP_201_CREATED
)
def register_user(
    request: RegisterRequest
):

    name = request.name.strip()
    email = request.email.strip().lower()
    password = request.password
    role = request.role.strip().lower()
    access_code = request.access_code.strip()

    if len(name) < 2:

        raise HTTPException(
            status_code=400,
            detail="Please enter your full name."
        )

    if not re.fullmatch(
        r"[^\s@]+@[^\s@]+\.[^\s@]+",
        email
    ):

        raise HTTPException(
            status_code=400,
            detail="Please enter a valid email address."
        )

    if len(password) < 8:

        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters."
        )

    if role not in [
        "student",
        "faculty",
        "admin"
    ]:

        raise HTTPException(
            status_code=400,
            detail="Invalid account role."
        )

    if role == "faculty":

        faculty_code = os.getenv(
            "FACULTY_REGISTRATION_CODE",
            ""
        ).strip()

        if not faculty_code:

            raise HTTPException(
                status_code=503,
                detail="Faculty registration is currently disabled."
            )

        if not hmac.compare_digest(
            access_code,
            faculty_code
        ):

            raise HTTPException(
                status_code=403,
                detail="Invalid faculty access code."
            )

    if role == "admin":

        admin_code = os.getenv(
            "ADMIN_REGISTRATION_CODE",
            ""
        ).strip()

        if not admin_code:

            raise HTTPException(
                status_code=503,
                detail="Admin registration is currently disabled."
            )

        if not hmac.compare_digest(
            access_code,
            admin_code
        ):

            raise HTTPException(
                status_code=403,
                detail="Invalid admin access code."
            )

    existing_user = get_user_by_email(
        email
    )

    if existing_user:

        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists."
        )

    password_hash = hash_password(
        password
    )

    user_id = save_user(
        name=name,
        email=email,
        role=role,
        password_hash=password_hash
    )

    return {
        "status": "success",
        "message": "Account created successfully. Please login.",
        "user": {
            "id": user_id,
            "name": name,
            "email": email,
            "role": role
        }
    }


# =========================================================
# LOGIN
# =========================================================

@app.post("/auth/login")
def login_user(
    request: LoginRequest,
    response: Response
):

    email = request.email.strip().lower()

    user = get_login_user_by_email(
        email
    )

    if (
        not user
        or not verify_password(
            request.password,
            user.get("password_hash")
        )
    ):

        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password."
        )

    session_token = create_login_session(
        user["id"]
    )

    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        max_age=SESSION_HOURS * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=(
            os.getenv("RENDER") == "true"
            or os.getenv("APP_BASE_URL", "").startswith("https://")
        ),
        path="/"
    )

    return {
        "status": "success",
        "message": "Login successful.",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        },
        "dashboard": get_dashboard_path(
            user["role"]
        )
    }


# =========================================================
# LOGOUT
# =========================================================

@app.post("/auth/logout")
def logout_user(
    request: Request,
    response: Response
):

    session_token = request.cookies.get(
        COOKIE_NAME
    )

    logout_session(
        session_token
    )

    response.delete_cookie(
        COOKIE_NAME,
        path="/"
    )

    return {
        "status": "success",
        "message": "Logout successful."
    }


# =========================================================
# CURRENT USER
# =========================================================

@app.get("/auth/me")
def current_logged_in_user(
    current_user=Depends(
        get_current_user
    )
):

    return {
        "status": "success",
        "user": current_user,
        "dashboard": get_dashboard_path(
            current_user["role"]
        )
    }

