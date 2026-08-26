from pathlib import Path
import re

from sentence_transformers import SentenceTransformer
import faiss
from pypdf import PdfReader

from app.database.database import get_faculty_information


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

KNOWLEDGE_DIR = BASE_DIR / "knowledge_base"

TEXT_FILE = KNOWLEDGE_DIR / "knowledge.txt"

PDF_FILE = KNOWLEDGE_DIR / "silver_oak_university.pdf"


# =========================================================
# READ KNOWLEDGE.TXT
# =========================================================

text_parts = []

if TEXT_FILE.exists():

    try:

        text_parts.append(
            TEXT_FILE.read_text(
                encoding="utf-8"
            )
        )

    except Exception as e:

        print(
            "Knowledge file error:",
            e
        )


# =========================================================
# READ PDF
# =========================================================

if PDF_FILE.exists():

    try:

        reader = PdfReader(
            str(PDF_FILE)
        )

        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:

                text_parts.append(
                    page_text
                )

    except Exception as e:

        print(
            "PDF reading error:",
            e
        )


# =========================================================
# CLEAN TEXT
# =========================================================

raw_text = "\n".join(
    text_parts
)

text = re.sub(
    r"\s+",
    " ",
    raw_text
).strip()


print("====================================")
print("AI STUDENT HELP DESK - RAG")
print("====================================")

print(
    "Knowledge file:",
    TEXT_FILE.exists()
)

print(
    "PDF loaded:",
    PDF_FILE.exists()
)


# =========================================================
# EXACT EXAM DATA
# =========================================================

EXAMS = {

    "artificial intelligence":
        "Artificial Intelligence exam is on 10 November 2026 from 10:00 AM to 12:00 PM in Room A-101.",

    "database management systems":
        "Database Management Systems exam is on 12 November 2026 from 10:00 AM to 12:00 PM in Room A-102.",

    "computer networks":
        "Computer Networks exam is on 16 November 2026 from 10:00 AM to 12:00 PM in Room A-103.",

    "cloud computing":
        "Cloud Computing exam is on 19 November 2026 from 10:00 AM to 12:00 PM in Room A-101.",

    "software engineering":
        "Software Engineering exam is on 23 November 2026 from 10:00 AM to 12:00 PM in Room A-104."

}


# =========================================================
# EVENTS
# =========================================================

EVENTS = {

    "student orientation programme":
        "Student Orientation Programme is on 5 November 2026 at 11:00 AM in the Seminar Hall.",

    "technical workshop":
        "Technical Workshop is on 14 November 2026 at 2:00 PM in Lab 2.",

    "student project presentation":
        "Student Project Presentation is on 26 November 2026 at 10:00 AM in the Seminar Hall.",

    "annual cultural event":
        "Annual Cultural Event is on 30 November 2026 at 4:00 PM in the Main Auditorium."

}


# =========================================================
# HOLIDAYS
# =========================================================

HOLIDAYS = [

    "9 November 2026 - Diwali Holiday",

    "10 November 2026 - Academic Holiday as scheduled",

    "24 November 2026 - Guru Nanak Jayanti"

]


# =========================================================
# FEES
# =========================================================

FEES_ANSWER = (

    "To pay your fees, login to the university/student portal, "
    "open the Fees or Fee Payment section, select the applicable fee, "
    "complete the online payment, and save or download the payment "
    "receipt for future reference."

)


# =========================================================
# HOSTEL
# =========================================================

HOSTEL_ANSWER = (

    "For changing your hostel room, contact the Hostel Administration "
    "or Warden office. Submit a room-change request mentioning your "
    "current room, reason for change, and preferred room if applicable. "
    "The request will be reviewed by the hostel administration."

)


# =========================================================
# EMBEDDING MODEL
# =========================================================

print(
    "Loading embedding model..."
)

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

print(
    "Embedding model loaded."
)


# =========================================================
# CREATE RAG CHUNKS
# =========================================================

chunks = []

if text:

    words = text.split()

    chunk_size = 150

    for i in range(
        0,
        len(words),
        chunk_size
    ):

        chunk = " ".join(
            words[
                i:i + chunk_size
            ]
        )

        if len(
            chunk.strip()
        ) > 20:

            chunks.append(
                chunk.strip()
            )


# =========================================================
# CREATE FAISS INDEX
# =========================================================

if chunks:

    embeddings = model.encode(

        chunks,

        convert_to_numpy=True,

        normalize_embeddings=True

    ).astype(
        "float32"
    )

    index = faiss.IndexFlatIP(
        embeddings.shape[1]
    )

    index.add(
        embeddings
    )

else:

    index = None


print(
    "General RAG chunks:",
    len(chunks)
)


