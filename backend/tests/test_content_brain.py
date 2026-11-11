import pytest

from app.schemas.content import GenerateContentRequest
from app.services.content_brain import ContentBrainError, build_prompt, parse_json_response, validate_content


def valid_payload(duration: int = 30) -> dict:
    return {
        "tema": "Produtividade e valor humano",
        "estrategia": {"objetivo": "Provocar reflexão", "publico": "Adultos jovens", "abordagem": "Crítica social"},
        "titulo": "O preço de estar sempre ocupado",
        "gancho": "E se estar ocupado não significar estar vivendo?",
        "roteiro": "Uma reflexão sobre produtividade.",
        "cenas": [
            {
                "numero": 1, "inicio_seg": 0, "fim_seg": 15,
                "narracao": "Primeira parte da narração.",
                "visual": "Pessoa atravessando uma avenida movimentada.",
                "texto_tela": "SEMPRE OCUPADO",
                "termos_busca_pixabay": ["busy city", "urban crowd"],
            },
            {
                "numero": 2, "inicio_seg": 15, "fim_seg": duration,
                "narracao": "Segunda parte da narração.",
                "visual": "Pessoa sozinha em um ônibus à noite.",
                "texto_tela": "MAS A QUE CUSTO?",
                "termos_busca_pixabay": ["lonely bus", "city night"],
            },
        ],
        "legenda": "Uma reflexão sobre o ritmo da vida.",
        "hashtags": ["#NOXISLAB", "#Sociedade"],
    }


def test_parse_json_response_accepts_markdown_fence():
    raw = '```json\n{"titulo": "Teste", "hashtags": []}\n```'
    assert parse_json_response(raw)["titulo"] == "Teste"


def test_parse_json_response_rejects_invalid_json():
    with pytest.raises(ContentBrainError, match="interpretar o JSON"):
        parse_json_response('{"titulo": }')


def test_parse_json_response_rejects_non_object_json():
    with pytest.raises(ContentBrainError, match="objeto JSON"):
        parse_json_response('["item"]')


def test_validate_content_accepts_contiguous_timeline():
    assert validate_content(valid_payload(), 30) is True


def test_validate_content_rejects_gap_between_scenes():
    payload = valid_payload()
    payload["cenas"][1]["inicio_seg"] = 16
    with pytest.raises(ContentBrainError, match="intervalo ou sobreposição"):
        validate_content(payload, 30)


def test_validate_content_rejects_wrong_final_duration():
    with pytest.raises(ContentBrainError, match="terminar em 30"):
        validate_content(valid_payload(29), 30)


def test_validate_content_rejects_missing_narration():
    payload = valid_payload()
    payload["cenas"][0]["narracao"] = ""
    with pytest.raises(ContentBrainError, match="narração e descrição visual"):
        validate_content(payload, 30)


def test_prompt_contains_requested_topic_duration_and_style():
    request = GenerateContentRequest(tema="A cultura da pressa", duracao=60, estilo="filosofia")
    prompt = build_prompt(request)
    assert "A cultura da pressa" in prompt
    assert "60 segundos" in prompt
    assert "existencialismo" in prompt
