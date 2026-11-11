import json
import re
from typing import Any

from google import genai
from groq import Groq

from app.core.config import Settings
from app.schemas.content import GenerateContentRequest


IDENTIDADE = """
Você é o diretor criativo e estrategista de conteúdo do NOXIS LAB.

POSICIONAMENTO:
Psicologia, hip-hop e crítica social sem filtro.

PERSONALIDADE:
- Inteligente, provocativa e independente.
- Linguagem contemporânea e natural.
- Reflexões profundas sem parecer um discurso acadêmico.
- Questionamento de padrões sociais e comportamentais.
- Filosofia conectada com a realidade cotidiana.

IDENTIDADE VISUAL:
- Cultura underground.
- Estética xerox e fanzine.
- Colagem, pichação e grafite.
- Preto, branco e roxo.
- Fotografia urbana, textura analógica e granulação.
- Referências à cultura hip-hop e de rua.

IMPORTANTE:
Não produza conteúdo genérico.
Não use frases motivacionais vazias.
Não invente estatísticas, pesquisas ou citações.
Diferencie fatos de opiniões.
"""

ESTILOS = {
    "critica_social": """
Tom provocativo e questionador.
Explore desigualdade, contradições sociais,
poder, manipulação e comportamento coletivo.
""",
    "psicologia": """
Explore comportamento humano, emoções,
relações, padrões mentais e autoconhecimento.
Linguagem acessível e reflexiva.
""",
    "filosofia": """
Conecte ideias filosóficas com dilemas reais.
Explore estoicismo, existencialismo,
ética, liberdade e consciência.
""",
    "storytelling": """
Construa uma narrativa envolvente.
Use contexto, tensão, desenvolvimento
e uma conclusão marcante.
""",
    "educativo": """
Explique assuntos complexos de maneira simples.
Use exemplos concretos e informações claras.
""",
    "hiphop": """
Explore cultura hip-hop, música, resistência,
identidade, arte urbana e vivência de rua.
Linguagem autêntica.
""",
    "motivacional": """
Inspire sem recorrer a clichês.
Explore disciplina, autonomia,
consciência e transformação pessoal.
""",
}


class ContentBrainError(RuntimeError):
    """Raised when generation or validation fails."""


def build_prompt(request: GenerateContentRequest) -> str:
    return f"""
{IDENTIDADE}

CRIE UM CONTEÚDO ORIGINAL PARA O NOXIS LAB.

TEMA: {request.tema}
DURAÇÃO TOTAL: {request.duracao} segundos.
PLATAFORMA: {request.plataforma}

ESTILO EDITORIAL:
{ESTILOS[request.estilo]}

DIRETRIZES:
1. Crie um título interessante.
2. Comece com um gancho forte.
3. Desenvolva uma ideia central.
4. Escreva uma narração natural, com ritmo de fala humana.
5. Termine com uma conclusão marcante.
6. Evite clichês e repetições.
7. Não invente informações.
8. Adapte o vocabulário ao público das redes sociais.
9. A narração deve caber na duração solicitada.
10. Cada cena deve conter uma sugestão visual detalhada.
11. Inclua termos de busca em inglês para encontrar imagens e vídeos no Pixabay.
12. Os termos de busca devem representar o visual, não apenas repetir o tema abstrato.

REGRAS DE TEMPO:
- A primeira cena começa em 0 segundos.
- As cenas devem ser contínuas, sem intervalos ou sobreposições.
- A última cena termina exatamente em {request.duracao}.
- Distribua a narração proporcionalmente ao tempo.

RETORNE SOMENTE JSON VÁLIDO, sem Markdown ou blocos de código.

ESTRUTURA:
{{
  "tema": "",
  "identidade": "NOXIS LAB",
  "estrategia": {{
    "objetivo": "",
    "publico": "",
    "abordagem": ""
  }},
  "titulo": "",
  "gancho": "",
  "roteiro": "",
  "cenas": [
    {{
      "numero": 1,
      "inicio_seg": 0,
      "fim_seg": {request.duracao},
      "narracao": "",
      "visual": "",
      "texto_tela": "",
      "termos_busca_pixabay": []
    }}
  ],
  "legenda": "",
  "hashtags": []
}}
"""


