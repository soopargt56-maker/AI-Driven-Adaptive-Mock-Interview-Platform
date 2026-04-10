from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from backend.config import get_settings
from backend.db import DatabaseConnectionError, get_database, is_database_exception
from backend.integrations import (
    IntegrationError,
    load_module,
    map_skills_to_domains,
)
from backend.models.candidate import CandidateDocument

router = APIRouter(prefix="/resume", tags=["resume"])


def _normalize_skills(payload: object) -> list[str]:
    if isinstance(payload, dict):
        for key in ("skills", "resume_skills", "data"):
            if key in payload:
                return _normalize_skills(payload[key])
        return []
    if isinstance(payload, (list, tuple, set)):
        return [str(item).strip() for item in payload if str(item).strip()]
    if isinstance(payload, str):
        return [payload.strip()] if payload.strip() else []
    return []


@router.post("")
async def parse_resume(file: UploadFile = File(...)) -> dict[str, object]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume upload must be a PDF file.",
        )

    settings = get_settings()
    suffix = Path(file.filename).suffix or ".pdf"

    with tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix, dir=settings.project_root
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(await file.read())

    try:
        parser_module = load_module("resume_parser", "resume_parser.py")
        if not hasattr(parser_module, "parse_resume"):
            raise IntegrationError(
                "resume_parser.py does not expose parse_resume(pdf_path)."
            )

        try:
            parsed_skills = parser_module.parse_resume(str(temp_path))
        except Exception as parse_exc:
            print(f"Warning: Failed to parse PDF ({parse_exc}). Defaulting skills.")
            parsed_skills = ["Python"]

        skills = _normalize_skills(parsed_skills)
        domain_profile = map_skills_to_domains(skills)
        candidate_id = str(uuid4())

        candidate = CandidateDocument(
            candidate_id=candidate_id,
            resume_skills=skills,
            sub_domain_profile=domain_profile,
            elo_ratings={skill: settings.initial_elo for skill in skills},
            session_history=[],
        )
        try:
            get_database()["candidates"].insert_one(candidate.to_mongo())
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
            "candidate_id": candidate_id,
            "skills": skills,
            "domain_profile": domain_profile,
        }
    except IntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except DatabaseConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    finally:
        if temp_path.exists():
            temp_path.unlink()
