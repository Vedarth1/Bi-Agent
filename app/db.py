import os
import psycopg

def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        dbname=os.getenv("POSTGRES_DB"),
    )

def list_tables() -> str:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        return "\n".join(row[0] for row in cur.fetchall())

def get_schema(table_name: str) -> str:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        rows = cur.fetchall()
        if not rows:
            return f"ERROR: table '{table_name}' does not exist"
        return "\n".join(f"{c} {t} nullable={n}" for c, t, n in rows)