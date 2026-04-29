## 2025-05-15 - [Database Indexing for Sorting]
**Learning:** SQLite's `EXPLAIN QUERY PLAN` is essential for verifying that sorting operations use indexes. Adding an index on `mtime` and `filename` eliminates the expensive `USE TEMP B-TREE FOR ORDER BY` step, which is critical for large media galleries.
**Action:** Always check the query plan for frequently used sort/filter combinations.

## 2025-05-15 - [SQL vs Python for Path Processing]
**Learning:** Fetching thousands of file paths to extract directory names in Python is a significant bottleneck. Offloading string manipulation (`substr`, `instr`) to SQL and using `DISTINCT` reduces memory overhead and latency by orders of magnitude.
**Action:** Prioritize SQL-based data reduction over Python-based processing for large collections of records.

## 2025-05-15 - [Viewer Virtualization Bottleneck]
**Learning:** Rendering all media items in a scrolling viewer simultaneously creates a massive DOM and overhead for React's reconciliation, especially as the gallery grows. Even with CSS scroll snapping, the number of component instances can reach hundreds, degrading performance.
**Action:** Implement windowing/virtualization to only render the current item and its immediate neighbors, significantly reducing DOM nodes and memory usage.

## 2025-05-15 - [SQLite FTS5 vs LIKE for Search]
**Learning:** Using `LIKE '%term%'` on large text columns causes a full table scan. SQLite's FTS5 virtual table provides O(log N) search performance. Additionally, ensure SQL placeholders and binding parameters match to avoid runtime `ProgrammingError`.
**Action:** Always prefer FTS5 for search functionality and verify query binding counts during optimization.

## 2026-04-09 - [Optimizing Random Selection and Caching]
**Learning:** Using `ORDER BY RANDOM()` on large tables is slow because it sorts full rows in memory. The "Late Row Lookup" pattern (sorting IDs in a subquery and joining) significantly improves performance. Additionally, enabling browser caching for thumbnails and using `decoding="async"` for images reduces perceived latency and main-thread blocking.
**Action:** Always use Late Row Lookup for random selection on tables with large blobs, and leverage browser-level optimizations for asset loading.

## 2026-04-15 - [Composite Indexing for Sorted Filtering]
**Learning:** While single-column indexes on `group_tag` and `mtime` are helpful, they don't prevent a "filesort" (temporary B-tree) when both are used together. A composite index `(group_tag, mtime DESC)` allows SQLite to perform both the filter and the sort using only the index, which is critical for smooth gallery performance.
**Action:** Create composite indexes for the most common "filter + sort" combinations in the UI.

## 2026-04-15 - [Ubiquitous Late Row Lookup]
**Learning:** Extending the Late Row Lookup pattern from just `RANDOM()` to ALL sorted and paginated queries consistently reduces memory pressure. Since the gallery queries often fetch many records before applying `LIMIT`, keeping the sorted working set restricted to only IDs ensures that large EXIF JSON strings aren't loaded until the final page of results is ready.
**Action:** Use Late Row Lookup for all paginated queries on tables with large columns, regardless of the sort order.

## 2026-04-29 - [Optimizing Metadata Retrieval for Assets]
**Learning:** Using `SELECT *` in helper functions can inadvertently fetch massive columns (like `exif` blobs) that are not needed for simple tasks like serving thumbnails or streaming. This increases disk I/O and serialization overhead.
**Action:** Always explicitly select only the necessary columns in data retrieval helpers, especially in performance-critical paths like asset serving.
