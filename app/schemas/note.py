import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class NoteCreate(BaseModel):
    title: str
    body: str

class NoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    body: str | None = Field(default=None, min_length=1)

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

class NotesResponse(BaseModel):
    count: int
    notes: list[NoteResponse]