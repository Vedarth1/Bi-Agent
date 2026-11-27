import json
from fastapi import APIRouter
from pydantic import ValidationError
from app.schemas import ChatRequest, AnalyzeRequest, ChartSpec
from app.llm_service import run_agent, build_chart_spec
from app.db import execute_query
from app.memory import store

router = APIRouter()


@router.post("/chat")
def chat(req: ChatRequest):
    result = run_agent(req.prompt)
    return {"response": result["answer"]}


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    cid = req.conversation_id
    if not cid or not store.exists(cid):
        cid = store.create()
    history = store.history(cid)

    result = run_agent(req.question, history=history)
    columns, rows, chart, chart_error = [], [], None, None

    if result["sql_used"]:
        try:
            columns, rows = execute_query(result["sql_used"])
        except Exception as e:
            chart_error = f"re-running captured SQL failed: {e}"

    if columns:
        try:
            chart = ChartSpec.model_validate(
                build_chart_spec(req.question, columns, rows)
            ).model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            chart_error = f"chart spec invalid: {e}"

    # only successful turns enter memory; errors are transient, not knowledge
    if result["answer"].startswith("ERROR"):
        history_turns = len(history) // 2
    else:
        history_turns = store.append_turn(cid, req.question, result["answer"])

    return {
        "question": req.question,
        "answer": result["answer"],
        "sql": result["sql_used"],
        "iterations": result["iterations"],
        "tools_used": result["tools_used"],
        "columns": columns,
        "rows": rows,
        "chart": chart,
        "chart_error": chart_error,
        "conversation_id": cid,
        "history_turns": history_turns,
    }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    store.delete(conversation_id)
    return {"deleted": conversation_id}