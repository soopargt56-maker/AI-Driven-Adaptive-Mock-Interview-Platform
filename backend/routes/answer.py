from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.config import get_settings
from backend.db import DatabaseConnectionError, get_database, is_database_exception
from backend.integrations import IntegrationError
from backend.routes.session import _get_next_question
from backend.scoring.pipeline import run_scoring_pipeline

router = APIRouter(prefix="/session", tags=["answer"])

DIFFICULTY_RATINGS = {"easy": 1000, "medium": 1500, "hard": 2000}


class SubmitAnswerRequest(BaseModel):
    session_id: str
    round: int
    answer_text: str
    cos_similarity: float
    length_ratio: float
    aligned_score: float
    word_count: int
    engagement_label: str | None = None
    wpm: float | None = None
    pause_count: int | None = None


def _difficulty_from_elo(elo: float) -> str:
    if elo < 1200:
        return "easy"
    if elo < 1700:
        return "medium"
    return "hard"


def _compute_elo_update(elo_before: float, difficulty: str, final_score: float) -> float:
    question_rating = DIFFICULTY_RATINGS.get(difficulty, 1500)
    expected = 1.0 / (1.0 + pow(10.0, (question_rating - elo_before) / 400.0))
    actual = final_score / 100.0
    updated = elo_before + 32 * (actual - expected)
    return round(max(600.0, min(2400.0, updated)), 2)


def _difficulty_delta(previous: str, current: str) -> str:
    order = {"easy": 0, "medium": 1, "hard": 2}
    if order.get(current, 1) > order.get(previous, 1):
        return "increase"
    if order.get(current, 1) < order.get(previous, 1):
        return "decrease"
    return "same"


@router.post("/answer")
def submit_answer(request: SubmitAnswerRequest) -> dict[str, object]:
    settings = get_settings()
    try:
        db = get_database()
    except DatabaseConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    session = db["sessions"].find_one({"session_id": request.session_id})
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    rounds = session.get("rounds", [])
    active_round = next((item for item in rounds if item.get("round") == request.round), None)
    if not active_round:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested round not found in session.",
        )
    if active_round.get("answer_text"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This round has already been submitted.",
        )

    try:
        scoring_result = run_scoring_pipeline(
            answer_text=request.answer_text,
            cos_similarity=request.cos_similarity,
            length_ratio=request.length_ratio,
            aligned_score=request.aligned_score,
            word_count=request.word_count,
            engagement_label=request.engagement_label,
            wpm=request.wpm,
            pause_count=request.pause_count,
            question_context=active_round.get("question_context", {}),
        )
    except IntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    elo_before = float(active_round.get("elo_before") or settings.initial_elo)
    elo_after = _compute_elo_update(
        elo_before=elo_before,
        difficulty=active_round.get("difficulty", "medium"),
        final_score=float(scoring_result["final_score"]),
    )
    next_difficulty = _difficulty_from_elo(elo_after)
    difficulty_change = _difficulty_delta(
        active_round.get("difficulty", "medium"), next_difficulty
    )

    for index, round_document in enumerate(rounds):
        if round_document.get("round") != request.round:
            continue
        rounds[index] = {
            **round_document,
            "answer_text": request.answer_text,
            "nlp_score": scoring_result["nlp_score"],
            "svm_label": scoring_result["svm_label"],
            "kg_score": scoring_result["kg_score"],
            "ner_entities": scoring_result["ner_entities"],
            "final_score": scoring_result["final_score"],
            "difficulty_change": difficulty_change,
            "feedback": scoring_result["feedback"],
            "elo_before": elo_before,
            "elo_after": elo_after,
        }
        break

    next_question: str | None = None
    if request.round < settings.max_rounds:
        asked = [item.get("question", "") for item in rounds]
        try:
            question_payload = _get_next_question(
                skill=session["skill"],
                sub_domain=session.get("sub_domain"),
                difficulty=next_difficulty,
                asked=asked,
            )
        except IntegrationError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
            ) from exc

        rounds.append(
            {
                "round": request.round + 1,
                "question": question_payload["question"],
                "answer_text": None,
                "nlp_score": None,
                "svm_label": None,
                "kg_score": None,
                "ner_entities": [],
                "final_score": None,
                "difficulty": next_difficulty,
                "difficulty_change": None,
                "feedback": {"content": [], "strengths": [], "next_step": ""},
                "elo_before": elo_after,
                "elo_after": None,
                "question_context": question_payload,
            }
        )
        next_question = question_payload["question"]

    try:
        db["sessions"].update_one(
            {"session_id": request.session_id},
            {
                "$set": {
                    "rounds": rounds,
                    "last_round": request.round,
                    "current_difficulty": next_difficulty,
                    "status": "completed"
                    if request.round >= settings.max_rounds
                    else "active",
                }
            },
        )
        db["candidates"].update_one(
            {"candidate_id": session["candidate_id"]},
            {"$set": {f"elo_ratings.{session['skill']}": elo_after}},
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
        "svm_label": scoring_result["svm_label"],
        "nlp_score": scoring_result["nlp_score"],
        "kg_score": scoring_result["kg_score"],
        "ner_entities": scoring_result["ner_entities"],
        "final_score": scoring_result["final_score"],
        "feedback": scoring_result["feedback"],
        "next_question": next_question,
        "next_difficulty": next_difficulty,
        "elo_after": elo_after,
        "difficulty_change": difficulty_change,
    }
