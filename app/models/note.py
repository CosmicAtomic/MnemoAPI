import uuid
from app.database import Base
from app.models.association import note_tags
from sqlalchemy import Column, DateTime, ForeignKey, func, String, UUID
from sqlalchemy.orm import relationship

class Note(Base):
    __tablename__ = "notes"
    id = Column(UUID(as_uuid=True), primary_key= True, default=uuid.uuid4, unique= True)
    title = Column(String, nullable= False)
    body = Column(String, nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable= False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default= func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default= func.now(), onupdate=func.now())

    author = relationship("User", back_populates="notes")
    tags = relationship("Tag", back_populates="notes", passive_deletes=True, secondary=note_tags)
