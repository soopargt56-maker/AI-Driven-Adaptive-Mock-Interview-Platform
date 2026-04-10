from __future__ import annotations

import csv
import importlib
import importlib.util
import inspect
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

from backend.config import get_settings


class IntegrationError(RuntimeError):
    pass


def _candidate_paths(group: str) -> list[Path]:
    settings = get_settings()
    if group == "module":
        return settings.interview_module_paths
    if group == "model":
        return settings.interview_model_paths
    if group == "data":
        return settings.interview_data_paths
    raise ValueError(f"Unknown path group: {group}")


def locate_file(filename: str, group: str = "module") -> Path:
    for base_path in _candidate_paths(group):
        candidate = base_path / filename
        if candidate.exists():
            return candidate

    raise IntegrationError(
        f"Required integration file '{filename}' was not found in configured {group} paths."
    )


@lru_cache(maxsize=None)
def load_module(module_name: str, filename: str | None = None) -> ModuleType:
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        if not filename:
            raise IntegrationError(
                f"Python module '{module_name}' is unavailable and no fallback filename was provided."
            ) from None

    file_path = locate_file(filename, group="module")
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if not spec or not spec.loader:
        raise IntegrationError(f"Unable to import integration module from '{file_path}'.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def call_with_supported_signature(func: Any, **kwargs: Any) -> Any:
    signature = inspect.signature(func)
    accepted = {}

    for name, parameter in signature.parameters.items():
        if parameter.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ) and name in kwargs:
            accepted[name] = kwargs[name]

    return func(**accepted)


@lru_cache(maxsize=1)
def load_skill_taxonomy() -> dict[str, dict[str, str]]:
    try:
        taxonomy_path = locate_file("skill_taxonomy.csv", group="data")
    except IntegrationError:
        return {}

    taxonomy: dict[str, dict[str, str]] = {}
    with taxonomy_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            skill = (
                row.get("skill")
                or row.get("Skill")
                or row.get("resume_skill")
                or row.get("Resume Skill")
            )
            if not skill:
                continue
            taxonomy[skill.strip().lower()] = {
                "domain": (
                    row.get("domain")
                    or row.get("Domain")
                    or row.get("category")
                    or "general"
                ).strip(),
                "sub_domain": (
                    row.get("sub_domain")
                    or row.get("subdomain")
                    or row.get("Sub Domain")
                    or row.get("SubDomain")
                    or row.get("domain")
                    or "general"
                ).strip(),
            }
    return taxonomy


def map_skills_to_domains(skills: list[str]) -> dict[str, str]:
    taxonomy = load_skill_taxonomy()
    mapped: dict[str, str] = {}
    for skill in skills:
        entry = taxonomy.get(skill.strip().lower())
        mapped[skill] = entry["sub_domain"] if entry else "general"
    return mapped


def normalize_feedback(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return {
            "content": payload.get("content") or payload.get("summary") or [],
            "strengths": payload.get("strengths") or [],
            "next_step": payload.get("next_step") or payload.get("recommendation") or "",
        }

    if isinstance(payload, (list, tuple)):
        return {"content": list(payload), "strengths": [], "next_step": ""}

    if isinstance(payload, str):
        return {"content": [payload], "strengths": [], "next_step": ""}

    return {"content": [], "strengths": [], "next_step": ""}

