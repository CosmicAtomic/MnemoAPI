# MnemoAPI: Performance Notes

Query-level performance work, connection-pooling behavior, and transaction
isolation observations. Measurements use PostgreSQL with a seeded dataset of
20,000 notes across 200 users (about 100 notes per user), on a local
development machine.

---

## 1. Indexing

### Setup
Ran `EXPLAIN ANALYZE` on the "list a user's notes" query, sorted by
`created_at` and by `updated_at`, before and after adding indexes. `ANALYZE`
was run after seeding and again after the migration, so planner statistics were
current. Times are Execution Time.

### Change
Added two composite indexes through an Alembic migration:
- `(author_id, created_at)`
- `(author_id, updated_at)`

Each index serves the filter and the sort in a single structure.

### Results

|                   | Before            | After      |
|-------------------|-------------------|------------|
| Scan type         | Seq Scan on notes | Index Scan |
| Sort step         | Top-N heapsort    | None       |
| Time (created_at) | 4.786 ms          | 0.776 ms   |
| Time (updated_at) | 4.343 ms          | 0.776 ms   |

Roughly a 6x improvement on this dataset.

### What changed
Before the indexes, PostgreSQL read every row in the table and then sorted the
matches. After them, it went straight to the user's rows in the index, already
in order, so the sort step disappeared.

### Takeaways
- The plan change (Seq Scan to Index Scan, sort removed) is the stronger
  evidence. The timings are single runs and vary between executions.
- A sequential scan scales with the whole table, while an index lookup does
  not, so the gap should grow with table size. This was not tested here.
- Each index adds a small cost to writes, especially `updated_at`, which
  changes on every edit. I judged that worthwhile because both sort options
  are supported. The write cost was not measured.

### Limitations
- The baseline was no index at all. I did not compare against a plain
  `(author_id)` index, so the added benefit of the composite over a
  single-column index is unmeasured.
- Single runs on a small dataset; treat the timings as indicative.

---

## 2. N+1 Queries

### Setup
Used the "list my notes" endpoint, which returns each note with its tags. SQL
logging (`echo=True`) was enabled and the statements per request were counted,
on the same seeded data.

### The problem
SQLAlchemy loads relationships lazily by default. The endpoint fetched the
notes in one query, then fetched tags separately for each note while the
response was being built. That is an N+1 pattern: 1 query for the list plus N
queries for the tags. No loop in my code caused it. It came from implicit
attribute access during response serialization.

### Results

| Loading strategy | Queries (10 notes) | Queries (100 notes) | Total query time (10 notes) |
|------------------|-------------------:|--------------------:|----------------------------:|
| Lazy (default)   | 13                 | 103                 | ~96 ms                      |
| `joinedload`     | 3                  | 3                   | ~24 ms                      |
| `selectinload`   | 4                  | 4                   | ~47 ms                      |

The 13 queries under lazy loading break down as one user lookup, one count,
one notes query, and ten tag queries (one per note). The first two are fixed
overhead and are not part of the N+1.

Against lazy loading, `selectinload` cut query time roughly in half and
`joinedload` by about three quarters, at 10 notes.

### The fix
Added eager loading to the list query so the tags are fetched up front. With
`selectinload`, one extra query loads the tags for all returned notes at once,
so the query count no longer grows with the number of notes.

### Why `selectinload` over `joinedload`
`joinedload` was faster on this dataset (about 24 ms against 47 ms), so this
choice was made for robustness, not raw speed:
- Notes and tags are many-to-many. A JOIN repeats each note's columns once per
  tag, including the text `body`, which sends duplicated data.
- Joined loading of a collection combined with `LIMIT` forces SQLAlchemy to
  wrap the main query in a subquery to keep the limit correct, which adds
  complexity.
- `selectinload` keeps the main query simple and adds one predictable extra
  query.

As a rule of thumb, `joinedload` fits many-to-one relationships (such as a
note's author), and `selectinload` fits collections.

### Takeaways
- Query count was the problem, not any single query's speed. Each tag query
  was cheap, but the number of them grew with the data.
- The N+1 came from implicit access (serializing the response), not from
  anything written as a loop.

### Limitations
- Timings were taken at 10 notes only and are indicative, not benchmarks.
- `joinedload`'s speed advantage may shrink or reverse with more tags per note
  or larger pages, because every tag duplicates the note's columns. This was
  not measured.
- The constant query count of `selectinload` holds up to its batch size.
  SQLAlchemy splits the `IN` list into batches (500 keys per query by
  default), so a page larger than that would cost more than one tag query.
  Page sizes here are well under that.

### Follow-ups
- Day 7 test: count SQL statements with a `before_cursor_execute` listener and
  assert the count is identical at 10 and at 100 notes.
- Option considered: `lazy="raise"` on `Note.tags`, so any code path that
  forgets to eager-load fails loudly instead of silently running N+1.

---

## 3. Connection Pooling

### Setup
Temporarily configured the SQLAlchemy engine with a single pooled connection,
no overflow connections, and a three-second checkout timeout:

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=1,
    max_overflow=0,
    pool_timeout=3,
)
```

The `/auth/me` route was also temporarily changed to sleep after
`get_current_user` completed:

```python
@jwt_auth.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user)):
    time.sleep(20)
    return current_user
