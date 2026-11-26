from app.db import list_tables, get_schema

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

    return f"ERROR: unknown tool '{name}'"