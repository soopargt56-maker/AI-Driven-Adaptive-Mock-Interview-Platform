from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.config import get_settings
from backend.db import DatabaseConnectionError, get_database, is_database_exception
from backend.integrations import IntegrationError, load_module
from backend.models.session import RoundDocument, SessionDocument

router = APIRouter(prefix="/session", tags=["session"])


class StartSessionRequest(BaseModel):
    candidate_id: str
    skill: str
    sub_domain: str | None = None


def _elo_to_difficulty(elo: float) -> str:
    if elo < 1200:
        return "easy"
    if elo < 1700:
        return "medium"
    return "hard"


def _normalize_question_payload(payload: object, *, skill: str, sub_domain: str | None) -> dict:
    if isinstance(payload, str):
        return {
            "question": payload,
            "ideal_answer": "",
            "ideal_keywords": "",
            "skill": skill,
            "sub_domain": sub_domain,
        }

    if isinstance(payload, dict):
        question_text = (
            payload.get("question")
            or payload.get("prompt")
            or payload.get("text")
            or payload.get("query")
        )
        if not question_text:
            raise IntegrationError("question_bank.py returned a question payload without text.")

        return {
            "question": str(question_text),
            "ideal_answer": str(
                payload.get("ideal_answer")
                or payload.get("reference_answer")
                or payload.get("answer")
                or ""
            ),
            "ideal_keywords": str(
                payload.get("ideal_keywords")
                or payload.get("keywords")
                or payload.get("expected_keywords")
                or ""
            ),
            "skill": skill,
            "sub_domain": sub_domain,
        }

    raise IntegrationError("question_bank.py returned an unsupported question format.")


def _get_next_question(
    *,
    skill: str,
    sub_domain: str | None,
    difficulty: str,
    asked: list[str],
) -> dict:
    module = load_module("question_bank", "question_bank.py")
    if not hasattr(module, "get_next_question"):
        raise IntegrationError(
            "question_bank.py does not expose get_next_question(skill, sub_domain, difficulty, asked)."
        )

    payload = module.get_next_question(skill, sub_domain, difficulty, asked)
    return _normalize_question_payload(payload, skill=skill, sub_domain=sub_domain)


@router.post("/start")
def start_session(request: StartSessionRequest) -> dict[str, object]:
    settings = get_settings()
    try:
        db = get_database()
    except DatabaseConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    candidate = db["candidates"].find_one({"candidate_id": request.candidate_id})
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found.",
        )

    elo_before = float(
        candidate.get("elo_ratings", {}).get(request.skill, settings.initial_elo)
    )
    difficulty = _elo_to_difficulty(elo_before)

    try:
        first_question = _get_next_question(
            skill=request.skill,
            sub_domain=request.sub_domain
            or candidate.get("sub_domain_profile", {}).get(request.skill),
            difficulty=difficulty,
            asked=[],
        )
    except IntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    round_document = RoundDocument(
        round=1,
        question=first_question["question"],
        difficulty=difficulty,
        elo_before=elo_before,
        question_context=first_question,
    )
    session_id = str(uuid4())
    session = SessionDocument(
        session_id=session_id,
        candidate_id=request.candidate_id,
        skill=request.skill,
        sub_domain=request.sub_domain
        or candidate.get("sub_domain_profile", {}).get(request.skill),
        rounds=[round_document],
        current_difficulty=difficulty,
        last_round=1,
    )

    try:
        db["sessions"].insert_one(session.to_mongo())
        db["candidates"].update_one(
            {"candidate_id": request.candidate_id},
            {
                "$addToSet": {"session_history": session_id, "resume_skills": request.skill},
                "$set": {
                    f"sub_domain_profile.{request.skill}": session.sub_domain or "general",
                    f"elo_ratings.{request.skill}": elo_before,
                },
            },
        )
    except DatabaseConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except Exception as exc:
        if is_database_exception(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"MongoDB operation failed: {exc}",
            ) from exc
        raise

    return {
        "session_id": session_id,
        "question": first_question["question"],
        "difficulty": difficulty,
        "round": 1,
    }
