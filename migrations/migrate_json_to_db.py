"""
Run this ONCE to create/update all tables.

Usage:
    python migrations/migrate_json_to_db.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_connection
from utils.logger import setup_logger

logger = setup_logger(__name__)


def run_migrations():
    conn = get_connection()
    cursor = conn.cursor()

    print("Running migrations...")

    # ----------------------------------------
    # Templates Table
    # ----------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id SERIAL PRIMARY KEY,
            document_type VARCHAR(255) NOT NULL,
            department VARCHAR(255) NOT NULL,
            structure JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ templates table ready")

    # ----------------------------------------
    # Questionnaires Table
    # ----------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questionnaires (
            id SERIAL PRIMARY KEY,
            document_type VARCHAR(255) NOT NULL,
            department VARCHAR(255) NOT NULL,
            questions JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ questionnaires table ready")

    # ----------------------------------------
    # Generated Documents Table
    # ----------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generated_documents (
            id SERIAL PRIMARY KEY,
            document_type VARCHAR(255) NOT NULL,
            department VARCHAR(255) NOT NULL,
            industry VARCHAR(255),
            question_answers JSONB,
            generated_content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("✅ generated_documents table ready")

    conn.commit()
    cursor.close()
    conn.close()

    print("\n✅ All migrations completed successfully.")


if __name__ == "__main__":
    run_migrations()
# import json
# import psycopg2
# import os
# from dotenv import load_dotenv


# # ==========================================
# # LOAD ENV VARIABLES
# # ==========================================
# load_dotenv()

# DB_CONFIG = {
#     "host": os.getenv("DB_HOST"),
#     "database": os.getenv("DB_NAME"),
#     "user": os.getenv("DB_USER"),
#     "password": os.getenv("DB_PASSWORD"),
#     "port": os.getenv("DB_PORT")
# }


# # ==========================================
# # DATABASE CONNECTION
# # ==========================================
# def get_connection():
#     return psycopg2.connect(**DB_CONFIG)


# # ==========================================
# # LOAD JSON FILE
# # ==========================================
# def load_json(path):
#     with open(path, "r", encoding="utf-8") as f:
#         return json.load(f)


# # ==========================================
# # SYNC DOCUMENT TYPES FROM content.json
# # ==========================================
# def insert_document_types(cursor, content_json):

#     document_types_set = set()

#     if isinstance(content_json, list):
#         for item in content_json:
#             templates = item.get("templates", {})
#             for doc_type in templates.keys():
#                 document_types_set.add(doc_type)

#     elif isinstance(content_json, dict):
#         for doc_type in content_json.keys():
#             document_types_set.add(doc_type)

#     else:
#         print("❌ Unsupported content.json structure")
#         return

#     for doc_type in document_types_set:
#         cursor.execute("""
#             INSERT INTO document_types (name)
#             VALUES (%s)
#             ON CONFLICT (name) DO NOTHING;
#         """, (doc_type,))

#     print("✅ Document types synced")


# # ==========================================
# # INSERT METADATA (GLOBAL)
# # ==========================================
# def insert_metadata(cursor, metadata_json):

#     cursor.execute("""
#         INSERT INTO documents
#         (document_type_id, title, department, content, metadata)
#         VALUES (NULL, 'GLOBAL_METADATA', 'SYSTEM', '{}'::jsonb, %s)
#     """, (json.dumps(metadata_json),))

#     print("✅ Metadata inserted")


# # ==========================================
# # INSERT TEMPLATES
# # ==========================================
# def insert_templates(cursor, content_json):

#     if isinstance(content_json, list):

#         for item in content_json:
#             department = item.get("department", "General")
#             templates = item.get("templates", {})

#             for doc_type, data in templates.items():
#                 insert_template_row(cursor, doc_type, department, data)

#     elif isinstance(content_json, dict):

#         for doc_type, data in content_json.items():
#             insert_template_row(cursor, doc_type, "General", data)

#     else:
#         print("❌ Unsupported content.json format")
#         return

#     print("✅ Templates inserted")


# def insert_template_row(cursor, doc_type, department, data):

#     cursor.execute(
#         "SELECT id FROM document_types WHERE name=%s",
#         (doc_type,)
#     )
#     result = cursor.fetchone()

#     if not result:
#         print(f"⚠ Unknown document type skipped: {doc_type}")
#         return

#     doc_type_id = result[0]

#     cursor.execute("""
#         INSERT INTO documents
#         (document_type_id, title, department, content)
#         VALUES (%s, %s, %s, %s)
#     """, (
#         doc_type_id,
#         doc_type,
#         department,
#         json.dumps(data)
#     ))


# # ==========================================
# # INSERT QUESTIONNAIRES
# # ==========================================
# def insert_questionnaires(cursor, qa_json):

#     if isinstance(qa_json, list):

#         for item in qa_json:
#             department = item.get("department", "General")
#             templates = item.get("templates", {})

