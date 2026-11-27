from typing import Literal
from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str


class AnalyzeRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class ChartSpec(BaseModel):
    type: Literal["bar", "line", "pie"]
    title: str
    x_key: str
    y_key: str