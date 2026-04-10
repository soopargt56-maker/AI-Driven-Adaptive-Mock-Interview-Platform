from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class RoundDocument(BaseModel):
    round: int
    question: str
    answer_text: str | None = None
    nlp_score: float | None = None
    svm_label: str | None = None
    kg_score: float | None = None
    ner_entities: list[dict[str, Any] | str] = Field(default_factory=list)
    final_score: float | None = None
    difficulty: str
    difficulty_change: str | None = None
    feedback: dict[str, Any] = Field(
        default_factory=lambda: {"content": [], "strengths": [], "next_step": ""}
    )
    elo_before: float | None = None
    elo_after: float | None = None
    question_context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionDocument(BaseModel):
    session_id: str
    candidate_id: str
    skill: str
    rounds: list[RoundDocument]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sub_domain: str | None = None
    status: str = "active"
    current_difficulty: str = "medium"
    last_round: int = 1

    def to_mongo(self) -> dict[str, Any]:
        return self.model_dump()

