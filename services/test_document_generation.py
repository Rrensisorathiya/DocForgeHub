from services.document_generator import generate_document

template_json = {
    "sections": [
        "Purpose",
        "Scope",
        "Roles & Responsibilities",
        "Process Steps",
        "Compliance Requirements"
    ]
}

metadata = {
    "company_name": "Turabit Technologies",
    "industry": "SaaS",
    "version": "1.0",
    "owner": "HR Department"
}

user_responses = {
    "purpose": "Define structured onboarding process",
    "scope": "All new employees",
    "tools_used": "HRMS, Slack, Email"
}

result = generate_document(
    document_type="SOP",
    department="HR & People Operations",
    template_json=template_json,
    metadata=metadata,
    user_responses=user_responses
)

print(result)
