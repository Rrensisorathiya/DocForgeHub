from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class DocumentGenerateRequest(BaseModel):
    industry: str = Field(..., example="SaaS")
    department: str = Field(..., example="HR & People Operations")
    document_type: str = Field(..., example="SOP")
    question_answers: Dict[str, Any] = Field(
        ...,
        example={
            "company_name": "TechFlow Solutions",
            "company_size": "51-200 (Medium)",
            "purpose": "Define structured onboarding process",
            "scope": "All new employees joining the company",
            "tools_used": ["BambooHR", "Slack", "Zoom"],
            "compliance_notes": "Must follow ISO 27001 guidelines",
        },
    )
# from pydantic import BaseModel, Field
# from typing import Dict, Any, Optional


# class DocumentGenerateRequest(BaseModel):
#     industry: str = Field(..., example="SaaS")
#     department: str = Field(..., example="HR & People Operations")
#     document_type: str = Field(..., example="SOP")
#     question_answers: Dict[str, Any] = Field(
#         ...,
#         example={
#             "purpose": "Define structured onboarding process",
#             "scope": "All new employees joining the company",
#             "tools_used": "HRMS, Slack, Email",
#             "compliance_notes": "Must follow ISO 27001 guidelines",
#         },
#     )


# class TemplateCreateRequest(BaseModel):
#     document_type: str = Field(..., example="SOP")
#     department: str = Field(..., example="HR & People Operations")
#     structure: Dict[str, Any] = Field(
#         ...,
#         example={
#             "sections": [
#                 "Purpose",
#                 "Scope",
#                 "Roles & Responsibilities",
#                 "Process Steps",
#                 "Compliance Requirements",
#             ]
#         },
#     )


# class TemplateUpdateRequest(BaseModel):
#     structure: Dict[str, Any] = Field(
#         ...,
#         example={
#             "sections": [
#                 "Purpose",
#                 "Scope",
#                 "Updated Process Steps",
#                 "Compliance Requirements",
#             ]
#         },
#     )


# class QuestionnaireCreateRequest(BaseModel):
#     document_type: str = Field(..., example="SOP")
#     department: str = Field(..., example="HR & People Operations")
#     questions: list = Field(
#         ...,
#         example=[
#             {"key": "purpose", "label": "What is the purpose of this document?"},
#             {"key": "scope", "label": "Who does this document apply to?"},
#             {"key": "tools_used", "label": "What tools or systems are involved?"},
#         ],
#     )

# from pydantic import BaseModel
# from typing import Dict, Any


# class DocumentGenerateRequest(BaseModel):
#     document_type: str
#     department: str
#     metadata: Dict[str, Any]
#     user_responses: Dict[str, Any]


# class DocumentGenerateResponse(BaseModel):
#     status: str
#     document: str
