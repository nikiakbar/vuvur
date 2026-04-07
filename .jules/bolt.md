## 2025-05-15 - [Database Indexing for Sorting]
**Learning:** SQLite's `EXPLAIN QUERY PLAN` is essential for verifying that sorting operations use indexes. Adding an index on `mtime` and `filename` eliminates the expensive `USE TEMP B-TREE FOR ORDER BY` step, which is critical for large media galleries.
**Action:** Always check the query plan for frequently used sort/filter combinations.

## 2025-05-15 - [SQL vs Python for Path Processing]
**Learning:** Fetching thousands of file paths to extract directory names in Python is a significant bottleneck. Offloading string manipulation (`substr`, `instr`) to SQL and using `DISTINCT` reduces memory overhead and latency by orders of magnitude.
**Action:** Prioritize SQL-based data reduction over Python-based processing for large collections of records.

## 2025-05-15 - [Virtualization in Scroll-Snapping Containers]
**Learning:** Eagerly rendering hundreds of media items in a full-screen viewer causes excessive memory usage and network congestion. Implementing a sliding window virtualization (rendering only the current item and its immediate neighbors) while maintaining the scroll container's total height and snap points preserves the UX while dramatically improving performance.
**Action:** Use conditional rendering for expensive components in large lists/carousels, ensuring the wrapper layout remains consistent to avoid breaking scroll snapping.
