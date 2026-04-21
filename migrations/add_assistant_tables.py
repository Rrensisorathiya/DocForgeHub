"""
migrations/add_assistant_tables.py
Run: python3 migrations/add_assistant_tables.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_connection

def create_tables():
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS assistant_threads (
            thread_id    VARCHAR(64) PRIMARY KEY,
            user_id      VARCHAR(64) DEFAULT 'anonymous',
            industry     VARCHAR(100),
            department   VARCHAR(100),
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS assistant_messages (
            id           SERIAL PRIMARY KEY,
            thread_id    VARCHAR(64) REFERENCES assistant_threads(thread_id) ON DELETE CASCADE,
            role         VARCHAR(20) NOT NULL,
            content      TEXT NOT NULL,
            intent       VARCHAR(20),
            citations    JSONB DEFAULT '[]',
            evidence_score FLOAT,
            trace_id     VARCHAR(64),
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS assistant_tickets (
            id                SERIAL PRIMARY KEY,
            thread_id         VARCHAR(64) REFERENCES assistant_threads(thread_id),
            notion_ticket_id  VARCHAR(100),
            notion_url        VARCHAR(500),
            question          TEXT NOT NULL,
            status            VARCHAR(30) DEFAULT 'open',
            priority          VARCHAR(20) DEFAULT 'medium',
            department        VARCHAR(100),
            assigned_owner    VARCHAR(100),
            evidence_score    FLOAT,
            sources_tried     JSONB DEFAULT '[]',
            conversation_summary TEXT,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at       TIMESTAMP
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_thread ON assistant_messages(thread_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tickets_thread  ON assistant_tickets(thread_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status  ON assistant_tickets(status)")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ assistant_threads, assistant_messages, assistant_tickets — created!")

if __name__ == "__main__":
    create_tables()
    
# """
# migrations/add_assistant_tables.py
# Run: python3 migrations/add_assistant_tables.py
# """
# import sys, os
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from db import get_connection

# def create_tables():
#     conn = get_connection()
#     cur  = conn.cursor()

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS assistant_threads (
#             thread_id    VARCHAR(64) PRIMARY KEY,
#             user_id      VARCHAR(64) DEFAULT 'anonymous',
#             industry     VARCHAR(100),
#             department   VARCHAR(100),
#             created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )
#     """)

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS assistant_messages (
#             id           SERIAL PRIMARY KEY,
#             thread_id    VARCHAR(64) REFERENCES assistant_threads(thread_id) ON DELETE CASCADE,
#             role         VARCHAR(20) NOT NULL,
#             content      TEXT NOT NULL,
#             intent       VARCHAR(20),
#             citations    JSONB DEFAULT '[]',
#             evidence_score FLOAT,
#             trace_id     VARCHAR(64),
#             created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )
#     """)

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS assistant_tickets (
#             id                SERIAL PRIMARY KEY,
#             thread_id         VARCHAR(64) REFERENCES assistant_threads(thread_id),
#             notion_ticket_id  VARCHAR(100),
#             notion_url        VARCHAR(500),
#             question          TEXT NOT NULL,
#             status            VARCHAR(30) DEFAULT 'open',
#             priority          VARCHAR(20) DEFAULT 'medium',
#             department        VARCHAR(100),
#             assigned_owner    VARCHAR(100),
#             evidence_score    FLOAT,
#             sources_tried     JSONB DEFAULT '[]',
#             conversation_summary TEXT,
#             created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             resolved_at       TIMESTAMP
#         )
#     """)

#     cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_thread ON assistant_messages(thread_id)")
#     cur.execute("CREATE INDEX IF NOT EXISTS idx_tickets_thread  ON assistant_tickets(thread_id)")
#     cur.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status  ON assistant_tickets(status)")

#     conn.commit()
#     cur.close()
#     conn.close()
#     print("✅ assistant_threads, assistant_messages, assistant_tickets — created!")

# if __name__ == "__main__":
#     create_tables()