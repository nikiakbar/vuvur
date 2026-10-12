# Possible Improvements

## Scanner Optimizations (Deferred)

### #2: Skip Unchanged Directories ⚡ HIGH IMPACT
**Problem**: Every periodic scan walks the entire filesystem even if nothing changed.

**Solution**: Cache directory mtimes. Skip directories that haven't changed since last scan.

```python
# Add to scan() function
dir_mtime_cache = {}  # Load from file: {dir_path: mtime}

for root, dirs, files in os.walk(GALLERY_PATH):
    dir_mtime = os.stat(root).st_mtime
    if root in dir_mtime_cache and dir_mtime == dir_mtime_cache[root]:
        dirs[:] = []  # Skip subdirectories
        continue  # Skip this directory
    dir_mtime_cache[root] = dir_mtime
```

**Expected gain**: 10-50x faster periodic scans when no new files (3 min → 5-30 sec)

**Implementation notes**:
- Persist cache to `/app/data/dir_mtime_cache.json`
- Only works for full scans (limit=None)
- Directory mtime changes when files are added/removed/modified inside it

---

### #3: Connection Pooling 🔄 LOW IMPACT
**Problem**: `process_single_file()` opens a new connection for every file watched by the real-time watcher.

**Solution**: Use thread-local connections to reuse database connections per thread.

```python
import threading

_thread_local = threading.local()

def get_thread_connection():
    if not hasattr(_thread_local, 'conn'):
        _thread_local.conn = sqlite3.connect(DB_PATH)
    return _thread_local.conn
```

**Expected gain**: 50-100ms saved per watched file event

**When it matters**:
- Bulk file operations (copying 100+ files into gallery)
- Real-time scanning while actively working
- High-frequency file creation (ComfyUI rendering batches)

---

### #6: FTS Index Optimization 🔍 MEDIUM IMPACT
**Problem**: If FTS5 search is enabled, large batch inserts can cause index rebuilds that block reads.

**Solution**: Run `PRAGMA optimize` after large scans to rebuild FTS index efficiently.

```python
# After scan completes
if total_processed_count > 1000:
    conn.execute("PRAGMA optimize")
    conn.commit()
```

**Expected gain**: Better API responsiveness during scans, faster search queries

---

## API Optimizations (To Be Analyzed)

### 1. Response Compression - MEDIUM IMPACT
**Problem**: Gallery API returns large JSON payloads (20-100 items with EXIF data per request).

**Current**: No compression enabled
**Solution**: Enable gzip compression in Flask/Gunicorn

```python
# In main.py or as middleware
from flask_compress import Compress
Compress(app)
```

Or in Gunicorn:
```bash
gunicorn --workers 2 --compression gzip ...
```

**Expected gain**: 60-80% smaller responses for JSON, faster page loads

---

### 2. HTTP Caching Headers - HIGH IMPACT
**Problem**: Thumbnails serve with max_age=31536000 (1 year) but gallery API responses have no caching.

**Current state**:
- Thumbnails: Excellent caching (1 year)
- Gallery API: No cache headers
- Stream endpoint: No cache headers

**Solution**: Add conditional caching for gallery responses

```python
# For immutable resources (thumbnails - already done)
response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'

# For gallery list (cache for 30s, revalidate)
response.headers['Cache-Control'] = 'public, max-age=30, must-revalidate'
response.headers['ETag'] = hash_of_results

# For media stream (private, cache 1 hour)
response.headers['Cache-Control'] = 'private, max-age=3600'
```

**Expected gain**: 50-90% reduction in API load for repeated requests

---

### 3. Database Connection Pooling - MEDIUM IMPACT
**Problem**: Each request opens/closes a database connection via get_db() and conn.close().

**Current**: New connection per request
**Solution**: Use SQLite connection pool or Flask-SQLAlchemy

```python
# Simple approach: Thread-local connections
from contextlib import contextmanager
import threading

_thread_local = threading.local()

@contextmanager
def get_db():
    if not hasattr(_thread_local, 'conn'):
        _thread_local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _thread_local.conn.row_factory = sqlite3.Row
    yield _thread_local.conn
    # Don't close - reuse for thread lifetime
```

**Expected gain**: 10-50ms saved per request

---

### 4. Lazy EXIF Parsing - LOW IMPACT
**Problem**: Gallery endpoint decodes EXIF JSON for ALL items, even if client doesn't need it.

**Current**: Always decodes exif field in /api/gallery
**Solution**: Add ?include_exif=true query param, default to excluding it

