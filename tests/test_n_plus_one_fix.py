from contextlib import contextmanager
from sqlalchemy import event


@contextmanager
def count_queries(engine):
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


async def create_notes(client, auth_headers, how_many, offset=0):
    ids = []
    for i in range(offset, offset + how_many):
        response = await client.post(
            "/notes",
            json={
                "title": f"nplus1 note {i}",
                "body": "body",
                "tags": [f"nplus1-tag-{i}", "nplus1-shared"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        ids.append(response.json()["id"])
    return ids


async def test_list_notes_query_count_does_not_grow(client, auth_headers, db_session):
    engine = db_session.get_bind()
    created_ids = []
    try:
        created_ids += await create_notes(client, auth_headers, 3)
        db_session.expire_all()

        with count_queries(engine) as small:
            small_response = await client.get("/notes", headers=auth_headers)

        created_ids += await create_notes(client, auth_headers, 7, offset=3)
        db_session.expire_all()

        with count_queries(engine) as large:
            large_response = await client.get("/notes", headers=auth_headers)

        assert small_response.status_code == 200
        assert large_response.status_code == 200
        assert any(n["tags"] for n in large_response.json()["notes"])
        assert len(small) > 0
        assert len(large) == len(small), (
            f"Query count grew with data: {len(small)} -> {len(large)}"
        )
    finally:
        for note_id in created_ids:
            await client.delete(f"/notes/{note_id}", headers=auth_headers)