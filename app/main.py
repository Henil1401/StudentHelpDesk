from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.rag import search_knowledge
from app.agent import run_agent

from app.database.database import (
    get_tickets,
    get_ticket,
    update_ticket_status,
    save_chat,
    get_chat_history,
    get_users,
    save_user,
    get_user_by_email,
    save_faculty_information,
    get_faculty_information,
    update_faculty_information,
    delete_faculty_information
)

from app.agents.ticket_agent import create_ticket
from app.agents.faculty_agent import route_to_faculty

from app.email_service import (
    send_ticket_created_email,
    send_ticket_status_email
)


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="AI Student Help Desk",
    description="Cloud-Based AI Student Help Desk using RAG and Multi-Agent System",
    version="1.0.0"
)


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


class FacultyInformationRequest(BaseModel):
    category: str
    title: str
    content: str


class UserRequest(BaseModel):
    name: str
    email: str
    role: str = "student"


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
# HOME
# =========================================================

@app.get("/")
def home():

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
    background_tasks: BackgroundTasks
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


        is_exam_problem = (
            has_problem_word
            and has_exam_word
        )


        # =================================================
        # EXAM PROBLEM -> CREATE TICKET
        # =================================================

        if is_exam_problem:

            ticket_intent = "exam"

            department = route_to_faculty(
                ticket_intent
            )


            ticket = create_ticket(
                question=question,
                intent=ticket_intent,
                department=department
            )


            ticket_id = None


            if isinstance(ticket, dict):

                ticket_id = ticket.get(
                    "ticket_id"
                )

            elif ticket:

                ticket_id = str(ticket)


            answer = (
                "Your exam timetable issue has been registered "
                "successfully. The Examination Department will "
                "review your ticket."
            )


            # =================================================
            # SAVE CHAT
            # =================================================

            try:

                save_chat(
                    question=question,
                    answer=answer,
                    intent="examination",
                    agent_type="ticket_agent"
                )

            except Exception as history_error:

                print(
                    "CHAT HISTORY ERROR:",
                    history_error
                )


            # =================================================
            # EMAIL IN BACKGROUND
            # =================================================

            student_email = (
                get_student_notification_email()
            )


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
                "intent": "examination",
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
                agent_type=agent_type
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
            "ticket_id": ticket_id
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
def chat_history():

    try:

        history = get_chat_history()

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
def get_all_students():

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
    request: UserRequest
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
    user_id: int
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
    background_tasks: BackgroundTasks
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
            department=department
        )


        ticket_id = None


        if isinstance(ticket, dict):

            ticket_id = ticket.get(
                "ticket_id"
            )

        elif ticket:

            ticket_id = str(ticket)


        student_email = (
            get_student_notification_email()
        )


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
def get_all_tickets():

    try:

        tickets = get_tickets()

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
    ticket_id: str
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


        return {
            "status": "success",
            "ticket": ticket
        }


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
    background_tasks: BackgroundTasks
):

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


        student_email = (
            get_student_notification_email()
        )


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