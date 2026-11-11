import re
from typing import Any

import httpx

from app.core.config import Settings


class MediaHunterError(RuntimeError):
    pass


class MediaHunter:
    API_URL = "https://pixabay.com/api/videos/"
    OPTIONS_PER_SCENE = 4
    RESULTS_PER_QUERY = 12

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.settings = settings
        self.client = client or httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0))
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    @staticmethod
    def _clean_query(value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9\\s]", " ", value or "")
        return " ".join(cleaned.split()[:6]).strip()

    @classmethod
    def scene_queries(cls, scene: dict[str, Any]) -> list[str]:
        raw_terms = scene.get("termos_busca_pixabay", [])
        if isinstance(raw_terms, str):
            raw_terms = [raw_terms]
        if not isinstance(raw_terms, list):
            raw_terms = []
        candidates = [cls._clean_query(str(term)) for term in raw_terms if term]
        visual = cls._clean_query(str(scene.get("visual", "")))
        if visual:
            candidates.append(visual)
        queries: list[str] = []
        seen: set[str] = set()
        for query in candidates:
            key = query.casefold()
            if query and key not in seen:
                queries.append(query)
                seen.add(key)
            if len(queries) == 3:
                break
        return queries

    @staticmethod
    def score_video(video: dict[str, Any], query: str) -> int:
        tags = re.sub(r"[^a-zA-Z0-9\\s]", " ", str(video.get("tags", ""))).lower()
        query_words = set(MediaHunter._clean_query(query).lower().split())
        tag_words = set(tags.split())
        matches = len(query_words.intersection(tag_words))
        renditions = video.get("videos") or {}
        quality = renditions.get("medium") or renditions.get("small") or renditions.get("tiny") or {}
        width = int(quality.get("width") or 0)
        height = int(quality.get("height") or 0)
        resolution_bonus = 2 if width >= 1080 else 1 if width >= 720 else 0
        portrait_bonus = 1 if height > width else 0
        return matches * 3 + resolution_bonus + portrait_bonus

    @staticmethod
    def _best_rendition(video: dict[str, Any]) -> dict[str, Any] | None:
        renditions = video.get("videos") or {}
        for name in ("large", "medium", "small", "tiny"):
            rendition = renditions.get(name)
            if rendition and rendition.get("url"):
                return rendition
        return None

    def _search(self, query: str) -> list[dict[str, Any]]:
        if not self.settings.pixabay_api_key:
            raise MediaHunterError("PIXABAY_KEY não configurada no ambiente.")
        try:
            response = self.client.get(
                self.API_URL,
                params={
                    "key": self.settings.pixabay_api_key,
                    "q": query,
                    "lang": "en",
                    "per_page": self.RESULTS_PER_QUERY,
                    "safesearch": "true",
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MediaHunterError(f"Falha ao consultar o Pixabay: {exc}") from exc
        hits = payload.get("hits", [])
        return hits if isinstance(hits, list) else []

    def search_scene(self, scene: dict[str, Any]) -> dict[str, Any]:
        scene_number = int(scene.get("numero", 0))
        queries = self.scene_queries(scene)
        if not queries:
            raise MediaHunterError(f"A cena {scene_number} não possui termos visuais para busca.")
        catalog: dict[int, dict[str, Any]] = {}
        for query in queries:
            for video in self._search(query):
                rendition = self._best_rendition(video)
                video_id = video.get("id")
                if not rendition or not video_id:
                    continue
                candidate = {
                    "id_pixabay": video_id,
                    "tipo": "video",
                    "consulta": query,
                    "titulo": video.get("tags", ""),
                    "tags": video.get("tags", ""),
                    "url_preview": rendition.get("url"),
                    "pagina_fonte": video.get("pageURL", ""),
                    "criador": video.get("user", ""),
                    "largura": rendition.get("width"),
                    "altura": rendition.get("height"),
                    "duracao": video.get("duration"),
                    "pontuacao": self.score_video(video, query),
                }
                previous = catalog.get(int(video_id))
                if previous is None or candidate["pontuacao"] > previous["pontuacao"]:
                    catalog[int(video_id)] = candidate
        ranked = sorted(catalog.values(), key=lambda item: item["pontuacao"], reverse=True)
        return {
            "cena": scene_number,
            "consultas": queries,
            "opcoes": ranked[: self.OPTIONS_PER_SCENE],
            "total_encontrado": len(ranked),
        }

    def search_project(self, scenes: list[dict[str, Any]]) -> dict[str, Any]:
        results = []
        for scene in scenes:
            results.append(self.search_scene(scene))
        return {"cenas": results, "total_cenas": len(results)}