# =========================================================
# GET FACULTY INFORMATION
# =========================================================

def get_latest_faculty_information():

    try:

        information = get_faculty_information()

        return information

    except Exception as e:

        print(
            "Faculty information error:",
            e
        )

        return []


# =========================================================
# FACULTY INFORMATION SEARCH
# =========================================================

def search_faculty_information(
    question: str
):

    if not question:

        return []

    try:

        faculty_information = (
            get_latest_faculty_information()
        )

    except Exception as e:

        print(
            "Faculty search error:",
            e
        )

        return []

    if not faculty_information:

        return []

    q = question.lower().strip()

    q = re.sub(
        r"[^\w\s]",
        " ",
        q
    )

    q = re.sub(
        r"\s+",
        " ",
        q
    ).strip()

    # =====================================================
    # QUESTION WORDS
    # =====================================================

    question_words = set(
        re.findall(
            r"\b[a-zA-Z0-9]+\b",
            q
        )
    )

    # =====================================================
    # STOP WORDS
    # =====================================================

    stop_words = {

        "what",
        "when",
        "where",
        "which",
        "who",
        "how",
        "is",
        "are",
        "the",
        "a",
        "an",
        "on",
        "in",
        "of",
        "for",
        "to",
        "tell",
        "me",
        "please",
        "can",
        "you",
        "about",
        "it",
        "this",
        "that",
        "does",
        "do",
        "subject",
        "exam",
        "examination",
        "paper",
        "test"

    }

    meaningful_words = (
        question_words
        - stop_words
    )

    # =====================================================
    # CHECK FACULTY RECORDS
    # =====================================================

    matched = []

    for item in faculty_information:

        category = str(
            item.get(
                "category",
                ""
            )
        ).lower()

        title = str(
            item.get(
                "title",
                ""
            )
        ).lower()

        content = str(
            item.get(
                "content",
                ""
            )
        ).lower()

        combined_text = (
            category
            + " "
            + title
            + " "
            + content
        )

        record_words = set(
            re.findall(
                r"\b[a-zA-Z0-9]+\b",
                combined_text
            )
        )

        common_words = (
            meaningful_words
            & record_words
        )

        score = len(
            common_words
        )

        # =================================================
        # TITLE MATCH
        # =================================================

        title_words = set(
            re.findall(
                r"\b[a-zA-Z0-9]+\b",
                title
            )
        )

        title_matches = (
            meaningful_words
            & title_words
        )

        score += (
            len(title_matches) * 5
        )

        # =================================================
        # CATEGORY MATCH
        # =================================================

        if category and category in q:

            score += 3

        # =================================================
        # FACULTY QUESTION
        # =================================================

        faculty_words = [

            "faculty",
            "teacher",
            "professor",
            "lecturer",
            "sir",
            "madam",
            "instructor",
            "department",
            "handled by",
            "who teaches",
            "who handle",
            "who is teaching"

        ]

        is_faculty_question = any(
            word in q
            for word in faculty_words
        )

        if is_faculty_question:

            score += 10

        # =================================================
        # TIME MATCH
        # =================================================

        if (
            "time" in q
            and re.search(
                r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
                content,
                re.IGNORECASE
            )
        ):

            score += 8

        # =================================================
        # VENUE MATCH
        # =================================================

        if (

            (
                "where" in q
                or "venue" in q
                or "room" in q
            )

            and re.search(
                r"\b(room|lab|auditorium|hall)\b",
                content,
                re.IGNORECASE
            )

        ):

            score += 8

        # =================================================
        # MEETING
        # =================================================

        if (
            "meeting" in q
            and "meeting" in combined_text
        ):

            score += 8

        # =================================================
        # TOMORROW
        # =================================================

        if (
            "tomorrow" in q
            and "tomorrow" in combined_text
        ):

            score += 6

        # =================================================
        # ADD MATCH
        # =================================================

        if score > 0:

            matched.append({

                "score": score,

                "item": item

            })

    # =====================================================
    # NO MATCH
    # =====================================================

    if not matched:

        return []

    # =====================================================
    # SORT BEST MATCH
    # =====================================================

    matched.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    best = matched[0]["item"]

    answer = (

        str(
            best.get(
                "title",
                ""
            )
        )

        + ": "

        + str(
            best.get(
                "content",
                ""
            )
        )

    )

    print(
        "Faculty information matched:",
        best.get(
            "title",
            ""
        ),
        "Score:",
        matched[0]["score"]
    )

    return [
        answer
    ]


# =========================================================
# SEMANTIC SEARCH
# =========================================================

