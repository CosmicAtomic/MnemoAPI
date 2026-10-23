# MnemoAPI

## Performance
- Composite indexes on `(author_id, created_at)` and `(author_id, updated_at)`
  cut the "list my notes" query from about 4.8 ms to about 0.8 ms on a
  20,000-note dataset.
- Switching tag loading from lazy to `selectinload` removed an N+1 pattern:
  13 queries down to 4 for a 10-note page, with a constant count as page size
  grows.
- A single-connection pool with no overflow caused a competing `/auth/me`
  request to fail after the three-second checkout timeout while the first
  request slept for 20 seconds.
- PostgreSQL `READ COMMITTED` prevented dirty reads but allowed a
  non-repeatable read; `REPEATABLE READ` preserved the original snapshot.

Details and caveats: [performance/PERFORMANCE.md](performance/PERFORMANCE.md)