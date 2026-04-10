from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.routes.answer import router as answer_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.resume import router as resume_router
from backend.routes.session import router as session_router


settings = get_settings()
app = FastAPI(title="AI-Based Adaptive Mock Interview System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume_router)
app.include_router(session_router)
app.include_router(answer_router)
app.include_router(dashboard_router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
