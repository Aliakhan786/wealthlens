"""Request models (Pydantic v2) — input validation is the first line of API defence."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class SimulateRequest(BaseModel):
    asset_id: str = Field(..., max_length=40, examples=["nifty50"])
    amount: float = Field(..., gt=0, le=1e9, description="₹ — per month for SIP, one-time for lump sum")
    years: float | None = Field(5, gt=0, le=30)
    start: date | None = None
    end: date | None = None
    step_up_pct: float = Field(0, ge=0, le=50, description="SIP only: yearly increase in the monthly amount")


class QuizRequest(BaseModel):
    answers: dict[str, int]


class ExplainRequest(BaseModel):
    asset_id: str = Field(..., max_length=40)
    lang: Literal["en", "hi"] = "en"


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=4000)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=600)
    lang: Literal["en", "hi"] = "en"
    history: list[ChatTurn] = Field(default_factory=list, max_length=10)
