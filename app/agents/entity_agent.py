import re


def extract_entities(question: str):

    entities = {}

    # Date
    dates = re.findall(
        r"\b\d{1,2}\s+"
        r"(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"\s+\d{4}\b",
        question,
        re.IGNORECASE
    )

    if dates:
        entities["date"] = dates

    # Room
    rooms = re.findall(
        r"\bRoom\s+[A-Z]-?\d+\b",
        question,
        re.IGNORECASE
    )

    if rooms:
        entities["room"] = rooms

    # Department
    departments = [
        "computer science",
        "information technology",
        "examination",
        "admission",
        "accounts",
        "placement",
        "library"
    ]

    found_departments = []

    for department in departments:
        if department in question.lower():
            found_departments.append(department)

    if found_departments:
        entities["department"] = found_departments

    return entities