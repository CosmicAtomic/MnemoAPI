import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.note import Note
from app.models.tag import Tag
from app.models.association import note_tags


async def test_create_note_rolls_back_everything_on_failure(client, auth_headers, db_session, monkeypatch):
    # Force a failure AFTER the data has been sent to PostgreSQL
    # but BEFORE the real commit happens.
    def failing_commit(self):
        self.flush()
        raise RuntimeError("deliberate failure")

    monkeypatch.setattr(Session, "commit", failing_commit)

    links_before = db_session.execute(select(func.count()).select_from(note_tags)).scalar()

      # 1. FIX: Tell pytest to expect the deliberate crash here
    with pytest.raises(RuntimeError, match="deliberate failure"):
        await client.post(
            "/notes",
            json={
                "title": "TRANSACTION TEST",
                "body": "should never persist",
                "tags": ["rollbacktest"],
            },
            headers=auth_headers,
        )

    monkeypatch.undo()  # restore the real commit before checking

    # Check with the test's own session, not the request's
    db_session.rollback()  # make sure we see fresh data
    assert db_session.query(Note).filter(Note.title == "TRANSACTION TEST").count() == 0
    assert db_session.query(Tag).filter(Tag.name == "rollbacktest").count() == 0
    links_after = db_session.execute(select(func.count()).select_from(note_tags)).scalar()
    assert links_after == links_before