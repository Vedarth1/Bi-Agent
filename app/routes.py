import json
from fastapi import APIRouter
from pydantic import ValidationError
from app.schemas import ChatRequest, AnalyzeRequest, ChartSpec
from app.llm_service import run_agent, build_chart_spec
from app.db import execute_query

router = APIRouter()


@router.post("/chat")
def chat(req: ChatRequest):
    result = run_agent(req.prompt)
    return {"response": result["answer"]}


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    result = run_agent(req.question)
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
    }