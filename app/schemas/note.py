import uuid
from datetime import datetime
from pydantic import BaseModel

class NoteCreate(BaseModel):
    title: str
    body: str

class NoteUpdate(BaseModel):
    title: str | None = None
    body: str | None = None

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