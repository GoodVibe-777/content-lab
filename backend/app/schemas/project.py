from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    content: dict = Field(min_length=1)


class MediaSelectionRequest(BaseModel):
    pixabay_id: int = Field(gt=0)
