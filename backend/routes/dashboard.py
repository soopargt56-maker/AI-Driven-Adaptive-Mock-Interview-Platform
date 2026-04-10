from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from backend.db import DatabaseConnectionError, get_database, is_database_exception

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _score_bucket(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 75:
        return "Good"
    if score >= 50:
        return "Average"
    return "Poor"


def _sanitize_rounds(rounds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized = []
    for round_document in rounds:
        cleaned = dict(round_document)
        cleaned.pop("question_context", None)
        cleaned["performance_band"] = _score_bucket(cleaned.get("final_score"))
        sanitized.append(cleaned)
    return sanitized


def _compute_topic_scores(session: dict[str, Any]) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for round_document in session.get("rounds", []):
        score = round_document.get("final_score")
        if score is None:
            continue
        context = round_document.get("question_context", {}) or {}
        label = (
            context.get("topic")
            or context.get("sub_topic")
            or context.get("sub_domain")
            or session.get("skill")
            or "Overall"
        )
        buckets.setdefault(str(label), []).append(float(score))

    return {
        label: round(sum(values) / len(values), 2) for label, values in buckets.items()
    }


@router.get("/{session_id}")
def get_dashboard(session_id: str) -> dict[str, Any]:
    try:
        session = get_database()["sessions"].find_one(
            {"session_id": session_id}, {"_id": 0}
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
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    rounds = _sanitize_rounds(session.get("rounds", []))
    completed_rounds = [item for item in rounds if item.get("final_score") is not None]

    if completed_rounds:
        averages = {
            "final_score": round(
                sum(float(item.get("final_score", 0)) for item in completed_rounds)
                / len(completed_rounds),
                2,
            ),
            "nlp_score": round(
                sum(float(item.get("nlp_score", 0)) for item in completed_rounds)
                / len(completed_rounds),
                2,
            ),
            "kg_score": round(
                sum(float(item.get("kg_score", 0)) for item in completed_rounds)
                / len(completed_rounds),
                2,
            ),
        }
    else:
        averages = {"final_score": 0.0, "nlp_score": 0.0, "kg_score": 0.0}

    breakdown = {"Good": 0, "Average": 0, "Poor": 0}
    for item in completed_rounds:
        band = item.get("performance_band")
        if band in breakdown:
            breakdown[band] += 1

    last_feedback = completed_rounds[-1].get("feedback", {}) if completed_rounds else {}

    session["rounds"] = rounds
    session["averages"] = averages
    session["breakdown"] = breakdown
    session["elo_progression"] = [
        item.get("elo_after") for item in completed_rounds if item.get("elo_after") is not None
    ]
    session["difficulty_progression"] = [item.get("difficulty") for item in completed_rounds]
    session["topic_scores"] = _compute_topic_scores(session)
    session["next_step"] = last_feedback.get("next_step", "")
    return session
