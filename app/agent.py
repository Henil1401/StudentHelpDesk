import re

from app.agents.intent_agent import detect_intent
from app.agents.entity_agent import extract_entities
from app.agents.retrieval_agent import retrieve_knowledge
from app.agents.decision_agent import make_decision
from app.agents.faculty_agent import route_to_faculty
from app.agents.ticket_agent import create_ticket


# =========================================================
# CLEAN ANSWER
# =========================================================

def clean_answer(
    question: str,
    text: str,
    previous_question: str = ""
):

    if not text:
        return "Sorry, information not found."

    q = question.lower().strip()

    full_text = " ".join(
        str(text).split()
    )


    # =====================================================
    # FOLLOW-UP QUESTIONS
    # =====================================================

    follow_up = [
        "when is it?",
        "when is it",
        "what time?",
        "what time",
        "what is the venue?",
        "what is the venue",
        "where is it?",
        "where is it",
        "which room?",
        "which room"
    ]

    if q in follow_up and previous_question:
        q = previous_question.lower().strip()


    # =====================================================
    # TIME QUESTION
    # =====================================================

    is_time_question = bool(
        re.search(
            r"\b(what time|time of|at what time)\b",
            q,
            re.IGNORECASE
        )
    )

    if is_time_question:

        time_match = re.search(
            r"\b\d{1,2}:\d{2}\s*(?:AM|PM)"
            r"\s*(?:to|-)\s*"
            r"\d{1,2}:\d{2}\s*(?:AM|PM)\b",
            full_text,
            re.IGNORECASE
        )

        if time_match:
            return time_match.group(0)


        time_match = re.search(
            r"\bat\s+\d{1,2}:\d{2}\s*(?:AM|PM)\b",
            full_text,
            re.IGNORECASE
        )

        if time_match:

            return time_match.group(0).replace(
                "at ",
                ""
            )


    # =====================================================
    # VENUE QUESTION
    # =====================================================

    is_venue_question = bool(
        re.search(
            r"\b(venue|where is it|where|which room)\b",
            q,
            re.IGNORECASE
        )
    )

    if is_venue_question:

        venue_match = re.search(
            r"\b(?:in|at)\s+"
            r"(Room\s+[A-Z]-?\d+|"
            r"Lab\s+\d+|"
            r"Main Auditorium)\b",
            full_text,
            re.IGNORECASE
        )

        if venue_match:
            return venue_match.group(1)


    # =====================================================
    # DATE QUESTION
    # =====================================================

    is_date_question = bool(
        re.search(
            r"\b(when|which date|what date|date)\b",
            q,
            re.IGNORECASE
        )
    )

    if is_date_question:

        # Return the complete date range before checking a single date.
        # Example: 6 November 2026 to 14 November 2026
        date_range_match = re.search(
            r"\b(?:from\s+)?"
            r"\d{1,2}\s+"
            r"(?:January|February|March|April|May|June|July|"
            r"August|September|October|November|December)"
            r"\s+\d{4}\s+"
            r"(?:to|-)\s+"
            r"\d{1,2}\s+"
            r"(?:January|February|March|April|May|June|July|"
            r"August|September|October|November|December)"
            r"\s+\d{4}\b",
            full_text,
            re.IGNORECASE
        )

        if date_range_match:
            answer = date_range_match.group(0)

            if answer.lower().startswith("from "):
                answer = answer[5:]

            return answer

        date_match = re.search(
            r"\b\d{1,2}\s+"
            r"(?:January|February|March|April|May|June|July|"
            r"August|September|October|November|December)"
            r"\s+\d{4}\b",
            full_text,
            re.IGNORECASE
        )

        if date_match:
            return date_match.group(0)


    # =====================================================
    # KEYWORDS
    # =====================================================

    keywords = []


    if (
        "artificial intelligence" in q
        or re.search(r"\bai\b", q)
    ):

        keywords = [
            "artificial intelligence"
        ]


    elif "database" in q:

        keywords = [
            "database"
        ]


    elif (
        "computer network" in q
        or "networks" in q
    ):

        keywords = [
            "computer networks"
        ]


    elif "cloud" in q:

        keywords = [
            "cloud computing"
        ]


    elif "software engineering" in q:

        keywords = [
            "software engineering"
        ]


    elif "diwali" in q:

        keywords = [
            "diwali"
        ]


    elif "guru nanak" in q:

        keywords = [
            "guru nanak"
        ]


    elif (
        "technical workshop" in q
        or "workshop" in q
    ):

        keywords = [
            "technical workshop"
        ]


    elif "cultural event" in q:

        keywords = [
            "annual cultural event"
        ]


    elif "orientation" in q:

        keywords = [
            "orientation"
        ]


    elif "project presentation" in q:

        keywords = [
            "project presentation"
        ]


    elif (
        "holiday" in q
        or "holidays" in q
    ):

        keywords = [
            "holiday"
        ]


    # =====================================================
    # SENTENCES
    # =====================================================

    sentences = re.split(
        r"(?<=[.!?])\s+",
        full_text
    )


    # =====================================================
    # FIND RELEVANT SENTENCE
    # =====================================================

    for sentence in sentences:

        s = sentence.lower()

        if any(
            keyword in s
            for keyword in keywords
        ):

            return sentence.strip()


    # =====================================================
    # FOLLOW-UP FALLBACK
    # =====================================================

    if previous_question:

        previous = previous_question.lower()

        for sentence in sentences:

            s = sentence.lower()

            if (
                (
                    "exam" in previous
                    and "exam" in s
                )
                or
                (
                    "workshop" in previous
                    and "workshop" in s
                )
                or
                (
                    "event" in previous
                    and "event" in s
                )
                or
                (
                    "holiday" in previous
                    and "holiday" in s
                )
            ):

                return sentence.strip()


    # =====================================================
    # FINAL FALLBACK
    # =====================================================

    return sentences[0].strip()