def parse_json_response(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    text = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text, flags=re.I)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ContentBrainError("A IA não retornou um objeto JSON válido.")
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ContentBrainError(f"Não foi possível interpretar o JSON da IA: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ContentBrainError("A resposta da IA precisa ser um objeto JSON.")
    return parsed


def validate_content(data: dict[str, Any], duration: int) -> bool:
    required = ("tema", "estrategia", "titulo", "gancho", "roteiro", "cenas", "legenda", "hashtags")
    missing = [field for field in required if field not in data]
    if missing:
        raise ContentBrainError(f"Campos ausentes na resposta: {', '.join(missing)}")

    scenes = data.get("cenas")
    if not isinstance(scenes, list) or not scenes:
        raise ContentBrainError("O roteiro precisa conter pelo menos uma cena.")

    previous_end = 0
    for index, scene in enumerate(scenes, start=1):
        try:
            start = int(scene["inicio_seg"])
            end = int(scene["fim_seg"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ContentBrainError(f"Tempos inválidos na cena {index}.") from exc

        if start != previous_end:
            raise ContentBrainError(f"Há intervalo ou sobreposição antes da cena {index}.")
        if end <= start:
            raise ContentBrainError(f"A cena {index} tem duração inválida.")
        if not scene.get("narracao") or not scene.get("visual"):
            raise ContentBrainError(f"A cena {index} precisa de narração e descrição visual.")
        if not isinstance(scene.get("termos_busca_pixabay", []), list):
            raise ContentBrainError(f"Os termos de busca da cena {index} precisam ser uma lista.")
        previous_end = end

    if int(scenes[0]["inicio_seg"]) != 0 or previous_end != duration:
        raise ContentBrainError(
            f"A linha do tempo precisa começar em 0 e terminar em {duration} segundos."
        )
    if not isinstance(data["hashtags"], list):
        raise ContentBrainError("O campo hashtags precisa ser uma lista.")
    return True


class ContentBrain:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _generate_with_gemini(self, prompt: str) -> str:
        if not self.settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY não configurada.")
        client = genai.Client(api_key=self.settings.gemini_api_key)
        response = client.interactions.create(
            model=self.settings.gemini_model,
            input=prompt,
        )
        output = getattr(response, "output_text", None)
        if not output:
            raise RuntimeError("Gemini retornou uma resposta vazia.")
        return output

    def _generate_with_groq(self, prompt: str) -> str:
        if not self.settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY não configurada.")
        client = Groq(api_key=self.settings.groq_api_key, max_retries=2)
        response = client.chat.completions.create(
            model=self.settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": "Você é o Content Brain do NOXIS LAB. Retorne somente JSON válido.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=6000,
        )
        output = response.choices[0].message.content
        if not output:
            raise RuntimeError("Groq retornou uma resposta vazia.")
        return output

    def generate(self, request: GenerateContentRequest) -> dict[str, Any]:
        prompt = build_prompt(request)
        errors: list[str] = []

        providers = (
            ("Gemini", self._generate_with_gemini),
            ("Groq", self._generate_with_groq),
        )
        for provider_name, generator in providers:
            try:
                raw = generator(prompt)
                content = parse_json_response(raw)
                valid = validate_content(content, request.duracao)
                content["provedor_ia"] = provider_name
                content["duracao_solicitada"] = request.duracao
                content["validacao_duracao"] = valid
                content.setdefault("identidade", "NOXIS LAB")
                return content
            except Exception as exc:
                errors.append(f"{provider_name}: {exc}")

        raise ContentBrainError(
            "Não foi possível gerar o conteúdo com os provedores configurados. "
            + " | ".join(errors)
        )
