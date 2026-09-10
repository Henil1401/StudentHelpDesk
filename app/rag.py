from pathlib import Path
import os
import re

import faiss
from pypdf import PdfReader

from app.database.database import get_faculty_information


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

KNOWLEDGE_DIR = BASE_DIR / "knowledge_base"

TEXT_FILE = KNOWLEDGE_DIR / "knowledge.txt"

PDF_FILES = sorted(
    KNOWLEDGE_DIR.glob("*.pdf")
)


# =========================================================
# READ KNOWLEDGE FILES
# =========================================================

text_parts = []

if TEXT_FILE.exists():
    try:
        text_parts.append(
            TEXT_FILE.read_text(encoding="utf-8")
        )
    except Exception as e:
        print("Knowledge file error:", e)

for pdf_file in PDF_FILES:
    try:
        reader = PdfReader(str(pdf_file))

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
                text_parts.append(page_text)

        print("PDF loaded:", pdf_file.name)

    except Exception as e:
        print("PDF reading error:", pdf_file.name, e)


# =========================================================
# CLEAN TEXT
# =========================================================

raw_text = "\n".join(text_parts)

text = re.sub(r"\s+", " ", raw_text).strip()

print("====================================")
print("AI STUDENT HELP DESK - RAG")
print("====================================")
print("Knowledge file:", TEXT_FILE.exists())
print("PDF files loaded:", len(PDF_FILES))


# =========================================================
# EXACT EXAM DATA
# =========================================================

EXAMS = {
    "artificial intelligence":
        "The official subject-wise Artificial Intelligence exam date, time and room are not available in the academic calendar. The End-Semester Regular/Remedial examination session for Semester 3, 5 and 7 is scheduled from 19 November 2026 to 5 December 2026.",

    "database management systems":
        "The official subject-wise Database Management Systems exam date, time and room are not available in the academic calendar. The End-Semester Regular/Remedial examination session for Semester 3, 5 and 7 is scheduled from 19 November 2026 to 5 December 2026.",

    "computer networks":
        "The official subject-wise Computer Networks exam date, time and room are not available in the academic calendar. The End-Semester Regular/Remedial examination session for Semester 3, 5 and 7 is scheduled from 19 November 2026 to 5 December 2026.",

    "cloud computing":
        "The official subject-wise Cloud Computing exam date, time and room are not available in the academic calendar. The End-Semester Regular/Remedial examination session for Semester 3, 5 and 7 is scheduled from 19 November 2026 to 5 December 2026.",

    "software engineering":
        "The official subject-wise Software Engineering exam date, time and room are not available in the academic calendar. The End-Semester Regular/Remedial examination session for Semester 3, 5 and 7 is scheduled from 19 November 2026 to 5 December 2026.",
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
        "Annual Cultural Event is on 30 November 2026 at 4:00 PM in the Main Auditorium.",
}


# =========================================================
# HOLIDAYS
# =========================================================

HOLIDAYS = [
    "2 October 2026 - Gandhi Jayanti",
    "21 October 2026 - Dussehra",
    "6 November 2026 to 14 November 2026 - Diwali Vacation",
    "25 December 2026 - Christmas",
    "26 January 2027 - Republic Day",
]


# =========================================================
# OFFICIAL ACADEMIC CALENDAR 2026-2027
# =========================================================

