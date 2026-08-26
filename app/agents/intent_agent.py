def detect_intent(question: str):

    q = question.lower().strip()

    # =====================================================
    # TICKET / COMPLAINT
    # =====================================================

    complaint_words = [
        "problem",
        "issue",
        "complaint",
        "complain",
        "error",
        "not working",
        "unable",
        "can't",
        "cannot",
        "help me",
        "having trouble",
        "facing problem",
        "facing issue"
    ]

    if any(
        word in q
        for word in complaint_words
    ):

        if "exam" in q or "examination" in q or "timetable" in q:
            return "exam_issue"

        return "general_issue"

    # =====================================================
    # EXAMINATION
    # =====================================================

    if (
        "exam" in q
        or "examination" in q
        or "timetable" in q
    ):
        return "examination"

    # =====================================================
    # HOLIDAY
    # =====================================================

    if (
        "holiday" in q
        or "holidays" in q
    ):
        return "holiday"

    # =====================================================
    # FEES
    # =====================================================

    if (
        "fee" in q
        or "fees" in q
    ):
        return "fees"

    # =====================================================
    # ADMISSION
    # =====================================================

    if "admission" in q:
        return "admission"

    # =====================================================
    # PLACEMENT
    # =====================================================

    if "placement" in q:
        return "placement"

    # =====================================================
    # LIBRARY
    # =====================================================

    if "library" in q:
        return "library"

    # =====================================================
    # GENERAL
    # =====================================================

    return "general"