# MnemoAPI

## Performance
Composite indexes on `(author_id, created_at)` and `(author_id, updated_at)` cut
the "list my notes" query from about 4.8 ms to about 0.8 ms on a 20,000-note
dataset. Details: [performance/INDEXING.md](performance/INDEXING.md)