# Indexing and Query Optimization

## Setup
Seeded PostgreSQL with 20,000 notes across 200 users (about 100 notes per user).
Ran `EXPLAIN ANALYZE` on the "list a user's notes" query, sorted by `created_at`
and by `updated_at`, before and after adding indexes. `ANALYZE` was run after
seeding and again after the migration, so planner statistics were current.
Times below are Execution Time.

## Change
Added two composite indexes through an Alembic migration:
- `(author_id, created_at)`
- `(author_id, updated_at)`

Each index serves the filter and the sort in a single structure.

## Results

|                    | Before                | After      |
|--------------------|-----------------------|------------|
| Scan type          | Seq Scan on notes     | Index Scan |
| Sort step          | Top-N heapsort        | None       |
| Time (created_at)  | 4.786 ms              | 0.776 ms   |
| Time (updated_at)  | 4.343 ms              | 0.776 ms   |

That is roughly a 6x improvement on this dataset.

## What changed
Before the indexes, PostgreSQL read every row in the table and then sorted the
matches. After them, it went straight to the user's rows in the index, already
in order, so the sort step disappeared.

## Takeaways
- The plan change (Seq Scan to Index Scan, sort removed) is the stronger
  evidence. The timings are single runs and vary between executions.
- A sequential scan scales with the whole table, while an index lookup does
  not, so the gap should grow with table size. This was not tested here.
- Each index adds a small cost to writes, especially `updated_at`, which changes
  on every edit. I judged that worthwhile because both sort options are
  supported. The write cost was not measured.

## Limitations
- The baseline was no index at all. I did not compare against a plain
  `(author_id)` index, so the added benefit of the composite over a
  single-column index is unmeasured.
- Single runs on a small dataset; treat the timings as indicative, not precise.