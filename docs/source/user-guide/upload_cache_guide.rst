Upload Cache Guide
==================

ostruct's upload cache eliminates duplicate file uploads across runs, providing significant performance improvements and cost savings.

How It Works
------------

1. When you attach a file, ostruct computes its SHA-256 hash
2. The cache is checked for this hash
3. If found, the existing OpenAI file ID is reused
4. If not found, the file is uploaded and cached

This means identical files are uploaded exactly once, regardless of:

- How many times you run ostruct
- What names you use for the files
- Which tools (CI, FS) you attach them to

Benefits
--------

- **Performance**: Instant reuse of previously uploaded files
- **Cost Savings**: Reduced API usage and bandwidth
- **Reliability**: Fewer uploads mean fewer potential failures

Configuration
-------------

The upload cache is enabled by default. Configure it in ``ostruct.yaml``:

.. code-block:: yaml

   uploads:
     persistent_cache: true      # Enable/disable cache
     preserve_cached_files: true # Enable TTL-based cache cleanup
     cache_max_age_days: 14      # Cache retention period (days)
     cache_path: null            # Use default path
     hash_algorithm: sha256      # Hash algorithm

Cache Cleanup & TTL Management
------------------------------

**TTL Rationale**: Two-week window covers typical sprint cycles while keeping embedded storage fees <$0.02 per 100MB.

ostruct automatically manages cached files using a Time-To-Live (TTL) system:

- **Default TTL**: 14 days (configurable)
- **Smart Cleanup**: Preserves cached files within TTL, deletes expired ones
- **Cost Control**: Prevents unlimited accumulation of storage costs
- **Privacy Compliance**: Supports immediate deletion for sensitive data

**Configuration Options**:

.. code-block:: yaml

   uploads:
     preserve_cached_files: true  # Enable TTL-based cleanup
     cache_max_age_days: 14      # Files older than this are deleted

**Common TTL Strategies**:

- **Development** (3-7 days): Frequent iterations, cost-conscious
- **Production** (14-30 days): Stability and performance focused
- **Compliance** (0 days): Immediate deletion for sensitive data

**Compliance Mode** (immediate deletion):

.. code-block:: yaml

   uploads:
     preserve_cached_files: false  # Disable preservation
     cache_max_age_days: 0        # Force immediate cleanup

Cache Location
--------------

By default, the cache is stored in platform-specific locations:

- **macOS**: ``~/Library/Caches/ostruct/upload_cache.sqlite``
- **Linux**: ``~/.cache/ostruct/upload_cache.sqlite``
- **Windows**: ``%LOCALAPPDATA%\ostruct\upload_cache.sqlite``

Command Line Options
--------------------

.. code-block:: bash

   # Disable cache for this run
   ostruct run template.j2 schema.json --no-cache-uploads

   # Disable cache preservation (force cleanup)
   ostruct run template.j2 schema.json --no-cache-preserve

   # Use custom cache location
   ostruct run template.j2 schema.json --cache-path ~/.my-cache/uploads.db

Environment Variables
---------------------

.. code-block:: bash

   # Disable cache globally
   export OSTRUCT_CACHE_UPLOADS=false

   # Use custom cache path
   export OSTRUCT_CACHE_PATH=/custom/path/cache.db

   # Use different hash algorithm
   export OSTRUCT_CACHE_ALGO=sha1

   # Configure cache cleanup
   export OSTRUCT_PRESERVE_CACHED_FILES=true
   export OSTRUCT_CACHE_MAX_AGE_DAYS=14

Performance Examples
--------------------

**First run** - uploads files:

.. code-block:: bash

   $ ostruct run analysis.j2 schema.json --file ci:data large_dataset.csv
   # Uploads large_dataset.csv (takes time based on file size)

**Subsequent runs** - reuses cached uploads (instant!):

.. code-block:: bash

   $ ostruct run analysis.j2 schema.json --file ci:data large_dataset.csv
   # Reuses cached upload instantly

The cache works across all file attachments:

- Code Interpreter files (``--file ci:``)
- File Search documents (``--file fs:``)
- Multi-tool attachments (``--file ci,fs:``)

Troubleshooting
---------------

**Cache not working?**

1. Check if cache is enabled: ``ostruct run --help | grep cache``
2. Verify cache location has write permissions
3. Use ``--verbose`` to see cache operations

**Need to clear the cache?**

The cache automatically cleans up expired files based on TTL settings. For manual cleanup:

.. code-block:: bash

   # macOS/Linux
   rm ~/.cache/ostruct/upload_cache.sqlite

   # Windows
   del %LOCALAPPDATA%\ostruct\upload_cache.sqlite

**Files being deleted too soon?**

Check your TTL configuration:

.. code-block:: bash

   # Extend TTL to 30 days
   export OSTRUCT_CACHE_MAX_AGE_DAYS=30

   # Or disable cleanup entirely
   export OSTRUCT_PRESERVE_CACHED_FILES=false

**File changed but ostruct uses old version?**

The cache detects file changes via size and modification time. If a file genuinely changed, it will be re-uploaded automatically.

**Disable cache temporarily:**

.. code-block:: bash

   ostruct run template.j2 schema.json --no-cache-uploads

Technical Details
-----------------

- **Hash Algorithm**: SHA-256 by default (configurable)
- **Database**: SQLite with WAL mode for concurrency
- **File Validation**: Size and mtime checking to detect changes
- **TTL Management**: Automatic cleanup based on file age (14-day default)
- **LRU Behavior**: Last-accessed timestamps for intelligent cleanup
- **Error Handling**: Graceful degradation when cache unavailable
- **404 Recovery**: Automatic cache cleanup when files are manually deleted

Security Considerations
-----------------------

- Cache files are stored with user-only permissions on Unix systems
- File content hashes are computed locally, not sent to OpenAI
- Cache database contains only hashes and OpenAI file IDs, not file content
- No sensitive data is stored in the cache beyond what's already sent to OpenAI

Integration with Tools
----------------------

The upload cache works seamlessly with all ostruct tools:

**Code Interpreter**:

.. code-block:: bash

   # First run uploads
   ostruct run analysis.j2 schema.json --file ci:data dataset.csv

   # Second run reuses cached file
   ostruct run different.j2 schema.json --file ci:analysis dataset.csv

**File Search**:

.. code-block:: bash

   # Cache works across different vector stores
   ostruct run search1.j2 schema.json --file fs:docs manual.pdf
   ostruct run search2.j2 schema.json --file fs:knowledge manual.pdf

**Multi-tool routing**:

.. code-block:: bash

   # Upload once, use in both tools
   ostruct run multi.j2 schema.json --file ci,fs:shared data.json
