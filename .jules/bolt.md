## 2025-05-15 - [Database Indexing for Sorting]
**Learning:** SQLite's `EXPLAIN QUERY PLAN` is essential for verifying that sorting operations use indexes. Adding an index on `mtime` and `filename` eliminates the expensive `USE TEMP B-TREE FOR ORDER BY` step, which is critical for large media galleries.
**Action:** Always check the query plan for frequently used sort/filter combinations.

## 2025-05-15 - [SQL vs Python for Path Processing]
**Learning:** Fetching thousands of file paths to extract directory names in Python is a significant bottleneck. Offloading string manipulation (`substr`, `instr`) to SQL and using `DISTINCT` reduces memory overhead and latency by orders of magnitude.
**Action:** Prioritize SQL-based data reduction over Python-based processing for large collections of records.
