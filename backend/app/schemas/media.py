from pydantic import BaseModel, Field


class MediaSearchScene(BaseModel):
    numero: int = Field(ge=1)
    visual: str = Field(default="", max_length=2000)
    narracao: str = Field(default="", max_length=5000)
    termos_busca_pixabay: list[str] | str = Field(default_factory=list)


class MediaSearchRequest(BaseModel):
    cenas: list[MediaSearchScene] = Field(min_length=1, max_length=30)
