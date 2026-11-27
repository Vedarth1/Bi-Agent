from typing import Literal
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(max_length=1000)


class AnalyzeRequest(BaseModel):
    question: str = Field(max_length=500)
    conversation_id: str | None = Field(default=None, max_length=64)


class ChartSpec(BaseModel):
    type: Literal["bar", "line", "pie"]
    title: str = Field(max_length=120)
    x_key: str = Field(max_length=64)
    y_key: str = Field(max_length=64)