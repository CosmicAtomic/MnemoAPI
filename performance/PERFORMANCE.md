# MnemoAPI: Performance Notes

Query-level performance work on the "list my notes" endpoint. All measurements
use PostgreSQL with a seeded dataset of 20,000 notes across 200 users (about
100 notes per user), on a local development machine.

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