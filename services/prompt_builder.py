# services/prompt_builder.py

import json


def build_document_prompt(
    document_type: str,
    department: str,
    template_json: dict,
    metadata: dict,
    user_responses: dict
):

    prompt = f"""
You are generating a professional {document_type} document for the {department} department.

STRICT RULES:
- Follow the provided template structure exactly.
- Use metadata and user responses accurately.
- Do NOT invent missing data.
- Maintain enterprise tone.
- Return clean formatted markdown.

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
Generate the full final document following the template sections.
"""

    return prompt