```python
include_exif = request.args.get("include_exif", "false").lower() == "true"

if include_exif and item.get("exif"):
    item["exif"] = json.loads(item["exif"])
else:
    item.pop("exif", None)  # Remove from response
```

**Expected gain**: 30-50% smaller response payloads when EXIF not needed

---

### 5. Index Optimization - HIGH IMPACT
**Problem**: Check if composite indexes are being used effectively.

**Current**: Already has Late Row Lookup optimization
**Analysis needed**:
- Run EXPLAIN QUERY PLAN on common queries
- Check if idx_media_group_mtime is used for date sorting with group filter
- Verify FTS index performance for search queries

```sql
-- Check index usage
EXPLAIN QUERY PLAN 
SELECT * FROM media WHERE group_tag = 'vids' ORDER BY mtime DESC LIMIT 20;

-- Verify FTS performance
EXPLAIN QUERY PLAN
SELECT * FROM media 
JOIN media_fts f ON media.id = f.rowid 
WHERE media_fts MATCH 'prompt*' LIMIT 20;
```

**Expected gain**: Ensure queries run in <50ms for 172k records

---

### 6. Thumbnail Generation Queue - LOW IMPACT
**Problem**: Thumbnail generation uses a semaphore (4 slots) and fast-fails when busy.

**Current**: Good design with timeout + placeholder
**Enhancement**: Add background worker pool for precomputation (already exists in scanner)

**Status**: Already optimized! Scanner precomputes thumbnails during idle time.

---

### 7. Stream Endpoint Optimization - MEDIUM IMPACT
**Problem**: No caching headers, opens file handle per chunk.

**Current**: Byte-range support, no caching
**Solution**: Add caching and optimize file reads

```python
# Add cache headers
response.headers['Cache-Control'] = 'private, max-age=3600'
response.headers['ETag'] = f'"{media_id}-{file_mtime}"'

# Support If-None-Match for 304 responses
if_none_match = request.headers.get('If-None-Match')
if if_none_match == f'"{media_id}-{file_mtime}"':
    return Response(status=304)
```

**Expected gain**: Browsers cache videos, reduce bandwidth 80%+

---

### 8. Worker Configuration - LOW IMPACT
**Current**: 2 Gunicorn workers (gevent mode), 300s timeout

**Analysis**:
- gevent mode is good for I/O-bound workloads (thumbnails, streaming)
- 2 workers might be low for high traffic
- 300s timeout is good for long scans

**Recommendation**: Monitor worker utilization. If CPU usage is low (<50%) but requests are slow, increase workers to 4.

```bash
gunicorn -w 4 -k gevent --worker-connections 1000 ...
```

**Expected gain**: Better concurrency for multiple clients

---

### 9. Preload Frequently Accessed Data - LOW IMPACT
**Problem**: Group list is queried on every gallery load.

**Solution**: Cache group tags in memory, refresh every 60s

```python
import time

_group_cache = {"data": [], "timestamp": 0}

def get_groups():
    now = time.time()
    if now - _group_cache["timestamp"] > 60:
        conn = get_db()
        _group_cache["data"] = [row["group_tag"] for row in conn.execute("SELECT DISTINCT group_tag FROM media")]
        _group_cache["timestamp"] = now
        conn.close()
    return _group_cache["data"]
```

**Expected gain**: Eliminate 1 query per gallery page load

---

## Priority Ranking (API)

1. **#2 HTTP Caching Headers** - Biggest impact, easy to implement
2. **#1 Response Compression** - 60-80% bandwidth savings
3. **#7 Stream Endpoint Caching** - Reduce video bandwidth dramatically
4. **#3 Database Connection Pooling** - Reduce per-request overhead
5. **#5 Index Analysis** - Verify performance is optimal
6. **#4 Lazy EXIF Parsing** - Optional enhancement
7. **#9 Group Cache** - Micro-optimization
8. **#8 Worker Tuning** - Monitor first, tune if needed

---

## Performance Baseline (172k files)

### Current Scanner Performance
- **Memory**: 70 MiB idle, ~120 MiB during scan (optimized)
- **Discovery time**: 183 seconds (3 min 3s) with 4 parallel workers
- **Full scan**: ~183s when no changes detected
- **Bottleneck**: Two large directories (50k files each) dominate scan time

### Current API Performance
- **Memory**: 71 MiB per worker (2 workers = 142 MiB total)
- **Worker mode**: Gunicorn + gevent (I/O optimized)
- **Thumbnail caching**: Excellent (1 year max-age)
- **Thumbnail generation**: Semaphore-limited with fast-fail
- **Gallery query**: Late Row Lookup optimization
- **Missing**: Response compression, HTTP caching, connection pooling