#             for doc_type, schema in templates.items():
#                 insert_questionnaire_row(cursor, doc_type, department, schema)

#     elif isinstance(qa_json, dict):

#         for doc_type, schema in qa_json.items():
#             insert_questionnaire_row(cursor, doc_type, "General", schema)

#     else:
#         print("❌ Unsupported Question_Answer.json format")
#         return

#     print("✅ Questionnaires inserted")


# def insert_questionnaire_row(cursor, doc_type, department, schema):

#     cursor.execute(
#         "SELECT id FROM document_types WHERE name=%s",
#         (doc_type,)
#     )
#     result = cursor.fetchone()

#     if not result:
#         print(f"⚠ Unknown questionnaire type skipped: {doc_type}")
#         return

#     doc_type_id = result[0]

#     cursor.execute("""
#         INSERT INTO questionnaires
#         (document_type_id, department, schema)
#         VALUES (%s, %s, %s)
#     """, (
#         doc_type_id,
#         department,
#         json.dumps(schema)
#     ))


# # ==========================================
# # MAIN FUNCTION
# # ==========================================
# def main():

#     print("🚀 Starting migration...")

#     conn = get_connection()
#     cursor = conn.cursor()

#     try:
#         content_json = load_json("Schemas/content.json")
#         metadata_json = load_json("Schemas/metadata.json")
#         qa_json = load_json("Schemas/Question_Answer.json")

#         insert_document_types(cursor, content_json)
#         insert_metadata(cursor, metadata_json)
#         insert_templates(cursor, content_json)
#         insert_questionnaires(cursor, qa_json)

#         conn.commit()
#         print("🎉 Migration completed successfully!")

#     except Exception as e:
#         conn.rollback()
#         print("❌ Migration failed:")
#         print(e)

#     finally:
#         cursor.close()
#         conn.close()


# # ==========================================
# # RUN
# # ==========================================
# if __name__ == "__main__":
#     main()


# # import json
# # import psycopg2
# # import os
# # from dotenv import load_dotenv

# # # Load env
# # load_dotenv()

# # DB_CONFIG = {
# #     "host": os.getenv("DB_HOST"),
# #     "database": os.getenv("DB_NAME"),
# #     "user": os.getenv("DB_USER"),
# #     "password": os.getenv("DB_PASSWORD"),
# #     "port": os.getenv("DB_PORT")
# # }


# # def get_connection():
# #     return psycopg2.connect(**DB_CONFIG)


# # def load_json(file_path):
# #     with open(file_path, "r", encoding="utf-8") as f:
# #         return json.load(f)


# # def insert_document_types(cursor):
# #     types = ["SOP", "Policy", "Proposal", "Handbook"]
# #     for t in types:
# #         cursor.execute("""
# #             INSERT INTO document_types (name)
# #             VALUES (%s)
# #             ON CONFLICT (name) DO NOTHING;
# #         """, (t,))


# # def insert_metadata_schema(cursor, metadata_json):
# #     cursor.execute("""
# #         INSERT INTO documents (document_type_id, department, content, metadata)
# #         VALUES (NULL, 'GLOBAL_METADATA', '{}'::jsonb, %s)
# #     """, (json.dumps(metadata_json),))


# # def insert_templates(cursor, content_json):
# #     for doc_type, data in content_json.items():

# #         cursor.execute("SELECT id FROM document_types WHERE name=%s", (doc_type,))
# #         result = cursor.fetchone()

# #         if result:
# #             doc_type_id = result[0]
# #         else:
# #             continue

# #         cursor.execute("""
# #             INSERT INTO documents (document_type_id, department, content)
# #             VALUES (%s, %s, %s)
# #         """, (
# #             doc_type_id,
# #             "General",
# #             json.dumps(data)
# #         ))


# # def insert_questionnaires(cursor, qa_json):
# #     for doc_type, schema in qa_json.items():

# #         cursor.execute("SELECT id FROM document_types WHERE name=%s", (doc_type,))
# #         result = cursor.fetchone()

# #         if not result:
# #             continue

# #         doc_type_id = result[0]

# #         cursor.execute("""
# #             INSERT INTO questionnaires (document_type_id, department, schema)
# #             VALUES (%s, %s, %s)
# #         """, (
# #             doc_type_id,
# #             "General",
# #             json.dumps(schema)
# #         ))


# # def main():
# #     conn = get_connection()
# #     cursor = conn.cursor()

# #     print("🚀 Starting migration...")

# #     content_json = load_json("Schemas/content.json")
# #     metadata_json = load_json("Schemas/metadata.json")
# #     qa_json = load_json("Schemas/Question_Answer.json")

# #     insert_document_types(cursor)
# #     insert_metadata_schema(cursor, metadata_json)
# #     insert_templates(cursor, content_json)
# #     insert_questionnaires(cursor, qa_json)

# #     conn.commit()
# #     cursor.close()
# #     conn.close()

# #     print("✅ Migration completed successfully!")


# # if __name__ == "__main__":
# #     main()
