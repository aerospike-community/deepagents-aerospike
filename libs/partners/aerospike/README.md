# deepagents-aerospike

Wire Aerospike as a LangGraph checkpointer for Deep Agents, with persistent
thread state and optional per-record TTL expiry through existing LangGraph
integration points. This package currently provides checkpoint persistence only,
not a `BaseStore` or `StoreBackend` factory for cross-thread memory.

## Quick Start

1. **Start Aerospike server (local dev)**

   ```bash
   docker run --rm --ulimit nofile=15000:15000 -p 127.0.0.1:3000:3000 aerospike/aerospike-server
   ```

   Use an existing namespace (`test` in the default server configuration).
   For positive record TTLs, configure a nonzero `nsup-period` for that namespace.

2. **Install the package**

   The current development configuration uses editable sibling checkouts of
   `langgraph-aerospike` and `aerospike-client-python-sdk`, alongside this
   `deepagents` checkout. These paths are declared in `pyproject.toml`; this
   is not yet a standalone installation from released dependencies.

   ```bash
   cd /path/to/deepagents/libs/partners/aerospike
   uv sync --all-groups
   ```

3. **Use with deepagents**

   ```python
   from deepagents import create_deep_agent
   from deepagents_aerospike import create_aerospike_checkpointer

   checkpointer = create_aerospike_checkpointer(
       host="localhost",
       port=3000,
       namespace="test",
   )

   try:
       agent = create_deep_agent(
           model="claude-sonnet-4-6",
           checkpointer=checkpointer,
       )

       agent.invoke(
           {"messages": [{"role": "user", "content": "Hello"}]},
           config={"configurable": {"thread_id": "user-123"}},
       )
   finally:
       checkpointer.close()
   ```

## How It Works

- One-time connection: `create_aerospike_checkpointer` opens a single Aerospike client connection and hands it to `AerospikeSaver`. That session is reused for every `put`, `get_tuple`, and list operation, so checkpoint reads stay fast and do not open a new socket per call.
- Automatic indexing: `AerospikeSaver` creates `thread_id` secondary indexes on its checkpoint sets the first time it is instantiated. If another instance is created against the same namespace, it finds the indexes already exist and proceeds normally — index setup is idempotent.
- TTL-based expiry: if you pass `ttl_minutes`, checkpoint records expire automatically after that many minutes. When omitted, the namespace's default TTL applies. Reads do not refresh TTL by default.
- Explicit lifecycle: reuse the returned saver across agent invocations and close it when finished. Initialization failures close the connection before propagating the original exception.

## Advanced Usage

Users needing advanced options — a TLS-configured session, custom serialization,
custom set names, or `refresh_on_read` sliding TTL — should construct
`AerospikeSaver` directly from `langgraph.checkpoint.aerospike`. Configure TLS
on the SDK connection, not on the saver. The `create_aerospike_checkpointer`
factory exposes only the common case.

## Testing

Run unit tests (no network required):

```bash
make test
```

Run integration tests (requires a running Aerospike server):

```bash
make integration_test
```

Set `AEROSPIKE_HOST`, `AEROSPIKE_PORT`, and `AEROSPIKE_NAMESPACE` to override
the defaults (`localhost`, `3000`, and `test`). Use a dedicated test namespace:
tests create checkpoint indexes and delete only their own randomly named threads.
An unreachable server skips the suite; a successful live verification must show
passed tests, not skips. The agent tests use a deterministic local model and do
not need model API keys.

Run formatting, linting, and type checking:

```bash
make format lint
```

Benchmarks are maintained separately from this package in the
`aerospike-benchmarks` repository's `deepagents/` directory.

## License

MIT
