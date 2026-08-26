import uuid

from app.database.database import save_ticket


def create_ticket(
    question: str,
    intent: str = "general",
    department: str = "Student Services"
):

    question = question.strip()

    ticket_id = save_ticket(
        question=question,
        intent=intent,
        department=department
    )

    return {
        "ticket_id": ticket_id,
        "question": question,
        "intent": intent,
        "department": department,
        "status": "open"
    }