ACADEMIC_CALENDAR = {
    "mid_sem_practical":
        "The Mid-Sem Practical Examination for SOIS Semester 3, 5 and 7 will be conducted from 21 September 2026 to 26 September 2026.",

    "mid_sem_exam":
        "The Mid-Sem Examination for Semester 3, 5 and 7 will be conducted from 5 October 2026 to 10 October 2026.",

    "mid_sem_result":
        "The Mid-Semester Examination result will be declared on 17 October 2026.",

    "remedial_internal_viva":
        "The Mid-Sem Remedial Examination, Internal Submission and Viva will be conducted from 26 October 2026 to 31 October 2026.",

    "term_end":
        "The academic term will end on 31 October 2026.",

    "remedial_result":
        "The Mid-Semester Remedial Examination result will be declared on 5 November 2026.",

    "diwali_vacation":
        "The Diwali vacation will be from 6 November 2026 to 14 November 2026.",

    "end_sem_internship_programmes":
        "The End-Semester Theory and Practical Regular/Remedial examination session for internship-applicable programmes will be conducted from 19 November 2026 to 28 November 2026.",

    "end_sem_odd_semesters":
        "The End-Semester Theory and Practical Regular/Remedial examination session for Semester 3, 5 and 7 will be conducted from 19 November 2026 to 5 December 2026.",

    "end_sem_remedial_even_semesters":
        "The End-Semester Theory and Practical Remedial examination session for Semester 2, 4, 6 and 8 will be conducted from 19 November 2026 to 20 December 2026.",

    "internship":
        "The internship period for applicable programmes will be from 30 November 2026 to 9 January 2027.",

    "semester_5_result":
        "The End-Semester Regular/Remedial Examination result declaration phase for Semester 5 will start on 19 December 2026.",

    "semester_3_7_result":
        "The End-Semester Regular/Remedial Examination result declaration phase for Semester 3 and 7 will start on 9 January 2027.",
}


ACADEMIC_WEEKS = {
    1: "21 June 2026 to 27 June 2026",
    2: "28 June 2026 to 4 July 2026",
    3: "5 July 2026 to 11 July 2026",
    4: "12 July 2026 to 18 July 2026",
    5: "19 July 2026 to 25 July 2026",
    6: "26 July 2026 to 1 August 2026",
    7: "2 August 2026 to 8 August 2026",
    8: "9 August 2026 to 15 August 2026",
    9: "16 August 2026 to 22 August 2026",
    10: "23 August 2026 to 29 August 2026",
    11: "30 August 2026 to 5 September 2026",
    12: "6 September 2026 to 12 September 2026",
    13: "13 September 2026 to 19 September 2026",
    14: "20 September 2026 to 26 September 2026",
    15: "27 September 2026 to 3 October 2026",
    16: "4 October 2026 to 10 October 2026",
    17: "11 October 2026 to 17 October 2026",
    18: "18 October 2026 to 24 October 2026",
    19: "25 October 2026 to 31 October 2026",
    20: "1 November 2026 to 7 November 2026",
    21: "8 November 2026 to 14 November 2026",
    22: "15 November 2026 to 21 November 2026",
    23: "22 November 2026 to 28 November 2026",
    24: "29 November 2026 to 5 December 2026",
    25: "6 December 2026 to 12 December 2026",
    26: "13 December 2026 to 19 December 2026",
    27: "20 December 2026 to 26 December 2026",
    28: "27 December 2026 to 2 January 2027",
}


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
#
# Render: HELPDESK_EMBEDDINGS=onnx
# Local: leave that variable unset to use the original model.
# =========================================================

if os.getenv("HELPDESK_EMBEDDINGS", "").strip().lower() == "onnx":
    import numpy as np
    from fastembed import TextEmbedding

    class CloudEmbeddingModel:
        def __init__(self):
            self.backend = TextEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                threads=1,
            )

        def encode(
            self,
            sentences,
            convert_to_numpy=True,
            normalize_embeddings=False,
        ):
            if isinstance(sentences, str):
                sentences = [sentences]

            vectors = list(
                self.backend.embed(
                    sentences,
                    batch_size=1,
                )
            )

            if not vectors:
                return np.empty(
                    (0, 384),
                    dtype=np.float32,
                )

            embeddings = np.asarray(
                vectors,
                dtype=np.float32,
            )

            if normalize_embeddings:
                lengths = np.linalg.norm(
                    embeddings,
                    axis=1,
                    keepdims=True,
                )

                embeddings = (
                    embeddings / np.maximum(lengths, 1e-12)
                )

            return embeddings

    print(
        "Loading cloud ONNX embedding model...",
        flush=True,
    )

    model = CloudEmbeddingModel()

