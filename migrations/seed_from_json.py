"""
Seed script - loads content.json, Question_Answer.json into PostgreSQL
Run: python3 migrations/seed_from_json.py
"""
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_connection

def get_sections(dept_obj, doc_type):
    """Handle both 'templates' and 'documents' keys, both 'sections' and 'topics' keys"""
    container = dept_obj.get("templates") or dept_obj.get("documents", {})
    doc = container.get(doc_type, {})
    sections = doc.get("sections") or doc.get("topics", [])
    
    # Extract only string sections (skip metadata_ref dicts)
    clean = []
    for s in sections:
        if isinstance(s, str):
            clean.append(s)
        elif isinstance(s, dict):
            # Get nested list items (e.g. "HR & People Operations Processes": [...])
            for key, val in s.items():
                if key == "section":
                    continue  # skip Document Metadata block
                if isinstance(val, list):
                    clean.extend([v for v in val if isinstance(v, str)])
                elif isinstance(val, str):
                    clean.append(f"{key}: {val}")
    return clean


def seed_templates(cur, content_data):
    print("\n[1] Seeding templates from content.json...")
    count = 0
    skipped = 0

    for dept_obj in content_data:
        dept = dept_obj.get("department")
        container = dept_obj.get("templates") or dept_obj.get("documents", {})

        for doc_type, doc_content in container.items():
            sections = get_sections(dept_obj, doc_type)
            structure = {
                "sections": sections,
                "total_sections": len(sections)
            }

            cur.execute("""
                INSERT INTO templates (department, document_type, structure, version, is_active)
                VALUES (%s, %s, %s, '1.0', TRUE)
                ON CONFLICT (department, document_type) DO UPDATE
                SET structure = EXCLUDED.structure,
                    updated_at = CURRENT_TIMESTAMP
            """, (dept, doc_type, json.dumps(structure)))

            if cur.rowcount > 0:
                count += 1
            else:
                skipped += 1

    print(f"  ✅ {count} templates seeded, {skipped} skipped (already exist)")
    return count


def seed_questionnaires(cur, qa_data):
    print("\n[2] Seeding questionnaires from Question_Answer.json...")
    count = 0

    schema = qa_data.get("user_qa_schema", {})
    question_types = schema.get("question_types", {})

    common_questions = question_types.get("common_questions", {}).get("questions", [])
    doc_type_questions = question_types.get("document_type_specific_questions", {})
    dept_questions = question_types.get("department_specific_questions", {})

    departments = [
        "HR & People Operations", "Legal & Compliance", "Sales & Customer-Facing",
        "Engineering & Operations", "Product & Design", "Marketing & Content",
        "Finance & Operations", "Partnership & Alliances", "IT & Internal Systems",
        "Platform & Infrastructure Operation", "Data & Analytics",
        "QA & Testing", "Security & Information Assurance"
    ]

    doc_types = [
        "SOP", "Policy", "Proposal", "SOW", "Incident Report",
        "FAQ", "Runbook", "Playbook", "RCA", "SLA", "Change Management", "Handbook"
    ]

    for dept in departments:
        for doc_type in doc_types:
            questions = []

            # 1. Common questions (for all)
            for q in common_questions:
                questions.append({
                    "id": q.get("id"),
                    "question": q.get("question", "").replace("{department}", dept),
                    "type": q.get("type"),
                    "required": q.get("required", False),
                    "options": q.get("options", []),
                    "placeholder": q.get("placeholder", ""),
                    "used_in_prompt": q.get("used_in_prompt", ""),
                    "category": "common"
                })

            # 2. Document type specific questions
            for q in doc_type_questions.get(doc_type, []):
                questions.append({
                    "id": q.get("id"),
                    "question": q.get("question", ""),
                    "type": q.get("type"),
                    "required": q.get("required", False),
                    "options": q.get("options", []),
                    "placeholder": q.get("placeholder", ""),
                    "used_in_prompt": q.get("used_in_prompt", ""),
                    "category": "document_type_specific"
                })

            # 3. Department specific questions
            for q in dept_questions.get(dept, []):
                questions.append({
                    "id": q.get("id"),
                    "question": q.get("question", ""),
                    "type": q.get("type"),
                    "required": q.get("required", False),
                    "options": q.get("options", []),
                    "placeholder": q.get("placeholder", ""),
                    "used_in_prompt": q.get("used_in_prompt", ""),
                    "category": "department_specific"
                })

            cur.execute("""
                INSERT INTO questionnaires (document_type, department, questions, version)
                VALUES (%s, %s, %s, '1.0')
                ON CONFLICT (department, document_type) DO UPDATE
                SET questions = EXCLUDED.questions,
                    updated_at = CURRENT_TIMESTAMP
            """, (doc_type, dept, json.dumps(questions)))
            count += 1

    print(f"  ✅ {count} questionnaires seeded ({len(departments)} depts × {len(doc_types)} doc types)")
    return count


def seed_departments(cur):
    print("\n[3] Seeding departments...")
    departments = [
        "HR & People Operations", "Legal & Compliance", "Sales & Customer-Facing",
        "Engineering & Operations", "Product & Design", "Marketing & Content",
        "Finance & Operations", "Partnership & Alliances", "IT & Internal Systems",
        "Platform & Infrastructure Operation", "Data & Analytics",
        "QA & Testing", "Security & Information Assurance"
    ]
    for d in departments:
        cur.execute("INSERT INTO departments (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (d,))
    print(f"  ✅ {len(departments)} departments seeded")


def seed_document_types(cur):
    print("\n[4] Seeding document types...")
    doc_types = [
        "SOP", "Policy", "Proposal", "SOW", "Incident Report",
        "FAQ", "Runbook", "Playbook", "RCA", "SLA", "Change Management", "Handbook"
    ]
    for dt in doc_types:
        cur.execute("INSERT INTO document_types (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (dt,))
    print(f"  ✅ {len(doc_types)} document types seeded")


def main():
    print("=" * 55)
    print("  DocForgeHub — Seed from JSON Files")
    print("=" * 55)

    # Load JSON files
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    content_path = os.path.join(base, "Schema", "content.json")
    qa_path      = os.path.join(base, "Schema", "Question_Answer.json")

    if not os.path.exists(content_path):
        print(f"❌ Not found: {content_path}")
        sys.exit(1)
    if not os.path.exists(qa_path):
        print(f"❌ Not found: {qa_path}")
        sys.exit(1)

    with open(content_path) as f:
        content_data = json.load(f)
    with open(qa_path) as f:
        qa_data = json.load(f)

    print(f"\n✅ Loaded content.json — {len(content_data)} departments")
    print(f"✅ Loaded Question_Answer.json")

    conn = get_connection()
    cur  = conn.cursor()

    seed_departments(cur)
    seed_document_types(cur)
    seed_templates(cur, content_data)
    seed_questionnaires(cur, qa_data)

    conn.commit()
    cur.close()
    conn.close()

    print("\n" + "=" * 55)
    print("  ✅ All done! Database fully seeded.")
    print("=" * 55)


if __name__ == "__main__":
    main()