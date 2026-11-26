from fastapi import APIRouter
from app.schemas import ChatRequest
from app.llm_service import ask_llm

router = APIRouter()

@router.post("/chat")
def chat(req: ChatRequest):
    answer = ask_llm(req.prompt)
    return {"response": answer}