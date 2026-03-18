"""
Seed script - loads new_content.json, new_question_answer.py, new_metadata.json into PostgreSQL
Run: python3 migrations/seed_from_json.py
     python3 migrations/seed_from_json.py --reset   # wipe + reseed
"""
import json
import sys
import os
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_connection

def get_sections(dept_obj, doc_type):
    """
    Reads the sections list from the documents key.
    """
    sections = dept_obj.get("documents", {}).get(doc_type, {}).get("sections",[])
    return [s for s in sections if isinstance(s, str)]


def seed_templates(cur, content_data):
    print("\n[1] Seeding templates from new_content.json...")
    count = 0
    skipped = 0

    for dept_obj in content_data:
        dept = dept_obj.get("department")
        container = dept_obj.get("documents", {})

        for doc_type, doc_content in container.items():
            sections = get_sections(dept_obj, doc_type)
            structure = {
                "sections": sections,
                "total_sections": len(sections),
                "industry": dept_obj.get("industry", "SaaS"),
                "governance_level": dept_obj.get("governance_level", "Enterprise"),
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
    print("\n[2] Seeding questionnaires from new_Question_Answer.py...")

    if isinstance(qa_data, dict):
        print("  ❌ Question_Answer data is in OLD dict format.")
        return 0

    count = 0

    for entry in qa_data:
        dept = entry.get("department", "").strip()
        if not dept:
            continue

        common_qs   = entry.get("common_questions",[])
        metadata_qs = entry.get("metadata_questions",[])
        doc_qs_map  = entry.get("document_questions", {})

        for doc_type, doc_data in doc_qs_map.items():
            questions =[]
            
            # Extract questions from new format (dict with document_specs, auto_sections, questions)
            # or old format (list of questions directly)
            if isinstance(doc_data, dict):
                doc_specific_qs = doc_data.get('questions', [])
                doc_specs = doc_data.get('document_specs', {})
                auto_sections = doc_data.get('auto_sections', [])
            else:
                # Old format: doc_data is a list
                doc_specific_qs = doc_data
                doc_specs = {}
                auto_sections = []

            # 1. Common questions
            for q in common_qs:
                q_copy = q.copy()
                q_copy['category'] = 'common'
                questions.append(q_copy)

            # 2. Metadata questions
            for q in metadata_qs:
                q_copy = q.copy()
                q_copy['category'] = 'metadata'
                questions.append(q_copy)

            # 3. Document-type-specific questions
            for q in doc_specific_qs:
                q_copy = q.copy()
                q_copy['category'] = 'document_type_specific'
                questions.append(q_copy)
            
            # 4. Add document specifications and auto-sections as metadata
            if doc_specs or auto_sections:
                questions.append({
                    'id': '_document_specs',
                    'category': 'metadata',
                    'document_specs': doc_specs,
                    'auto_sections': auto_sections
                })

            cur.execute("""
                INSERT INTO questionnaires (document_type, department, questions, version)
                VALUES (%s, %s, %s, '1.0')
                ON CONFLICT (department, document_type) DO UPDATE
                SET questions   = EXCLUDED.questions,
                    updated_at  = CURRENT_TIMESTAMP
            """, (doc_type, dept, json.dumps(questions)))
            count += 1

    print(f"  ✅ {count} questionnaires seeded")
    return count


def seed_departments(cur, content_data):
    print("\n[3] Seeding departments...")
    inserted = 0
    for dept_obj in content_data:
        dept = dept_obj.get("department", "").strip()
        if dept:
            cur.execute(
                "INSERT INTO departments (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                (dept,)
            )
            if cur.rowcount:
                inserted += 1
    print(f"  ✅ {inserted} new / {len(content_data) - inserted} already existed")


def seed_document_types(cur, content_data):
    print("\n[4] Seeding document_types...")
    seen     = set()
    inserted = 0
    for dept_obj in content_data:
        for doc_type in dept_obj.get("documents", {}).keys():
            if doc_type in seen:
                continue
            seen.add(doc_type)
            cur.execute(
                "INSERT INTO document_types (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                (doc_type,)
            )
            if cur.rowcount:
                inserted += 1
    print(f"  ✅ {inserted} new / {len(seen) - inserted} already existed")


def seed_metadata(cur, metadata_data):
    """
    TODO: Insert logic for new_metadata.json
    I noticed you have a 'document_metadata' table in your database.
    If you provide the JSON structure, I can write the exact SQL query here.
    """
    print("\n[5] Seeding document metadata from new_metadata.json...")
    
    count = 0
    # Example loop (update this to match your new_metadata.json structure & table columns):
    # for meta in metadata_data:
    #     cur.execute("""
    #         INSERT INTO document_metadata (column1, column2) VALUES (%s, %s)
    #     """, (meta['key1'], meta['key2']))
    #     count += 1

    print(f"  ✅ {count} metadata entries seeded (NOTE: update seed_metadata function)")
    return count


def reset_tables(cur):
    """TRUNCATE all seed-managed tables for a clean reseed."""
    print("\n[0] --reset: truncating seed tables...")
    # Added document_metadata to the truncation list based on your schema
    for tbl in["document_metadata", "questionnaires", "templates", "document_types", "departments"]:
        try:
            cur.execute(f"TRUNCATE TABLE {tbl} RESTART IDENTITY CASCADE")
            print(f"  🗑️  {tbl} cleared")
        except Exception as e:
            print(f"  ⚠️  Could not clear {tbl} (might not exist yet)")


def main():
    parser = argparse.ArgumentParser(description="Seed DocForgeHub database from JSON files.")
    parser.add_argument("--reset", action="store_true",
                        help="TRUNCATE seed tables before inserting (clean reseed).")
    args = parser.parse_args()

    print("=" * 55)
    print("  DocForgeHub — Seed from NEW JSON Files")
    print("=" * 55)

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # UPDATED FILE PATHS
    content_path  = os.path.join(base, "Schema", "new_content.json")
    qa_path       = os.path.join(base, "Schema", "new_Question_Answer.py")
    metadata_path = os.path.join(base, "Schema", "new_metadata.json")

    # Check existence
    for path in[content_path, qa_path, metadata_path]:
        if not os.path.exists(path):
            print(f"❌ Not found: {path}")
            sys.exit(1)

    # Load JSON files
    with open(content_path) as f:
        content_data = json.load(f)
    with open(qa_path) as f:
        qa_data = json.load(f)
    with open(metadata_path) as f:
        metadata_data = json.load(f)

    print(f"\n✅ Loaded new_content.json        — {len(content_data)} departments")
    print(f"✅ Loaded new_question_answer.py — {len(qa_data)} entries")
    print(f"✅ Loaded new_metadata.json        — {len(metadata_data)} entries")

    conn = get_connection()
    cur  = conn.cursor()

    try:
        if args.reset:
            reset_tables(cur)

        seed_departments(cur, content_data)
        seed_document_types(cur, content_data)
        seed_templates(cur, content_data)
        seed_questionnaires(cur, qa_data)
        seed_metadata(cur, metadata_data)  # Added the new metadata call

        conn.commit()

        # Quick verification
        print("\n[✓] Verification:")
        for table in ["departments", "document_types", "templates", "questionnaires"]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            actual = cur.fetchone()[0]
            print(f"  ✅ {table:<20} {actual:>4} rows")

    except Exception as exc:
        conn.rollback()
        print(f"\n❌ Seeding failed — rolled back.\n   {exc}")
        raise
    finally:
        cur.close()
        conn.close()

    print("\n" + "=" * 55)
    print("  ✅ All done! Database fully seeded with new files.")
    print("=" * 55)


if __name__ == "__main__":
    main()

#------------------------------------------------------------------------

# """
# Seed script - loads content.json, Question_Answer.json into PostgreSQL
# Run: python3 migrations/seed_from_json.py
# """
# import json
# import sys
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from db import get_connection

# def get_sections(dept_obj, doc_type):
#     """Handle both 'templates' and 'documents' keys, both 'sections' and 'topics' keys"""
#     container = dept_obj.get("templates") or dept_obj.get("documents", {})
#     doc = container.get(doc_type, {})
#     sections = doc.get("sections") or doc.get("topics", [])
    
#     # Extract only string sections (skip metadata_ref dicts)
#     clean = []
#     for s in sections:
#         if isinstance(s, str):
#             clean.append(s)
#         elif isinstance(s, dict):
#             # Get nested list items (e.g. "HR & People Operations Processes": [...])
#             for key, val in s.items():
#                 if key == "section":
#                     continue  # skip Document Metadata block
#                 if isinstance(val, list):
#                     clean.extend([v for v in val if isinstance(v, str)])
#                 elif isinstance(val, str):
#                     clean.append(f"{key}: {val}")
#     return clean


# def seed_templates(cur, content_data):
#     print("\n[1] Seeding templates from content.json...")
#     count = 0
#     skipped = 0

#     for dept_obj in content_data:
#         dept = dept_obj.get("department")
#         container = dept_obj.get("templates") or dept_obj.get("documents", {})

#         for doc_type, doc_content in container.items():
#             sections = get_sections(dept_obj, doc_type)
#             structure = {
#                 "sections": sections,
#                 "total_sections": len(sections)
#             }

#             cur.execute("""
#                 INSERT INTO templates (department, document_type, structure, version, is_active)
#                 VALUES (%s, %s, %s, '1.0', TRUE)
#                 ON CONFLICT (department, document_type) DO UPDATE
#                 SET structure = EXCLUDED.structure,
#                     updated_at = CURRENT_TIMESTAMP
#             """, (dept, doc_type, json.dumps(structure)))

#             if cur.rowcount > 0:
#                 count += 1
#             else:
#                 skipped += 1

#     print(f"  ✅ {count} templates seeded, {skipped} skipped (already exist)")
#     return count


# def seed_questionnaires(cur, qa_data):
#     print("\n[2] Seeding questionnaires from Question_Answer.json...")
#     count = 0

#     schema = qa_data.get("user_qa_schema", {})
#     question_types = schema.get("question_types", {})

#     common_questions = question_types.get("common_questions", {}).get("questions", [])
#     doc_type_questions = question_types.get("document_type_specific_questions", {})
#     dept_questions = question_types.get("department_specific_questions", {})

#     departments = [
#         "HR & People Operations", "Legal & Compliance", "Sales & Customer-Facing",
#         "Engineering & Operations", "Product & Design", "Marketing & Content",
#         "Finance & Operations", "Partnership & Alliances", "IT & Internal Systems",
#         "Platform & Infrastructure Operation", "Data & Analytics",
#         "QA & Testing", "Security & Information Assurance"
#     ]

#     doc_types = [
#         "SOP", "Policy", "Proposal", "SOW", "Incident Report",
#         "FAQ", "Runbook", "Playbook", "RCA", "SLA", "Change Management", "Handbook"
#     ]

#     for dept in departments:
#         for doc_type in doc_types:
#             questions = []

#             # 1. Common questions (for all)
#             for q in common_questions:
#                 questions.append({
#                     "id": q.get("id"),
#                     "question": q.get("question", "").replace("{department}", dept),
#                     "type": q.get("type"),
#                     "required": q.get("required", False),
#                     "options": q.get("options", []),
#                     "placeholder": q.get("placeholder", ""),
#                     "used_in_prompt": q.get("used_in_prompt", ""),
#                     "category": "common"
#                 })

#             # 2. Document type specific questions
#             for q in doc_type_questions.get(doc_type, []):
#                 questions.append({
#                     "id": q.get("id"),
#                     "question": q.get("question", ""),
#                     "type": q.get("type"),
#                     "required": q.get("required", False),
#                     "options": q.get("options", []),
#                     "placeholder": q.get("placeholder", ""),
#                     "used_in_prompt": q.get("used_in_prompt", ""),
#                     "category": "document_type_specific"
#                 })

#             # 3. Department specific questions
#             for q in dept_questions.get(dept, []):
#                 questions.append({
#                     "id": q.get("id"),
#                     "question": q.get("question", ""),
#                     "type": q.get("type"),
#                     "required": q.get("required", False),
#                     "options": q.get("options", []),
#                     "placeholder": q.get("placeholder", ""),
#                     "used_in_prompt": q.get("used_in_prompt", ""),
#                     "category": "department_specific"
#                 })

#             cur.execute("""
#                 INSERT INTO questionnaires (document_type, department, questions, version)
#                 VALUES (%s, %s, %s, '1.0')
#                 ON CONFLICT (department, document_type) DO UPDATE
#                 SET questions = EXCLUDED.questions,
#                     updated_at = CURRENT_TIMESTAMP
#             """, (doc_type, dept, json.dumps(questions)))
#             count += 1

#     print(f"  ✅ {count} questionnaires seeded ({len(departments)} depts × {len(doc_types)} doc types)")
#     return count


# def seed_departments(cur):
#     print("\n[3] Seeding departments...")
#     departments = [
#         "HR & People Operations", "Legal & Compliance", "Sales & Customer-Facing",
#         "Engineering & Operations", "Product & Design", "Marketing & Content",
#         "Finance & Operations", "Partnership & Alliances", "IT & Internal Systems",
#         "Platform & Infrastructure Operation", "Data & Analytics",
#         "QA & Testing", "Security & Information Assurance"
#     ]
#     for d in departments:
#         cur.execute("INSERT INTO departments (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (d,))
#     print(f"  ✅ {len(departments)} departments seeded")


# def seed_document_types(cur):
#     print("\n[4] Seeding document types...")
#     doc_types = [
#         "SOP", "Policy", "Proposal", "SOW", "Incident Report",
#         "FAQ", "Runbook", "Playbook", "RCA", "SLA", "Change Management", "Handbook"
#     ]
#     for dt in doc_types:
#         cur.execute("INSERT INTO document_types (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (dt,))
#     print(f"  ✅ {len(doc_types)} document types seeded")


# def main():
#     print("=" * 55)
#     print("  DocForgeHub — Seed from JSON Files")
#     print("=" * 55)

#     # Load JSON files
#     base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#     content_path = os.path.join(base, "Schema", "content.json")
#     qa_path      = os.path.join(base, "Schema", "Question_Answer.json")

#     if not os.path.exists(content_path):
#         print(f"❌ Not found: {content_path}")
#         sys.exit(1)
#     if not os.path.exists(qa_path):
#         print(f"❌ Not found: {qa_path}")
#         sys.exit(1)

#     with open(content_path) as f:
#         content_data = json.load(f)
#     with open(qa_path) as f:
#         qa_data = json.load(f)

#     print(f"\n✅ Loaded content.json — {len(content_data)} departments")
#     print(f"✅ Loaded Question_Answer.json")

#     conn = get_connection()
#     cur  = conn.cursor()

#     seed_departments(cur)
#     seed_document_types(cur)
#     seed_templates(cur, content_data)
#     seed_questionnaires(cur, qa_data)

#     conn.commit()
#     cur.close()
#     conn.close()

#     print("\n" + "=" * 55)
#     print("  ✅ All done! Database fully seeded.")
#     print("=" * 55)


# if __name__ == "__main__":
#     main()