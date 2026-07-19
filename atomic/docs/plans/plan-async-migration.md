# Plan: Async AtomicCore — Production-Ready Postgres for Public Deployment

## Goal

Deploy a public-facing Atomic instance backed by Postgres. Users without tokens get scoped read access; authenticated users get full access. This plan addresses the **scalability prerequisite**: making the server handle concurrent public traffic without exhausting threads or connections.

Auth, multi-tenancy, and access scoping are separate concerns — they depend on this work being done first.

## Why Async Is the Bottleneck

Every database call currently flows through a sync→async bridge:

```
actix route handler (async)
  → web::block() (move to threadpool)
    → AtomicCore sync method
      → dispatch! macro
        → Postgres: block_on() on PG_RUNTIME (spawn thread, block on future)
        → SQLite: direct sync call
```

For a single-user desktop app with SQLite, this is fine. For a public server with Postgres and N concurrent users:

1. **Thread exhaustion** — Each request occupies a threadpool thread (from `web::block`) AND spawns another thread for the `block_on` bridge. With actix's default threadpool, ~20 concurrent requests saturate the system.
2. **Connection waste** — Each `block_on` call acquires a Postgres connection, blocks a thread waiting for I/O, then releases. No pipelining. A single request that makes 5 sequential DB calls holds a thread for 5× the actual I/O time.
3. **Latency overhead** — ~100μs per call from thread spawning/joining, compounding across sequential DB calls within a request.

After the migration, the same request path becomes:

```
actix route handler (async)
  → AtomicCore async method
    → StorageBackend async dispatch
      → Postgres: sqlx future runs directly on actix's tokio runtime
      → SQLite: spawn_blocking (one threadpool hop)
```

Zero thread coordination for Postgres. The sqlx connection pool handles concurrency natively. A request making 5 DB calls uses one task on the async runtime, not 5 blocked threads.

## Current State (as of codebase analysis)

| Component | Count | Description |
|-----------|-------|-------------|
| `dispatch!` macro methods | ~110 | Sync bridge wrappers in `storage/mod.rs` |
| `pub fn` on AtomicCore | 111 | Sync public API methods in `lib.rs` |
| `pub async fn` on AtomicCore | 14 | Already-async methods (search, chat, wiki, etc.) |
| `web::block()` in routes | 20 | Across 9 route files |
| `blocking_ok` usage | 11 files | Helper that wraps `web::block` + error mapping |
| `as_sqlite()` bypass paths | 4 files | Special-case branches avoiding the storage trait |
| Storage traits | All async | `#[async_trait]` — the target interface already exists |

## Migration Steps

### Step 1: Make AtomicCore Methods Async

Convert 111 `pub fn` methods to `pub async fn`. Method bodies stay the same — they still call the sync dispatch methods. The `async` keyword is preparation so that callers can be updated.

The 14 already-async methods stay as-is. Reconcile any naming inconsistencies (some call dispatch methods, some bypass to `as_sqlite()`).

```rust
// Before
pub fn get_atom(&self, id: &str) -> Result<Option<AtomWithTags>> {
    self.storage.get_atom_impl(id)
}

// After
pub async fn get_atom(&self, id: &str) -> Result<Option<AtomWithTags>> {
    self.storage.get_atom_impl(id)  // Still sync dispatch for now
}
```

**Files:** `crates/atomic-core/src/lib.rs`

### Step 2: Update Server Route Handlers

Remove `web::block()` wrappers and `blocking_ok` helper. Since AtomicCore methods are now async, handlers `.await` them directly.

```rust
// Before
pub async fn get_atom(db: Db, path: web::Path<String>) -> HttpResponse {
    let id = path.into_inner();
    let core = db.0;
    match web::block(move || core.get_atom(&id)).await {
        Ok(Ok(Some(atom))) => HttpResponse::Ok().json(atom),
        ...
    }
}

// After
pub async fn get_atom(db: Db, path: web::Path<String>) -> HttpResponse {
    match db.0.get_atom(&path.into_inner()).await {
        Ok(Some(atom)) => HttpResponse::Ok().json(atom),
        ...
    }
}
```

**Files:** All files in `crates/atomic-server/src/routes/`, `crates/atomic-server/src/error.rs`

### Step 3: Replace Dispatch Macro with Async Routing

Replace the ~110 `dispatch!` methods with async methods on `StorageBackend`. SQLite wraps in `spawn_blocking`; Postgres calls the trait directly.