```

This placement matters because `get_current_user` has already executed a
database query by the time `get_me` starts sleeping.

### Request and connection lifetime
The `get_db` dependency creates a SQLAlchemy session and closes it in its
`finally` block:

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

The session checks out a connection when `get_current_user` performs its user
query. FastAPI keeps the dependency context alive until the request finishes,
so the connection remains checked out while `get_me` sleeps. It is returned to
the pool only after the endpoint returns and `get_db` closes the session.

### Results
Two concurrent `/auth/me` requests were sent to a single-worker server with
the temporary pool configuration.

| Request | Result |
|---------|--------|
| Request that acquired the connection | HTTP 200 after about 22 seconds |
| Competing request | HTTP 500 after about 3 seconds |

The server log reported:

```text
sqlalchemy.exc.TimeoutError:
QueuePool limit of size 1 overflow 0 reached,
connection timed out, timeout 3.00
```

The result confirms that the second request cannot obtain a connection while
the first request holds the only pooled connection during its sleep.

### Takeaways
- A SQLAlchemy `Session` is created before a connection is necessarily
  checked out, but the first database query checks out a connection.
- A dependency-held session can retain that connection until the entire
  request completes, including time spent doing non-database work.
- With `pool_size=1` and `max_overflow=0`, concurrent requests are limited to
  one active database connection.
- `pool_timeout` controls how long a request waits for a connection. It does
  not limit endpoint duration or interrupt a request that already owns a
  connection.
- Slow endpoints, sleeps, external calls, or other blocking work after a
  database query can exhaust a small pool and cause `QueuePool` timeouts.

### Limitations
- The reproduction used one server worker. Each worker creates its own engine
  and pool, so multiple workers increase the total number of connections and
  can change contention behavior.
- The test used two concurrent requests and a deliberately small pool; the
  timing demonstrates pool behavior but is not a production capacity
  benchmark.

---

## 4. Transaction Isolation

### Setup
Used two PostgreSQL sessions, A and B, to update and read the same seeded
value under different isolation levels. Session B changed the value to
`CHANGED BY B` and then either held or committed its transaction while session
A repeated the read.

The application remains on PostgreSQL's default `READ COMMITTED` isolation
level.

### Results

| Scenario | What session A saw |
|----------|--------------------|
| `READ COMMITTED`, B updated but had not committed | Original value (`seed 0`) |
| `READ COMMITTED`, B committed | New value (`CHANGED BY B`) |
| `REPEATABLE READ`, B committed | Original value until A finished its transaction |

### Dirty reads
Dirty reads did not occur. Session A never saw session B's uncommitted
change. PostgreSQL accepts `READ UNCOMMITTED`, but implements it with the same
behavior as `READ COMMITTED`, so uncommitted changes remain invisible.

### Non-repeatable reads
At `READ COMMITTED`, each statement obtains a current snapshot. Therefore, the
same `SELECT` can return different values within one transaction:

1. Session A reads the original value.
2. Session B updates the value and commits.
3. Session A repeats the same `SELECT`.
4. Session A sees `CHANGED BY B`.

This is a non-repeatable read.

### Prevention with `REPEATABLE READ`
At `REPEATABLE READ`, session A retains the transaction snapshot it established
at the beginning of its transaction. Even after session B commits, A continues
to see the original value until its transaction ends.

### Takeaways
- PostgreSQL's default `READ COMMITTED` prevents dirty reads.
- `READ COMMITTED` allows a later statement in the same transaction to see
  commits that occurred after an earlier statement.
- `REPEATABLE READ` provides a stable transaction-wide snapshot and prevents
  the observed non-repeatable read.
- `READ UNCOMMITTED` does not provide weaker dirty-read behavior in
  PostgreSQL; it behaves as `READ COMMITTED`.
- `READ COMMITTED` is sufficient for this application because requests use
  short transactions and do not currently require a stable snapshot across
  multiple statements.
- Moving to `REPEATABLE READ` would introduce additional retry handling for
  serialization failures and is not needed for the current request pattern.