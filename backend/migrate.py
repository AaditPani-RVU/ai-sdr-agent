import sqlite3

conn = sqlite3.connect("sdr.db")
cur = conn.cursor()

migrations = [
    ("prospects", "sent_at", "DATETIME"),
    ("prospects", "followups_sent", "INTEGER DEFAULT 0 NOT NULL"),
    ("prospects", "gmail_thread_id", "VARCHAR(255)"),
    ("email_drafts", "subject_alt", "VARCHAR(500) DEFAULT ''"),
    # Week 4
    ("prospects", "booked_at", "DATETIME"),
    ("prospects", "calendly_event_url", "VARCHAR(500)"),
]

for table, col, definition in migrations:
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
        print(f"Added {table}.{col}")
    except Exception as e:
        print(f"Skipped {table}.{col}: {e}")

conn.commit()
conn.close()
print("Done")
