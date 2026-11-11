import pytest

from app.core.config import Settings
from app.services.project_store import ProjectStore, ProjectStoreError


def test_create_get_and_list_project(tmp_path):
    store = ProjectStore(Settings(app_data_dir=tmp_path))
    created = store.create({"titulo": "Teste NOXIS", "tema": "Cultura urbana", "cenas": []})
    loaded = store.get(created["id"])
    listed = store.list()
    assert loaded["id"] == created["id"]
    assert loaded["status"] == "content_ready"
    assert listed[0]["titulo"] == "Teste NOXIS"


def test_invalid_project_id_is_rejected(tmp_path):
    store = ProjectStore(Settings(app_data_dir=tmp_path))
    with pytest.raises(ProjectStoreError, match="ID de projeto inválido"):
        store.get("../../secrets")


def test_missing_project_is_reported(tmp_path):
    store = ProjectStore(Settings(app_data_dir=tmp_path))
    with pytest.raises(ProjectStoreError, match="Projeto não encontrado"):
        store.get("00000000-0000-0000-0000-000000000000")


def test_media_selection_only_accepts_candidate_for_scene(tmp_path):
    store = ProjectStore(Settings(app_data_dir=tmp_path))
    project = store.create({"titulo": "Teste", "cenas": []})
    store.save_media_search(project["id"], {
        "cenas": [{"cena": 1, "opcoes": [{"id_pixabay": 123, "url_preview": "https://example.com/a.mp4"}]}]
    })
    selected = store.save_media_selection(project["id"], 1, 123)
    assert selected["media"]["selecao"]["1"]["id_pixabay"] == 123
    with pytest.raises(ProjectStoreError, match="não pertence às opções"):
        store.save_media_selection(project["id"], 1, 999)
