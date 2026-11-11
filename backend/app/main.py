from fastapi import FastAPI, HTTPException

from app.core.config import get_settings
from app.schemas.content import GenerateContentRequest
from app.schemas.media import MediaSearchRequest
from app.schemas.project import MediaSelectionRequest, ProjectCreateRequest
from app.services.content_brain import ContentBrain, ContentBrainError
from app.services.media_hunter import MediaHunter, MediaHunterError
from app.services.project_store import ProjectStore, ProjectStoreError


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


@app.post("/api/media/search")
def search_media(request: MediaSearchRequest) -> dict:
    hunter = MediaHunter(settings)
    try:
        return hunter.search_project([scene.model_dump() for scene in request.cenas])
    except MediaHunterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        hunter.close()


@app.post("/api/projects", status_code=201)
def create_project(request: ProjectCreateRequest) -> dict:
    try:
        return ProjectStore(settings).create(request.content)
    except ProjectStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects")
def list_projects() -> dict:
    return {"projects": ProjectStore(settings).list()}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict:
    try:
        return ProjectStore(settings).get(project_id)
    except ProjectStoreError as exc:
        status = 404 if str(exc) == "Projeto não encontrado." else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/media/search")
def search_project_media(project_id: str) -> dict:
    store = ProjectStore(settings)
    try:
        project = store.get(project_id)
        scenes = project.get("content", {}).get("cenas", [])
        if not scenes:
            raise HTTPException(status_code=400, detail="O projeto ainda não possui cenas.")
        hunter = MediaHunter(settings)
        try:
            results = hunter.search_project(scenes)
        finally:
            hunter.close()
        return store.save_media_search(project_id, results)
    except ProjectStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MediaHunterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.put("/api/projects/{project_id}/media/scenes/{scene_number}/selection")
def select_project_media(project_id: str, scene_number: int, request: MediaSelectionRequest) -> dict:
    try:
        return ProjectStore(settings).save_media_selection(project_id, scene_number, request.pixabay_id)
    except ProjectStoreError as exc:
        status = 404 if "não encontrado" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
