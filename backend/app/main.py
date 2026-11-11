from fastapi import FastAPI, HTTPException

from app.core.config import get_settings
from app.schemas.content import GenerateContentRequest
from app.services.content_brain import ContentBrain, ContentBrainError


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API de produção audiovisual do Content Lab.",
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/content/styles")
def content_styles() -> dict[str, list[str]]:
    return {
        "styles": [
            "critica_social",
            "psicologia",
            "filosofia",
            "storytelling",
            "educativo",
            "hiphop",
            "motivacional",
        ]
    }


@app.post("/api/content/generate")
def generate_content(request: GenerateContentRequest) -> dict:
    try:
        return ContentBrain(settings).generate(request)
    except ContentBrainError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
