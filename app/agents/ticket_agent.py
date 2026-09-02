from app.database.database import save_ticket


def create_ticket(
    question: str,
    intent: str = "general",
    department: str = "Student Services",
    user_id=None
):

    question = question.strip()

    ticket_id = save_ticket(
        question=question,
        intent=intent,
        department=department,
        user_id=user_id
    )

    return {
        "ticket_id": ticket_id,
        "question": question,
        "intent": intent,
        "department": department,
        "status": "open"
    }
