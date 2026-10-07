from app.models.note import Note
from app.models.user import User
from fastapi import  HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

def get_user_by_email(db: Session, email):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: UUID):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_github_id(db: Session, github_id):
    return db.query(User).filter(User.github_id == str(github_id)).first()

def get_user_by_google_id(db: Session, google_id):
    return db.query(User).filter(User.google_id == str(google_id)).first()

def get_note_by_id(db: Session, note_id: UUID):
    return db.query(Note).filter(Note.id == str(note_id)).first()

def get_note_or_404(db:Session, note_id: UUID, user_id: UUID):
    note = get_note_by_id(db, note_id)
    if not note or note.author_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note