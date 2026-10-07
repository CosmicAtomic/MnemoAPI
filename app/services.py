from app.models.note import Note
from app.models.user import User
from sqlalchemy.orm import Session

def get_user_by_email(db: Session, email):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id):
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_github_id(db: Session, github_id):
    return db.query(User).filter(User.github_id == str(github_id)).first()

def get_user_by_google_id(db: Session, google_id):
    return db.query(User).filter(User.google_id == str(google_id)).first()

def get_note_by_id(db: Session, note_id):
    return db.query(Note).filter(Note.id == str(note_id)).first()