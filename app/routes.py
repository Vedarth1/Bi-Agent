from fastapi import APIRouter
from app.schemas import ChatRequest
from app.llm_service import run_agent

router = APIRouter()

@router.post("/chat")
def chat(req: ChatRequest):
    answer = run_agent(req.prompt)
    return {"response": answer}