import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

def normalize_tags(names: list[str]) -> list[str]:
    cleaned, seen = [], set()
    for name in names:
        name = name.strip().lower()
        if not name:
            continue
        if len(name) > 50:
            raise ValueError("Tag names must be 50 characters or fewer")
        if name not in seen:
            seen.add(name)
            cleaned.append(name)
    return cleaned

class TagResponse(BaseModel):
    id : uuid.UUID
    name: str

    model_config = ConfigDict(from_attributes=True)

class NoteCreate(BaseModel):
    title: str
    body: str
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, v):
        return normalize_tags(v)

class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    body: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None
    
    @field_validator("tags")
    @classmethod
    def clean_tags(cls, v):
        if v is None:
            raise ValueError("Tags cannot be null. Send [] to remove all tags")
        return normalize_tags(v)

    @field_validator("title", "body")
    @classmethod
    def no_explicit_null(cls, v):
        if v is None:
            raise ValueError("This field cannot be null")
        return v

class NoteResponse(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    author_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    tags: list[TagResponse]

    model_config = ConfigDict(from_attributes=True)

class NotesResponse(BaseModel):
    count: int
    notes: list[NoteResponse]