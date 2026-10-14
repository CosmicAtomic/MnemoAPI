import random
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models.user import User
from app.models.note import Note
from app.services import get_or_create_tags

NUM_USERS = 200
NOTES_PER_USER = 100
TAG_NAMES = [f"tag{i}" for i in range(20)]


def seed():
    db = SessionLocal()
    try:
        tags = get_or_create_tags(db, TAG_NAMES)
        db.add_all(tags)
        db.flush()

        users = [
            User(email=f"seed{i}@seed.test", hashed_password="not-a-real-hash")
            for i in range(NUM_USERS)
        ]
        db.add_all(users)
        db.flush()

        now = datetime.now(timezone.utc)
        for user in users:
            notes = []
            for n in range(NOTES_PER_USER):
                created = now - timedelta(minutes=random.randint(0, 60 * 24 * 365))
                minutes_left = int((now - created).total_seconds() / 60)
                updated = created + timedelta(minutes=random.randint(0, minutes_left))
                notes.append(
                    Note(
                        title=f"Seed note {n}",
                        body="Seeded body text " * 5,
                        author_id=user.id,
                        created_at=created,
                        updated_at=updated,
                        tags=random.sample(tags, k=random.randint(0, 3)),
                    )
                )
            db.add_all(notes)

        db.commit()
        print(f"Seeded {NUM_USERS} users and {NUM_USERS * NOTES_PER_USER} notes")
    finally:
        db.close()


if __name__ == "__main__":
    seed()