import json
import re
from typing import Dict, Any, List

from services.langchain_service import generate_document_with_langchain
from services.template_repository import get_template_by_type
from services.questionnaire_repository import get_questionnaire_by_type


# --------------------------------------------------
# Utility: Clean Markdown Output
# --------------------------------------------------

def clean_markdown_output(text: str) -> str:
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    return text.strip()


# --------------------------------------------------
# Extract Sections from Template Structure
# --------------------------------------------------

def extract_sections(structure: Dict[str, Any]) -> List[str]:
    sections = []
    raw_sections = structure.get("sections", [])

    for section in raw_sections:
        if isinstance(section, str):
            sections.append(section)
        elif isinstance(section, dict):
            for parent, children in section.items():
                sections.append(parent)
                if isinstance(children, list):
                    sections.extend(children)

    return sections


# --------------------------------------------------
# Build Prompt for a Single Section
# --------------------------------------------------

def build_section_prompt(
    industry: str,
    department: str,
    document_type: str,
    section_name: str,
    question_answers: Dict[str, Any],
) -> str:
    answers_text = json.dumps(question_answers, indent=2)

    return f"""You are a senior SaaS documentation expert.

Generate ONLY the section titled: "{section_name}"

Document Type: {document_type}
Department: {department}
Industry: {industry}

Business Context (answers provided by user):
{answers_text}

Instructions:
- Write ONLY this section. Do not write other sections.
- Be detailed, structured, and professional.
- Use clean Markdown formatting.
- Do NOT wrap output in ```markdown``` code blocks.
- Do NOT include the document title or department header.
"""


# --------------------------------------------------
# Main Document Generator
# --------------------------------------------------

def generate_document(
    industry: str,
    department: str,
    document_type: str,
    question_answers: Dict[str, Any],
) -> str:

    # 1. Fetch Template
    template = get_template_by_type(document_type)
    if not template:
        raise ValueError(
            f"No template found for document type: '{document_type}'. "
            f"Please create a template first via POST /templates/"
        )

    # 2. Fetch Questionnaire (optional — used for context only)
    questionnaire = get_questionnaire_by_type(document_type)
    # questionnaire is optional — document can still generate without it

    # 3. Extract Sections from Template
    sections = extract_sections(template["structure"])

    if not sections:
        raise ValueError(
            f"Template for '{document_type}' has no sections defined. "
            f"Make sure your template structure has a 'sections' key."
        )

    # 4. Build Document Header
    final_document = f"# {document_type}\n\n"
    final_document += f"**Department:** {department} | **Industry:** {industry}\n\n"
    final_document += "---\n\n"

    # 5. Generate Each Section via LLM
    for section in sections:
        prompt = build_section_prompt(
            industry=industry,
            department=department,
            document_type=document_type,
            section_name=section,
            question_answers=question_answers,
        )

        section_content = generate_document_with_langchain(prompt)
        section_content = clean_markdown_output(section_content)

        final_document += f"## {section}\n\n"
        final_document += section_content + "\n\n---\n\n"

    return final_document.strip()
# import json
# import re
# from typing import Dict, Any, List
# from services.langchain_service import generate_document_with_langchain
# from services.template_repository import get_template_by_type
# from services.questionnaire_repository import get_questionnaire_by_type


# # --------------------------------------------------
# # Utility: Clean Markdown Output
# # --------------------------------------------------

# def clean_markdown_output(text: str) -> str:
#     if text.startswith("```"):
#         text = re.sub(r"^```[a-zA-Z]*", "", text)
#         text = re.sub(r"```$", "", text)
#     return text.strip()


# # --------------------------------------------------
# # Prompt Builder for Single Section
# # --------------------------------------------------

# def build_section_prompt(
#     industry: str,
#     department: str,
#     document_type: str,
#     section_name: str,
#     questionnaire_answers: Dict[str, Any],
# ) -> str:

#     answers_text = json.dumps(questionnaire_answers, indent=2)

#     prompt = f"""
# You are a senior SaaS documentation expert.

# Generate ONLY the section titled:

# {section_name}

# For a {document_type} document in the {department} department
# within the {industry} industry.

# Business Context:
# {answers_text}

# Instructions:
# - Write only this section.
# - Do not repeat other sections.
# - Be detailed and professional.
# - Use clean Markdown.
# - Do NOT include ```markdown tags.
# - Do NOT include document title.
# """

#     return prompt


# # --------------------------------------------------
# # Extract Sections from Template
# # --------------------------------------------------

# def extract_sections(template_structure: Dict[str, Any]) -> List[str]:
#     sections = []

#     raw_sections = template_structure.get("sections", [])

#     for section in raw_sections:
#         if isinstance(section, str):
#             sections.append(section)

#         elif isinstance(section, dict):
#             for parent, children in section.items():
#                 sections.append(parent)
#                 sections.extend(children)

#     return sections


# # --------------------------------------------------
# # Main Document Generator (Section-wise)
# # --------------------------------------------------

# def generate_document(
#     industry: str,
#     department: str,
#     document_type: str,
#     question_answers: Dict[str, Any],
# ) -> str:

#     # 1️⃣ Fetch Template
#     template = get_template_by_type(document_type)
#     if not template:
#         raise ValueError(f"Template not found: {document_typea}")

#     # 2️⃣ Fetch Questionnaire
#     questionnaire = get_questionnaire_by_type(document_type)
#     if not questionnaire:
#         raise ValueError(f"Questionnaire not found: {document_type}")

#     # 3️⃣ Extract Sections
#     sections = extract_sections(template["structure"])

#     final_document = f"# {document_type}\n\n"
#     final_document += f"## {department} Department\n\n---\n\n"

#     # 4️⃣ Generate Each Section Separately
#     for section in sections:
#         prompt = build_section_prompt(
#             industry=industry,
#             department=department,
#             document_type=document_type,
#             section_name=section,
#             questionnaire_answers=question_answers,
#         )

#         section_content = generate_document_with_langchain(prompt)
#         section_content = clean_markdown_output(section_content)

#         final_document += f"## {section}\n\n"
#         final_document += section_content + "\n\n---\n\n"

#     return final_document.strip()
