from app.database import Base
from sqlalchemy import Column, ForeignKey, Table

note_tags = Table(
    "note_tags", Base.metadata,
    Column("note_id", ForeignKey("notes.id", ondelete= "CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete= "CASCADE"), primary_key=True),
)