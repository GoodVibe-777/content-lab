from typing import Literal

from pydantic import BaseModel, Field


EditorialStyle = Literal[
    "critica_social",
    "psicologia",
    "filosofia",
    "storytelling",
    "educativo",
    "hiphop",
    "motivacional",
]


class GenerateContentRequest(BaseModel):
    tema: str = Field(min_length=3, max_length=500)
    duracao: int = Field(default=45, ge=15, le=180)
    plataforma: str = Field(default="Instagram Reels", max_length=80)
    estilo: EditorialStyle = "critica_social"


class ContentScene(BaseModel):
    numero: int
    inicio_seg: int
    fim_seg: int
    narracao: str
    visual: str
    texto_tela: str
    termos_busca_pixabay: list[str] = Field(default_factory=list)


class ContentStrategy(BaseModel):
    objetivo: str = ""
    publico: str = ""
    abordagem: str = ""


class GeneratedContent(BaseModel):
    tema: str
    identidade: str = "NOXIS LAB"
    estrategia: ContentStrategy
    titulo: str
    gancho: str
    roteiro: str
    cenas: list[ContentScene]
    legenda: str
    hashtags: list[str]
    provedor_ia: str
    duracao_solicitada: int
    validacao_duracao: bool
