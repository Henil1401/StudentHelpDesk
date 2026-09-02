import re

from app.rag import search_knowledge
from app.database.database import get_faculty_information


# =========================================================
# STOP WORDS
# =========================================================

STOP_WORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "when",
    "where",
    "what",
    "which",
    "who",
    "whom",
    "why",
    "how",
    "do",
    "does",
    "did",
    "can",
    "could",
    "will",
    "would",
    "should",
    "of",
    "on",
    "in",
    "at",
    "to",
    "for",
    "from",
    "with",
    "and",
    "or",
    "it",
    "this",
    "that",
    "please",
    "tell",
    "me"
}


# =========================================================
# NORMALIZE TEXT
# =========================================================

def normalize_text(text: str):

    text = str(
        text or ""
    ).lower()

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# GET IMPORTANT WORDS
# =========================================================

def get_keywords(text: str):

    normalized = normalize_text(
        text
    )

    words = normalized.split()

    keywords = []

    for word in words:

        if (
            len(word) >= 2
            and word not in STOP_WORDS
        ):

            keywords.append(
                word
            )

    return keywords


# =========================================================
# FACULTY INFORMATION SCORE
# =========================================================

def calculate_faculty_score(
    question: str,
    item: dict
):

    question_text = normalize_text(
        question
    )

    title = normalize_text(
        item.get(
            "title",
            ""
        )
    )

    content = normalize_text(
        item.get(
            "content",
            ""
        )
    )

    category = normalize_text(
        item.get(
            "category",
            ""
        )
    )

    question_keywords = get_keywords(
        question
    )

    score = 0


    # =====================================================
    # TITLE DIRECT MATCH
    # =====================================================

    if (
        title
        and title in question_text
    ):

        score += 100


    # =====================================================
    # QUESTION DIRECTLY APPEARS IN TITLE
    # =====================================================

    if (
        question_text
        and question_text in title
    ):

        score += 100


    # =====================================================
    # KEYWORD MATCHING
    # =====================================================

    for keyword in question_keywords:

        if keyword in title:

            score += 12

        if keyword in content:

            score += 6

        if keyword in category:

            score += 3


    # =====================================================
    # AI / ARTIFICIAL INTELLIGENCE ALIAS
    # =====================================================

    if (
        (
            re.search(
                r"\bai\b",
                question_text
            )
            or
            "artificial intelligence"
            in question_text
        )
        and
        (
            re.search(
                r"\bai\b",
                title
            )
            or
            "artificial intelligence"
            in title
            or
            re.search(
                r"\bai\b",
                content
            )
            or
            "artificial intelligence"
            in content
        )
    ):

        score += 15


    return score


# =========================================================
# SEARCH FACULTY DATABASE
# =========================================================

def search_faculty_information(
    question: str
):

    try:

        information = (
            get_faculty_information()
            or []
        )

    except Exception as error:

        print(
            "Faculty information retrieval error:",
            error
        )

        return []


    best_item = None
    best_score = 0


    for item in information:

        if not isinstance(
            item,
            dict
        ):

            continue


        score = calculate_faculty_score(
            question,
            item
        )


        if score > best_score:

            best_score = score
            best_item = item


    # =====================================================
    # REQUIRE A MEANINGFUL MATCH
    # =====================================================

    if (
        best_item is None
        or best_score < 10
    ):

        return []


    title = str(
        best_item.get(
            "title",
            ""
        )
    ).strip()


    content = str(
        best_item.get(
            "content",
            ""
        )
    ).strip()


    if not content:

        return []


    # Put title + content together so clean_answer()
    # can extract date, time and venue correctly.

    if title:

        result_text = (
            title
            + ". "
            + content
        )

    else:

        result_text = content


    return [
        result_text
    ]


# =========================================================
# MAIN RETRIEVAL AGENT
# =========================================================

def retrieve_knowledge(
    question: str
):

    # =====================================================
    # 1. FACULTY DATABASE FIRST
    # =====================================================

    faculty_results = (
        search_faculty_information(
            question
        )
    )


    if faculty_results:

        return faculty_results


    # =====================================================
    # 2. UNIVERSITY PDF / RAG
    # =====================================================

    try:

        results = search_knowledge(
            question,
            top_k=1
        )

    except Exception as error:

        print(
            "RAG retrieval error:",
            error
        )

        return []


    return results or []