```rust
impl StorageBackend {
    pub async fn get_atom(&self, id: &str) -> Result<Option<AtomWithTags>> {
        match self {
            StorageBackend::Sqlite(s) => {
                let s = s.clone();
                let id = id.to_string();
                tokio::task::spawn_blocking(move || s.get_atom_impl(&id))
                    .await
                    .map_err(|e| AtomicCoreError::DatabaseOperation(e.to_string()))?
            }
            #[cfg(feature = "postgres")]
            StorageBackend::Postgres(s) => {
                <PostgresStorage as AtomStore>::get_atom(s, id).await
            }
        }
    }
}
```

This is the step that eliminates the performance bottleneck. After this, Postgres calls run natively on the async runtime.

**Files:** `crates/atomic-core/src/storage/mod.rs`

### Step 4: Update Internal Async Modules

The embedding pipeline, agent, wiki, and search modules are already async but call `_sync` dispatch methods. Switch them to `.await` the new async `StorageBackend` methods.

```rust
// Before (embedding.rs)
storage.claim_pending_embeddings_sync(PENDING_BATCH_SIZE)?;

// After
storage.claim_pending_embeddings(PENDING_BATCH_SIZE).await?;
```

**Files:**
- `crates/atomic-core/src/embedding.rs`
- `crates/atomic-core/src/agent.rs`
- `crates/atomic-core/src/wiki/mod.rs`, `wiki/centroid.rs`, `wiki/agentic.rs`
- `crates/atomic-core/src/search.rs`

### Step 5: Remove Backend-Specific Bypass Paths

4 files use `as_sqlite()` / `as_postgres()` to branch around the storage trait. With async dispatch these branches are unnecessary — both backends go through the same async interface.

Remove `as_sqlite()`, `as_postgres()`, and `sqlite_db()` from `StorageBackend`. Unify to a single code path everywhere.

**Files:**
- `crates/atomic-core/src/lib.rs`
- `crates/atomic-core/src/agent.rs`
- `crates/atomic-core/src/manager.rs`
- `crates/atomic-core/src/storage/mod.rs`

### Step 6: Cleanup

- Remove `PG_RUNTIME` static and `block_on` / `pg_runtime_block_on` functions
- Remove the `dispatch!` macro definition
- Remove `_sync` and `_impl` suffixed methods from `SqliteStorage` (keep only async trait impls with `spawn_blocking` internally)
- Evaluate whether `executor::BACKGROUND` runtime is still needed — background tasks could run on the caller's tokio runtime now
- Clean up unused imports

**Files:** `crates/atomic-core/src/storage/mod.rs`, `storage/sqlite/*.rs`, `crates/atomic-core/src/executor.rs`

## Execution Order

```
Step 1 (AtomicCore async) ──→ Step 2 (Routes — can parallel with 3)
         │
         └──────────────────→ Step 3 (Async dispatch — can parallel with 2)
                                      │
                                      └──→ Step 4 (Internal modules)
                                                    │
                                                    └──→ Step 5 (Remove bypass paths)
                                                                  │
                                                                  └──→ Step 6 (Cleanup)
```

## What Stays The Same

- **Storage trait definitions** (`traits.rs`) — already async
- **PostgresStorage implementations** — already async
- **Frontend** — HTTP/WebSocket API unchanged
- **Tauri desktop** — uses sidecar HTTP, no AtomicCore calls
- **iOS app** — HTTP client, unaffected

## Verification

1. `cargo test --workspace` — all tests pass with `.await` additions
2. `cargo test -p atomic-core --test storage_tests --features postgres` — parameterized storage tests pass on Postgres
3. Load test: measure p50/p99 latency of `/api/atoms` under 50 concurrent connections, SQLite vs Postgres, before vs after
4. Confirm thread count under load drops significantly (no more per-call thread spawning)

## What Comes After (Not In Scope)

Once async is done, the server is ready for public deployment work:

- **Public access scoping** — unauthenticated read access to specific databases/tags
- **Connection pool tuning** — `PgPoolOptions::max_connections` sized for expected concurrency
- **Rate limiting** — per-IP or per-token request limits for public endpoints
- **Horizontal scaling** — multiple instances sharing one Postgres, WebSocket events via Redis pub/sub
- **Caching** — in-memory TTL cache for hot data (tag tree, settings) to reduce DB round-trips
