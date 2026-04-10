from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class CandidateDocument(BaseModel):
    candidate_id: str
    resume_skills: list[str]
    sub_domain_profile: dict[str, str]
    elo_ratings: dict[str, float]
    session_history: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_mongo(self) -> dict[str, Any]:
        return self.model_dump()