else:
    from sentence_transformers import SentenceTransformer

    print(
        "Loading local embedding model...",
        flush=True,
    )

    model = SentenceTransformer(
        "all-MiniLM-L6-v2"
    )

print("Embedding model loaded.", flush=True)


# =========================================================
# CREATE RAG CHUNKS
# =========================================================

chunks = []

if text:
    words = text.split()
    chunk_size = 150

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(
            words[i:i + chunk_size]
        )

        if len(chunk.strip()) > 20:
            chunks.append(chunk.strip())


# =========================================================
# CREATE FAISS INDEX
# =========================================================

if chunks:
    embeddings = model.encode(
        chunks,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    index = faiss.IndexFlatIP(
        embeddings.shape[1]
    )

    index.add(embeddings)

else:
    index = None

print("General RAG chunks:", len(chunks))


# =========================================================
# GET FACULTY INFORMATION
# =========================================================

def get_latest_faculty_information():
    try:
        return get_faculty_information()

    except Exception as e:
        print("Faculty information error:", e)
        return []


# =========================================================
# FACULTY INFORMATION SEARCH
# =========================================================

def search_faculty_information(question: str):
    if not question:
        return []

    try:
        faculty_information = (
            get_latest_faculty_information()
        )

    except Exception as e:
        print("Faculty search error:", e)
        return []

    if not faculty_information:
        return []

    q = question.lower().strip()
    q = re.sub(r"[^\w\s]", " ", q)
    q = re.sub(r"\s+", " ", q).strip()

    question_words = set(
        re.findall(r"\b[a-zA-Z0-9]+\b", q)
    )

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
        "test",
    }

    meaningful_words = (
        question_words - stop_words
    )

    matched = []

    for item in faculty_information:
        category = str(
            item.get("category", "")
        ).lower()

        title = str(
            item.get("title", "")
        ).lower()

        content = str(
            item.get("content", "")
        ).lower()

        combined_text = (
            category + " " + title + " " + content
        )

        record_words = set(
            re.findall(
                r"\b[a-zA-Z0-9]+\b",
                combined_text,
            )
        )

        common_words = (
            meaningful_words & record_words
        )

        score = len(common_words)

        title_words = set(
            re.findall(
                r"\b[a-zA-Z0-9]+\b",
                title,
            )
        )

        title_matches = (
            meaningful_words & title_words
        )

        score += len(title_matches) * 5

        if category and category in q:
            score += 3

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
            "who is teaching",
        ]

        is_faculty_question = any(
            word in q
            for word in faculty_words
        )

        if is_faculty_question:
            score += 10

        if (
            "time" in q
            and re.search(
                r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
                content,
                re.IGNORECASE,
            )
        ):
            score += 8

        if (
            (
                "where" in q
                or "venue" in q
                or "room" in q
            )
            and re.search(
                r"\b(room|lab|auditorium|hall)\b",
                content,
                re.IGNORECASE,
            )
        ):
            score += 8

        if (
            "meeting" in q
            and "meeting" in combined_text
        ):
            score += 8

        if (
            "tomorrow" in q
            and "tomorrow" in combined_text
        ):
            score += 6

        if score > 0:
            matched.append({
                "score": score,
                "item": item,
            })

    if not matched:
        return []

    matched.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    best = matched[0]["item"]

    answer = (
        str(best.get("title", ""))
        + ": "
        + str(best.get("content", ""))
    )

    print(
        "Faculty information matched:",
        best.get("title", ""),
        "Score:",
        matched[0]["score"],
    )

    return [answer]


# =========================================================
# SEMANTIC SEARCH
# =========================================================

