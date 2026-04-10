from __future__ import annotations

from functools import lru_cache
from typing import Any

import joblib

from backend.integrations import (
    IntegrationError,
    call_with_supported_signature,
    load_module,
    locate_file,
    normalize_feedback,
)


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@lru_cache(maxsize=1)
def _load_svm_model() -> Any:
    model_path = locate_file("svm_model.joblib", group="model")
    return joblib.load(model_path)


def _extract_score_value(payload: Any, keys: tuple[str, ...]) -> float | None:
    if isinstance(payload, dict):
        for key in keys:
            if key in payload:
                return _coerce_float(payload[key])
    elif payload is not None:
        return _coerce_float(payload)
    return None


def _run_nlp_score(answer_text: str, question_context: dict[str, Any]) -> tuple[float, Any]:
    module = load_module("nlp_scorer", "nlp_scorer.py")

    if hasattr(module, "NLPScorer"):
        scorer = module.NLPScorer()
        result = call_with_supported_signature(
            scorer.compute_overall_score,
            answer_text=answer_text,
            answer=answer_text,
            question=question_context.get("question"),
            ideal_answer=question_context.get("ideal_answer"),
            reference_answer=question_context.get("ideal_answer"),
            ideal_keywords=question_context.get("ideal_keywords", ""),
            expected_keywords=question_context.get("ideal_keywords", ""),
        )
    elif hasattr(module, "compute_score"):
        result = call_with_supported_signature(
            module.compute_score,
            answer=answer_text,
            answer_text=answer_text,
            ideal_keywords=question_context.get("ideal_keywords", ""),
            ideal_answer=question_context.get("ideal_answer"),
        )
    else:
        raise IntegrationError(
            "nlp_scorer.py does not expose a supported scoring interface."
        )

    score = _extract_score_value(result, ("overall_score", "final_score", "score", "nlp_score"))
    return _coerce_float(score), result


def _run_svm_label(
    cos_similarity: float,
    length_ratio: float,
    aligned_score: float,
    word_count: int,
) -> str:
    model = _load_svm_model()
    features = [[cos_similarity, length_ratio, aligned_score, word_count]]
    prediction = model.predict(features)
    if prediction is None or len(prediction) == 0:
        raise IntegrationError("SVM model returned no prediction.")
    return str(prediction[0])


def _run_knowledge_graph(
    answer_text: str, question_context: dict[str, Any]
) -> tuple[float, Any]:
    module = load_module("knowledge_graph", "knowledge_graph.py")
    if not hasattr(module, "KnowledgeGraphScorer"):
        raise IntegrationError(
            "knowledge_graph.py does not expose KnowledgeGraphScorer."
        )

    scorer = module.KnowledgeGraphScorer()
    result = call_with_supported_signature(
        scorer.score_answer,
        answer=answer_text,
        answer_text=answer_text,
        question=question_context.get("question"),
        ideal_answer=question_context.get("ideal_answer"),
        reference_answer=question_context.get("ideal_answer"),
        skill=question_context.get("skill"),
        sub_domain=question_context.get("sub_domain"),
    )

    score = _extract_score_value(result, ("kg_score", "score", "final_score"))
    return _coerce_float(score), result


def _run_ner(answer_text: str) -> list[dict[str, Any] | str]:
    module = load_module("ner_scorer", "ner_scorer.py")
    if not hasattr(module, "NERScorer"):
        raise IntegrationError("ner_scorer.py does not expose NERScorer.")

    scorer = module.NERScorer()
    entities = call_with_supported_signature(
        scorer.extract_entities,
        answer=answer_text,
        answer_text=answer_text,
    )
    if isinstance(entities, list):
        return entities
    if entities is None:
        return []
    return [entities]


def _run_feedback(
    answer_text: str,
    nlp_score: float,
    svm_label: str,
    kg_score: float,
    final_score: float,
    ner_entities: list[dict[str, Any] | str],
    question_context: dict[str, Any],
) -> dict[str, Any]:
    module = load_module("c4_feedback", "c4_feedback.py")
    if not hasattr(module, "generate_feedback"):
        raise IntegrationError("c4_feedback.py does not expose generate_feedback().")

    payload = call_with_supported_signature(
        module.generate_feedback,
        answer=answer_text,
        answer_text=answer_text,
        question=question_context.get("question"),
        ideal_answer=question_context.get("ideal_answer"),
        skill=question_context.get("skill"),
        sub_domain=question_context.get("sub_domain"),
        nlp_score=nlp_score,
        svm_label=svm_label,
        kg_score=kg_score,
        final_score=final_score,
        ner_entities=ner_entities,
    )
    return normalize_feedback(payload)


def run_scoring_pipeline(
    *,
    answer_text: str,
    cos_similarity: float,
    length_ratio: float,
    aligned_score: float,
    word_count: int,
    engagement_label: str | None = None,
    wpm: float | None = None,
    pause_count: int | None = None,
    question_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    question_context = question_context or {}

    nlp_score, nlp_payload = _run_nlp_score(answer_text, question_context)
    svm_label = _run_svm_label(cos_similarity, length_ratio, aligned_score, word_count)
    kg_score, kg_payload = _run_knowledge_graph(answer_text, question_context)
    ner_entities = _run_ner(answer_text)
    final_score = _extract_score_value(
        kg_payload,
        ("final_score", "overall_score", "score", "kg_score"),
    )
    if final_score is None:
        final_score = _extract_score_value(
            nlp_payload,
            ("final_score", "overall_score", "score", "nlp_score"),
        )
    if final_score is None:
        raise IntegrationError(
            "No final_score was exposed by the provided scoring modules. "
            "The pipeline will not invent one inline."
        )
    feedback = _run_feedback(
        answer_text=answer_text,
        nlp_score=nlp_score,
        svm_label=svm_label,
        kg_score=kg_score,
        final_score=round(final_score, 2),
        ner_entities=ner_entities,
        question_context=question_context,
    )

    metadata = {
        "engagement_label": engagement_label,
        "wpm": _coerce_float(wpm, 0.0) if wpm is not None else None,
        "pause_count": int(pause_count) if pause_count is not None else None,
    }

    return {
        "svm_label": svm_label,
        "nlp_score": round(nlp_score, 2),
        "kg_score": round(kg_score, 2),
        "ner_entities": ner_entities,
        "final_score": round(final_score, 2),
        "feedback": feedback,
        "metadata": metadata,
    }