def semantic_search(
    question: str,
    top_k: int = 3
):

    if not question:

        return []

    if index is None:

        return []

    question_embedding = model.encode(

        [question],

        convert_to_numpy=True,

        normalize_embeddings=True

    ).astype(
        "float32"
    )

    scores, indices = index.search(

        question_embedding,

        top_k
    )

    results = []

    for score, idx in zip(
        scores[0],
        indices[0]
    ):

        if idx < 0:

            continue

        results.append({

            "text":
                chunks[idx],

            "score":
                float(score)

        })

    return results


# =========================================================
# SEARCH KNOWLEDGE
# =========================================================

def search_knowledge(
    question: str,
    top_k: int = 1
):

    q = question.lower().strip()

    if not q:

        return []

    # =====================================================
    # FEES
    # =====================================================

    fee_words = [

        "fee",
        "fees",
        "fee payment",
        "fees payment",
        "pay fees",
        "pay fee",
        "payment of fees",
        "college fees",
        "tuition fee",
        "tuition fees"

    ]

    if any(
        word in q
        for word in fee_words
    ):

        return [
            FEES_ANSWER
        ]

    # =====================================================
    # HOSTEL
    # =====================================================

    if (

        "hostel" in q

        or "hostel room" in q

        or "room change" in q

        or "change my room" in q

        or "changing my room" in q

        or "room allotment" in q

    ):

        return [
            HOSTEL_ANSWER
        ]

    # =====================================================
    # HOLIDAYS
    # =====================================================

    holiday_words = [

        "holiday",
        "holidays",
        "chhuti",
        "chhutti",
        "leave",
        "vacation"

    ]

    if any(
        word in q
        for word in holiday_words
    ):

        return [

            "Holidays - November 2026\n\n"
            + "\n".join(
                HOLIDAYS
            )

        ]

    # =====================================================
    # EXAMS
    # IMPORTANT: EXAM SEARCH BEFORE FACULTY SEARCH
    # =====================================================

    if (

        "exam" in q

        or "examination" in q

        or "paper" in q

        or "test" in q

    ):

        # Artificial Intelligence

        if (

            "artificial intelligence" in q

            or "artificial" in q

            or re.search(
                r"\bai\b",
                q
            )

        ):

            print(
                "Exact exam match: Artificial Intelligence"
            )

            return [
                EXAMS[
                    "artificial intelligence"
                ]
            ]

        # DBMS

        if (

            "dbms" in q

            or "database" in q

        ):

            print(
                "Exact exam match: Database Management Systems"
            )

            return [
                EXAMS[
                    "database management systems"
                ]
            ]

        # Computer Networks

        if (

            "computer network" in q

            or "computer networks" in q

            or "network" in q

        ):

            print(
                "Exact exam match: Computer Networks"
            )

            return [
                EXAMS[
                    "computer networks"
                ]
            ]

        # Cloud Computing

        if "cloud" in q:

            print(
                "Exact exam match: Cloud Computing"
            )

            return [
                EXAMS[
                    "cloud computing"
                ]
            ]

        # Software Engineering

        if "software" in q:

            print(
                "Exact exam match: Software Engineering"
            )

            return [
                EXAMS[
                    "software engineering"
                ]
            ]

        # All exams

        return [

            "Examination Schedule - November 2026\n\n"
            + "\n".join(
                EXAMS.values()
            )

        ]

    # =====================================================
    # EVENTS
    # =====================================================

    event_words = [

        "event",
        "events",
        "workshop",
        "orientation",
        "presentation",
        "cultural"

    ]

    if any(
        word in q
        for word in event_words
    ):

        if "workshop" in q:

            return [
                EVENTS[
                    "technical workshop"
                ]
            ]

        if "orientation" in q:

            return [
                EVENTS[
                    "student orientation programme"
                ]
            ]

        if (
            "project" in q
            or "presentation" in q
        ):

            return [
                EVENTS[
                    "student project presentation"
                ]
            ]

        if "cultural" in q:

            return [
                EVENTS[
                    "annual cultural event"
                ]
            ]

        return [

            "Events - November 2026\n\n"
            + "\n".join(
                EVENTS.values()
            )

        ]

    # =====================================================
    # FACULTY DATABASE INFORMATION
    # =====================================================

    faculty_results = search_faculty_information(
        question
    )

    if faculty_results:

        return faculty_results

    # =====================================================
    # GENERAL RAG SEARCH
    # =====================================================

    semantic_results = semantic_search(

        question,

        top_k=top_k

    )

    if not semantic_results:

        return []

    # =====================================================
    # SIMILARITY FILTER
    # =====================================================

    best_score = (
        semantic_results[0]["score"]
    )

    print(
        "RAG similarity:",
        round(
            best_score,
            4
        )
    )

    if best_score < 0.25:

        return []

    return [

        item["text"]

        for item in semantic_results

    ]