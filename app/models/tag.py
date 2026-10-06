import uuid
from app.database import Base
from app.models.association import note_tags
from sqlalchemy import Column, String, UUID
from sqlalchemy.orm import relationship

class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default= uuid.uuid4)
    name = Column(String, unique=True, nullable=False)

    notes = relationship("Note", back_populates="tags", passive_deletes= True, secondary=note_tags)