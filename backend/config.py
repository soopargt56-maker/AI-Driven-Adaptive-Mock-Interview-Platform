from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    mongodb_uri: str
    mongodb_db: str
    mongodb_timeout_ms: int
    cors_origins: list[str]
    max_rounds: int
    initial_elo: float
    interview_module_paths: list[Path]
    interview_model_paths: list[Path]
    interview_data_paths: list[Path]


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _resolve_paths(raw_value: str | None, defaults: list[Path]) -> list[Path]:
    if not raw_value:
        return defaults

    resolved: list[Path] = []
    for entry in raw_value.split(os.pathsep):
        entry = entry.strip()
        if not entry:
            continue
        resolved.append(Path(entry).expanduser().resolve())
    return resolved or defaults


def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[1]
    sibling_eval_project = project_root.parent / "eval_project"

    default_module_paths = [
        project_root,
        project_root / "backend",
        project_root / "modules",
        sibling_eval_project,
        sibling_eval_project / "modules",
    ]
    default_model_paths = [
        project_root,
        project_root / "backend" / "scoring",
        project_root / "models",
        sibling_eval_project,
        sibling_eval_project / "dataset_v1",
    ]
    default_data_paths = [
        project_root,
        project_root / "data",
        sibling_eval_project,
        sibling_eval_project / "data",
    ]

    return Settings(
        project_root=project_root,
        mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        mongodb_db=os.getenv("MONGODB_DB", "adaptive_mock_interview"),
        mongodb_timeout_ms=int(os.getenv("MONGODB_TIMEOUT_MS", "2000")),
        cors_origins=_split_csv(
            os.getenv(
                "CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
            )
        ),
        max_rounds=int(os.getenv("MAX_ROUNDS", "5")),
        initial_elo=float(os.getenv("INITIAL_ELO", "1200")),
        interview_module_paths=_resolve_paths(
            os.getenv("INTERVIEW_MODULE_PATHS"), default_module_paths
        ),
        interview_model_paths=_resolve_paths(
            os.getenv("INTERVIEW_MODEL_PATHS"), default_model_paths
        ),
        interview_data_paths=_resolve_paths(
            os.getenv("INTERVIEW_DATA_PATHS"), default_data_paths
        ),
    )
