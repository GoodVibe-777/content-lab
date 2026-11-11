import pytest

from app.core.config import Settings
from app.services.media_hunter import MediaHunter, MediaHunterError


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, params):
        self.calls.append((url, params))
        return FakeResponse(self.payload)


def video(video_id, tags, width=1280, height=720):
    return {
        "id": video_id,
        "tags": tags,
        "pageURL": "https://pixabay.com/videos/example/",
        "user": "creator",
        "duration": 12,
        "videos": {"medium": {"url": "https://cdn.example/video.mp4", "width": width, "height": height}},
    }


def test_scene_queries_uses_terms_and_visual_without_duplicates():
    scene = {
        "termos_busca_pixabay": ["urban night", "urban night", "street protest"],
        "visual": "Urban night with people walking",
    }
    assert MediaHunter.scene_queries(scene) == [
        "urban night", "street protest", "Urban night with people walking"
    ]


def test_clean_query_preserves_letters_and_removes_punctuation():
    assert MediaHunter._clean_query("street's night! 2026") == "street s night 2026"


def test_score_video_rewards_tag_matches_and_resolution():
    item = video(1, "urban night city", 1920, 1080)
    assert MediaHunter.score_video(item, "urban night") > MediaHunter.score_video(video(2, "nature forest", 640, 360), "urban night")


def test_search_scene_returns_ranked_candidates_and_deduplicates():
    client = FakeClient({"hits": [video(10, "urban night city"), video(11, "urban crowd")]})
    hunter = MediaHunter(Settings(pixabay_api_key="test-key"), client=client)
    result = hunter.search_scene({
        "numero": 1,
        "visual": "urban night",
        "termos_busca_pixabay": ["urban night", "city crowd"],
    })
    assert result["cena"] == 1
    assert result["total_encontrado"] == 2
    assert len(result["opcoes"]) == 2
    assert len(client.calls) == 2
    assert result["opcoes"][0]["id_pixabay"] == 10


def test_search_requires_pixabay_key():
    hunter = MediaHunter(Settings())
    with pytest.raises(MediaHunterError, match="PIXABAY_KEY"):
        hunter.search_scene({"numero": 1, "visual": "urban night", "termos_busca_pixabay": ["urban night"]})
    hunter.close()
