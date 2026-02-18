from pydantic import BaseModel
from typing import Dict, Any


class DocumentGenerateRequest(BaseModel):
    document_type: str
    department: str
    metadata: Dict[str, Any]
    user_responses: Dict[str, Any]


class DocumentGenerateResponse(BaseModel):
    status: str
    document: str
