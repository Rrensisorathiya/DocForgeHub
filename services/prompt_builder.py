# services/prompt_builder.py

import json
from utils.logger import setup_logger

logger = setup_logger(__name__)

LENGTH_INSTRUCTIONS = {
    "short": (
        "DOCUMENT LENGTH: SHORT (1 page / 400-600 words).\n"
        "- Be concise and direct\n"
        "- Only essential sections\n"
        "- Total output must not exceed 600 words"
    ),
    "medium": (
        "DOCUMENT LENGTH: MEDIUM (4-8 pages / 2000-4000 words).\n"
        "- Cover main sections with clear substantive content\n"
        "- Each section: 1-3 paragraphs or structured table/list\n"
        "- Total output: 2000-4000 words"
    ),
    "long": (
        "DOCUMENT LENGTH: LONG (35-40 pages / 15000+ words).\n"
        "- Write MINIMUM 200 words per section\n"
        "- Every section MUST include:\n"
        "  * Policy Statement (2-3 sentences)\n"
        "  * Scope & Applicability\n"
        "  * Detailed Procedures (numbered steps)\n"
        "  * Roles & Responsibilities\n"
        "  * Compliance Requirements\n"
        "  * Quick Reference Checklist\n"
        "- Use ### sub-sections under every ## section\n"
        "- Include tables where relevant\n"
        "- NEVER skip or summarize any section\n"
        "- NEVER stop before completing ALL sections\n"
        "- Total output MUST be 15000+ words"
    ),
}


def build_document_prompt(
    document_type: str,
    department: str,
    template_json: dict,
    metadata: dict,
    user_responses: dict
):
    # Determine document length based on metadata length field if present, otherwise default to "medium"
    doc_length = metadata.get("length", "medium") if isinstance(metadata, dict) else "medium"
    length_instructions = LENGTH_INSTRUCTIONS.get(doc_length, LENGTH_INSTRUCTIONS["medium"])

    prompt = f"""
You are generating a professional {document_type} document for the {department} department.

STRICT RULES:
- Follow the provided template structure exactly.
- Use metadata and user responses accurately.
- Do NOT invent missing data.
- Maintain enterprise tone.
- Return clean formatted markdown.

====================
DOCUMENT LENGTH REQUIREMENTS:
====================
{length_instructions}

====================
TEMPLATE STRUCTURE:
====================
{json.dumps(template_json, indent=2)}

====================
METADATA:
====================
{json.dumps(metadata, indent=2)}

====================
USER INPUT:
====================
{json.dumps(user_responses, indent=2)}

====================
INSTRUCTIONS:
====================
1. Generate the complete document following ALL template sections provided above.
2. Match the specified document length: {doc_length.upper()}
3. For short documents (1 page): Include only essential sections
4. For medium documents (4-8 pages): Cover all sections with standard detail
5. For long documents (35-40 pages): Include maximum detail with all subsections
6. Adjust content volume based on length requirements, not by skipping sections.
"""

    return prompt
