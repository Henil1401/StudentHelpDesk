# ==========================================
# FACULTY / DEPARTMENT ROUTING AGENT
# ==========================================

def route_to_faculty(intent: str):

    intent = str(intent).lower().strip()

    routing = {

        # Examination
        "examination":
            "Examination Department",

        "exam":
            "Examination Department",

        # Technical / Academic
        "technical":
            "Computer Science Department",

        "artificial intelligence":
            "Computer Science Department",

        "database":
            "Computer Science Department",

        "computer networks":
            "Computer Science Department",

        "cloud computing":
            "Computer Science Department",

        "software engineering":
            "Computer Science Department",

        # Finance
        "fees":
            "Accounts Department",

        "fee":
            "Accounts Department",

        # Admission
        "admission":
            "Admission Department",

        # Placement
        "placement":
            "Placement Department",

        # Library
        "library":
            "Library Department",

        # Holiday
        "holiday":
            "Academic Office",

        # General
        "general":
            "Student Services"
    }

    return routing.get(
        intent,
        "Student Services"
    )