# =========================================================
# MULTI-AGENT SYSTEM
# =========================================================

def run_agent(
    question: str,
    results: list = None,
    previous_question: str = ""
):

    # =====================================================
    # 1. INTENT RECOGNITION
    # =====================================================

    intent = detect_intent(
        question
    )


    # =====================================================
    # 2. ENTITY EXTRACTION
    # =====================================================

    entities = extract_entities(
        question
    )


    # =====================================================
    # 3. KNOWLEDGE RETRIEVAL
    # =====================================================

    retrieved_results = retrieve_knowledge(
        question
    )


    # =====================================================
    # USE EXTERNAL RESULTS IF NEEDED
    # =====================================================

    if (
        not retrieved_results
        and results
    ):

        retrieved_results = results


    # =====================================================
    # 4. DECISION AGENT
    # =====================================================

    decision = make_decision(
        retrieved_results
    )


    # =====================================================
    # 5. CREATE TICKET
    # =====================================================

    if decision == "ticket":

        department = route_to_faculty(
            intent
        )

        try:

            ticket = create_ticket(
                question=question,
                intent=intent,
                department=department
            )

            if isinstance(ticket, dict):

                ticket_id = ticket.get(
                    "ticket_id"
                )

            else:

                ticket_id = str(ticket)


            return {

                "answer":
                    "The information was not found in the "
                    "university knowledge base, so a support "
                    "ticket has been created automatically.",

                "source":
                    "ticket_system",

                "status":
                    "ticket_created",

                "type":
                    "support_ticket",

                "intent":
                    intent,

                "entities":
                    entities,

                "ticket_id":
                    ticket_id,

                "faculty":
                    department

            }

        except Exception as error:

            print(
                "Ticket creation error:",
                error
            )

            return {

                "answer":
                    "Sorry, this information is not available "
                    "in the university knowledge base.",

                "source":
                    "university_knowledge",

                "status":
                    "not_found",

                "type":
                    "information_not_found",

                "intent":
                    intent,

                "entities":
                    entities,

                "ticket_id":
                    None,

                "faculty":
                    department

            }


    # =====================================================
    # 6. NO RETRIEVED RESULT
    # =====================================================

    if not retrieved_results:

        return {

            "answer":
                "Sorry, this information is not "
                "available in the university "
                "knowledge base.",

            "source":
                "university_knowledge",

            "status":
                "not_found",

            "type":
                "information_not_found",

            "intent":
                intent,

            "entities":
                entities,

            "ticket_id":
                None,

            "faculty":
                route_to_faculty(
                    intent
                )

        }


    # =====================================================
    # 7. GET FIRST RESULT
    # =====================================================

    text = retrieved_results[0]


    if isinstance(text, dict):

        text = text.get(
            "text",
            text.get(
                "content",
                str(text)
            )
        )


    # =====================================================
    # 8. CLEAN ANSWER
    # =====================================================

    answer = clean_answer(

        question=question,

        text=str(text),

        previous_question=previous_question

    )


    # =====================================================
    # 9. FINAL RESPONSE
    # =====================================================

    return {

        "answer":
            answer,

        "source":
            "university_knowledge",

        "status":
            "found",

        "type":
            "multi_agent_rag",

        "intent":
            intent,

        "entities":
            entities,

        "ticket_id":
            None,

        "faculty":
            route_to_faculty(
                intent
            )

    }