def semantic_search(
    question: str,
    top_k: int = 3,
):
    if not question:
        return []

    if index is None:
        return []

    question_embedding = model.encode(
        [question],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    scores, indices = index.search(
        question_embedding,
        top_k,
    )

    results = []

    for score, idx in zip(
        scores[0],
        indices[0],
    ):
        if idx < 0:
            continue

        results.append({
            "text": chunks[idx],
            "score": float(score),
        })

    return results


# =========================================================
# SEARCH KNOWLEDGE
# =========================================================

def search_knowledge(
    question: str,
    top_k: int = 1,
):
    q = question.lower().strip()
    normalized_q = re.sub(r"[-_]+", " ", q)
    normalized_q = re.sub(r"\s+", " ", normalized_q).strip()

    if not q:
        return []

    # FEES

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
        "tuition fees",
    ]

    if any(word in q for word in fee_words):
        return [FEES_ANSWER]

    # HOSTEL

    if (
        "hostel" in q
        or "hostel room" in q
        or "room change" in q
        or "change my room" in q
        or "changing my room" in q
        or "room allotment" in q
    ):
        return [HOSTEL_ANSWER]

    # OFFICIAL ACADEMIC CALENDAR

    week_match = re.search(
        r"\bweek\s*(\d{1,2})\b",
        normalized_q,
    )

    if week_match:
        week_number = int(week_match.group(1))
        week_dates = ACADEMIC_WEEKS.get(week_number)

        if week_dates:
            return [
                f"Academic Week {week_number} is from {week_dates}."
            ]

    if "diwali" in normalized_q:
        return [
            ACADEMIC_CALENDAR["diwali_vacation"]
        ]

    if "gandhi jayanti" in normalized_q:
        return [
            "The university will observe Gandhi Jayanti on 2 October 2026."
        ]

    if "dussehra" in normalized_q:
        return [
            "The university will observe the Dussehra holiday on 21 October 2026."
        ]

    if "christmas" in normalized_q:
        return [
            "The university will observe the Christmas holiday on 25 December 2026."
        ]

    if "republic day" in normalized_q:
        return [
            "The university will observe Republic Day on 26 January 2027."
        ]

    if (
        "remedial" in normalized_q
        and "result" in normalized_q
    ):
        return [
            ACADEMIC_CALENDAR["remedial_result"]
        ]

    if (
        "mid sem" in normalized_q
        and (
            "remedial" in normalized_q
            or "internal" in normalized_q
            or "viva" in normalized_q
        )
    ):
        return [
            ACADEMIC_CALENDAR["remedial_internal_viva"]
        ]

    if (
        "mid sem" in normalized_q
        and "practical" in normalized_q
    ):
        return [
            ACADEMIC_CALENDAR["mid_sem_practical"]
        ]

    if (
        "mid sem" in normalized_q
        and "result" in normalized_q
    ):
        return [
            ACADEMIC_CALENDAR["mid_sem_result"]
        ]

    if "mid sem" in normalized_q:
        return [
            ACADEMIC_CALENDAR["mid_sem_exam"]
        ]

    if "term end" in normalized_q:
        return [
            ACADEMIC_CALENDAR["term_end"]
        ]

    if (
        "internship" in normalized_q
        and "exam" not in normalized_q
        and "examination" not in normalized_q
        and "end sem" not in normalized_q
        and "end semester" not in normalized_q
    ):
        return [
            ACADEMIC_CALENDAR["internship"]
        ]

    if (
        "result" in normalized_q
        and re.search(r"\b(?:sem|semester)\s*5\b", normalized_q)
    ):
        return [
            ACADEMIC_CALENDAR["semester_5_result"]
        ]

    if (
        "result" in normalized_q
        and (
            re.search(r"\b(?:sem|semester)\s*3\b", normalized_q)
            or re.search(r"\b(?:sem|semester)\s*7\b", normalized_q)
        )
    ):
        return [
            ACADEMIC_CALENDAR["semester_3_7_result"]
        ]

    if (
        "result" in normalized_q
        and (
            "semester" in normalized_q
            or "sem" in normalized_q
        )
    ):
        return [
            ACADEMIC_CALENDAR["semester_5_result"]
            + "\n"
            + ACADEMIC_CALENDAR["semester_3_7_result"]
        ]

    if (
        "end sem" in normalized_q
        or "end semester" in normalized_q
    ):
        if re.search(
            r"\b(?:sem|semester)\s*(?:2|4|6|8)\b",
            normalized_q,
        ):
            return [
                ACADEMIC_CALENDAR[
                    "end_sem_remedial_even_semesters"
                ]
            ]

        if "internship" in normalized_q:
            return [
                ACADEMIC_CALENDAR[
                    "end_sem_internship_programmes"
                ]
            ]

        return [
            ACADEMIC_CALENDAR["end_sem_odd_semesters"]
            + "\n"
            + ACADEMIC_CALENDAR[
                "end_sem_remedial_even_semesters"
            ]
        ]

    # HOLIDAYS

    holiday_words = [
        "holiday",
        "holidays",
        "chhuti",
        "chhutti",
        "leave",
        "vacation",
    ]

    if any(word in q for word in holiday_words):
        return [
            "Academic Holidays - 2026-2027\n\n"
            + "\n".join(HOLIDAYS)
        ]

    # EXAMS

    if (
        "exam" in q
        or "examination" in q
        or "paper" in q
        or "test" in q
    ):
        if (
            "artificial intelligence" in q
            or "artificial" in q
            or re.search(r"\bai\b", q)
        ):
            print(
                "Exact exam match: Artificial Intelligence"
            )

            return [
                EXAMS["artificial intelligence"]
            ]

        if "dbms" in q or "database" in q:
            print(
                "Exact exam match: Database Management Systems"
            )

            return [
                EXAMS["database management systems"]
            ]

        if (
            "computer network" in q
            or "computer networks" in q
            or "network" in q
        ):
            print(
                "Exact exam match: Computer Networks"
            )

            return [
                EXAMS["computer networks"]
            ]

        if "cloud" in q:
            print(
                "Exact exam match: Cloud Computing"
            )

            return [
                EXAMS["cloud computing"]
            ]

        if "software" in q:
            print(
                "Exact exam match: Software Engineering"
            )

            return [
                EXAMS["software engineering"]
            ]

        return [
            "Official Examination Sessions\n\n"
            + ACADEMIC_CALENDAR["mid_sem_practical"]
            + "\n"
            + ACADEMIC_CALENDAR["mid_sem_exam"]
            + "\n"
            + ACADEMIC_CALENDAR["end_sem_odd_semesters"]
            + "\n"
            + ACADEMIC_CALENDAR[
                "end_sem_remedial_even_semesters"
            ]
        ]

    # EVENTS

    event_words = [
        "event",
        "events",
        "workshop",
        "orientation",
        "presentation",
        "cultural",
    ]

    if any(word in q for word in event_words):
        if "workshop" in q:
            return [
                EVENTS["technical workshop"]
            ]

        if "orientation" in q:
            return [
                EVENTS["student orientation programme"]
            ]

        if "project" in q or "presentation" in q:
            return [
                EVENTS["student project presentation"]
            ]

        if "cultural" in q:
            return [
                EVENTS["annual cultural event"]
            ]

        return [
            "Events - November 2026\n\n"
            + "\n".join(EVENTS.values())
        ]

    # FACULTY DATABASE INFORMATION

    faculty_results = search_faculty_information(
        question
    )

    if faculty_results:
        return faculty_results

    # GENERAL RAG SEARCH

    semantic_results = semantic_search(
        question,
        top_k=top_k,
    )

    if not semantic_results:
        return []

    best_score = semantic_results[0]["score"]

    print(
        "RAG similarity:",
        round(best_score, 4),
    )

    if best_score < 0.25:
        return []

    return [
        item["text"]
        for item in semantic_results
    ]
