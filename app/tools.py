from app.db import list_tables, get_schema, run_query

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "List all tables in the database",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_schema",
            "description": "Get columns and types for one table. Use after list_tables to understand the structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Exact table name"}
                },
                "required": ["table_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_query",
            "description": "Run a read-only SQL SELECT query against the database and return up to 20 rows. Use get_schema first to learn column names.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "A single SELECT statement"}
                },
                "required": ["sql"]
            }
        }
    }
]


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool the model requested. Always returns a string:
    either the tool result or a readable error (the model can read errors too)."""
    if name == "list_tables":
        return list_tables()

    if name == "get_schema":
        table_name = arguments.get("table_name")
        if not table_name:
            return "ERROR: table_name argument is required"
        return get_schema(table_name=table_name)

    if name == "run_query":
        sql = arguments.get("sql")
        if not sql:
            return "ERROR: sql argument is required"
        return run_query(sql)

    return f"ERROR: unknown tool '{name}'"