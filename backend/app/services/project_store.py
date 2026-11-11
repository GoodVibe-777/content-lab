import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4
from typing import Any

from app.core.config import Settings


class ProjectStoreError(RuntimeError):
    pass


class ProjectStore:
    def __init__(self, settings: Settings):
        self.directory = settings.projects_dir

    def _path(self, project_id: str) -> Path:
        try:
            safe_id = str(UUID(project_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ProjectStoreError("ID de projeto inválido.") from exc
        return self.directory / f"{safe_id}.json"

    def _write(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent,
                prefix=f".{path.stem}.", suffix=".tmp", delete=False
            ) as temp_file:
                temp_path = Path(temp_file.name)
                json.dump(data, temp_file, ensure_ascii=False, indent=2)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def create(self, content: dict[str, Any]) -> dict[str, Any]:
        project_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        project = {
            "id": project_id,
            "status": "content_ready",
            "created_at": now,
            "updated_at": now,
            "content": content,
            "media": {"cenas": [], "selecao": {}},
        }
        self._write(self._path(project_id), project)
        return project

    def get(self, project_id: str) -> dict[str, Any]:
        path = self._path(project_id)
        if not path.exists():
            raise ProjectStoreError("Projeto não encontrado.")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProjectStoreError("Não foi possível ler o projeto salvo.") from exc

    def list(self) -> list[dict[str, Any]]:
        projects = []
        for path in self.directory.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                projects.append({
                    "id": data["id"],
                    "status": data.get("status", "unknown"),
                    "titulo": data.get("content", {}).get("titulo", "Projeto sem título"),
                    "tema": data.get("content", {}).get("tema", ""),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                })
            except (OSError, json.JSONDecodeError, KeyError, TypeError):
                continue
        return sorted(projects, key=lambda item: item.get("updated_at") or "", reverse=True)

    def save_media_search(self, project_id: str, media_results: dict[str, Any]) -> dict[str, Any]:
        project = self.get(project_id)
        project["media"]["cenas"] = media_results.get("cenas", [])
        project["status"] = "media_ready"
        project["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write(self._path(project_id), project)
        return project

    def save_media_selection(self, project_id: str, scene_number: int, pixabay_id: int) -> dict[str, Any]:
        project = self.get(project_id)
        scene = next((item for item in project["media"].get("cenas", []) if item.get("cena") == scene_number), None)
        if scene is None:
            raise ProjectStoreError(f"Não existe resultado de mídia para a cena {scene_number}.")
        option = next((item for item in scene.get("opcoes", []) if int(item.get("id_pixabay", -1)) == pixabay_id), None)
        if option is None:
            raise ProjectStoreError("O vídeo selecionado não pertence às opções desta cena.")
        project["media"].setdefault("selecao", {})[str(scene_number)] = option
        project["status"] = "media_selected"
        project["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write(self._path(project_id), project)
        return project
