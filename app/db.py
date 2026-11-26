import os
import re
import psycopg

def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("DB_USER", "agent_ro"),
        password=os.getenv("DB_PASSWORD"),
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

FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|VACUUM|CALL|DO|MERGE)\b",
    re.IGNORECASE,
)

def validate_sql(sql: str) -> str | None:
    """Return an error message if the SQL is not a plain read-only SELECT, else None."""
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        return "ERROR: empty SQL"
    if ";" in cleaned:
        return "ERROR: multiple statements are not allowed"
    if not re.match(r"^(SELECT|WITH)\b", cleaned, re.IGNORECASE):
        return "ERROR: only SELECT (or WITH ... SELECT) statements are allowed"
    match = FORBIDDEN.search(cleaned)
    if match:
        return f"ERROR: keyword '{match.group(1).upper()}' is not allowed (read-only access)"
    return None


def run_query(sql: str) -> str:
    error = validate_sql(sql)
    if error:
        return error

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(sql)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchmany(20)                      # cap output: results become context = tokens
            lines = [" | ".join(columns)]
            lines += [" | ".join(str(v) for v in row) for row in rows]
            if len(rows) == 20:
                lines.append("(truncated at 20 rows)")
            return "\n".join(lines)
    except psycopg.Error as e:
        return f"SQL ERROR: {e}"                          # feed the error to the model so it can self-correct