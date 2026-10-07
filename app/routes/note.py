from app.dependencies import get_current_user, get_db
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteResponse, NoteUpdate, NotesResponse
from app.services import get_note_or_404
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

note_router = APIRouter(prefix="/notes", tags=["Notes"])

@note_router.post('', response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    new_note = Note(
        title = payload.title,
        body = payload.body,
        author_id = current_user.id
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note

@note_router.get('/{note_id}', response_model=NoteResponse, status_code=status.HTTP_200_OK)
def get_note(note_id: UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    note = get_note_or_404(db, note_id= note_id, user_id=current_user.id)
    return note

@note_router.get('', response_model=NotesResponse, status_code=status.HTTP_200_OK)
def get_your_notes(db: Session=Depends(get_db), current_user = Depends(get_current_user)):
    query = db.query(Note).filter(Note.author_id == current_user.id)
    total_notes = query.count()
    notes = query.all()
    return {
        "count": total_notes,
        "notes": notes
    }

@note_router.patch('/{note_id}', response_model=NoteResponse)
def update_note(payload: NoteUpdate, note_id: UUID, db: Session= Depends(get_db), current_user = Depends(get_current_user)):
    note = get_note_or_404(db, note_id= note_id, user_id=current_user.id)
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail = "No fields t0 update")
    for key, value in update_data.items():
        setattr(note, key, value)
    db.commit()
    db.refresh(note)
    return note

@note_router.delete('/{note_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    note = get_note_or_404(db, note_id= note_id, user_id=current_user.id)
    db.delete(note)
    db.commit()