# HTTP and MCP API

The HTTP API, MCP tools, and web UI share the same document/indexing service. Use the base URLs for the selected [Compose profile](../README.md#quick-start). These examples use Bash, curl, and Python 3 and must run in the same shell session.

## Select endpoints

<!-- api-example:endpoints -->
```bash
export BASE_URL="http://127.0.0.1:${POSTGRES_APP_PORT:-8080}"
export MCP_URL="http://127.0.0.1:${POSTGRES_MCP_PORT:-8081}/mcp"
# For Qdrant, use QDRANT_APP_PORT (default 8082) and QDRANT_MCP_PORT (default 8083).
```

All HTTP document/search endpoints accept JSON via POST. Successful responses are JSON with HTTP 200. No endpoint fetches the content of `source_uri`: it is stored as source metadata. Supply the text in `content`.

## Add information

<!-- api-example:insert -->
```bash
response=$(curl --fail-with-body --silent --show-error "$BASE_URL/api/documents/upsert" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Backup retention","source_uri":"manual:backup-retention","source_type":"manual","language":"en","content":"Database backups run every night at 03:00 UTC. Backup copies are retained for fourteen days. Restore tests use an isolated environment.","metadata":{"tags":["operations"],"owner":"platform"}}')
printf '%s\n' "$response"
DOCUMENT_ID=$(printf '%s' "$response" | python3 -c 'import json,sys; print(json.load(sys.stdin)["document_id"])')
```

A response has this shape; IDs and chunk counts depend on the store/content:

```json
{"status":"created","document_id":123,"chunks_created":2}
```

| Field | Required | Behavior |
| --- | --- | --- |
| `document_id` | No | Omit or use `0` to create. Supply an existing positive ID to replace that document. |
| `title` | Yes | Nonempty document title. |
| `content` | Yes | Nonempty original text; normalization and chunking happen during indexing. |
| `source_uri` | No | Source identifier or URL; never fetched automatically. |
| `source_type` | No | Defaults to `manual`. |
| `language` | No | Defaults to `en` across HTTP, MCP, and the web form. |
| `metadata` | No | JSON object; defaults to `{}`. |

Replacing an existing document returns `status: "reindexed"` and retains its document ID. Chunk IDs may change. A nonexistent update ID returns an application error; it does not create a document under that ID.

## Search information

<!-- api-example:search -->
```bash
curl --fail-with-body --silent --show-error "$BASE_URL/api/search" \
  -H 'Content-Type: application/json' \
  -d '{"query":"How long are backup copies retained?","limit":5}'
```

Response shape (values are illustrative):

```json
{
  "query":"How long are backup copies retained?",
  "limit":5,
  "results":[{
    "document_id":123,
    "title":"Backup retention",
    "source_uri":"manual:backup-retention",
    "chunk_id":456,
    "chunk_no":1,
    "chunk_text":"Database backups run every night at 03:00 UTC. Backup copies are retained for fourteen days.",
    "score":0.82
  }]
}
```

`query` is required. HTTP/UI default to a limit of 10; MCP defaults to 5. The maximum is 20 in the default configuration. Results are chunks, so several may share a document ID. Scores are cosine similarities, not confidence percentages. An empty store/no matches can return `results: null`; clients should treat null or an empty array as no results.

## Reindex existing documents

Reindexing rebuilds chunks and embeddings from stored original bodies. It retains document IDs and does not transfer data to another collection/database.

<!-- api-example:reindex -->
```bash
curl --fail-with-body --silent --show-error "$BASE_URL/api/documents/reindex" \
  -H 'Content-Type: application/json' \
  -d "{\"document_ids\":[$DOCUMENT_ID]}"
```

For a batch, include multiple existing IDs. Duplicate IDs are processed once. Use `{"all":true}` to reindex every document; do not combine `all: true` with `document_ids`. Responses contain `document_ids`, `documents_reindexed`, and `chunks_created_total`.

## MCP requests

The current MCP server uses JSON-RPC requests over HTTP POST at `/mcp`. It supports initialization, tool discovery, and tool calls. The examples address the implemented HTTP endpoint directly; a client-specific MCP configuration is separate.

Initialize and list tools:

<!-- api-example:mcp-discovery -->
```bash
curl --fail-with-body --silent --show-error "$MCP_URL" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
curl --fail-with-body --silent --show-error "$MCP_URL" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

Search and retrieve the original document inserted above:

<!-- api-example:mcp-search-read -->
```bash
curl --fail-with-body --silent --show-error "$MCP_URL" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_chunks","arguments":{"query":"How long do we retain backups?","limit":5}}}'
curl --fail-with-body --silent --show-error "$MCP_URL" \
  -H 'Content-Type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"get_document\",\"arguments\":{\"document_id\":$DOCUMENT_ID}}}"
```

Add information through MCP:

<!-- api-example:mcp-insert -->
```bash
curl --fail-with-body --silent --show-error "$MCP_URL" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"insert_document","arguments":{"title":"Restore testing","source_uri":"manual:restore-testing","language":"en","content":"Test restored database backups in an isolated environment before making recovered data available to users.","metadata":{"tags":["operations"]}}}}'
```

Tool results contain both `result.structuredContent` and a JSON text representation in `result.content`. `get_document` returns original content, source fields, language, metadata, and document ID. There is no separate HTTP GET-document endpoint in the current API.

## Errors

| Interface | Condition | Response |
| --- | --- | --- |
| HTTP | Invalid JSON or request fields | HTTP 400 with a plain-text explanation. |
| HTTP | Unsupported method | HTTP 405. |
| HTTP | Embedding/storage/reindex failure | HTTP 500 with a plain-text explanation. |
| MCP | Malformed JSON | JSON-RPC error `-32700`. |
| MCP | Malformed `tools/call` params object | JSON-RPC error `-32602`. |
| MCP | Unknown method | JSON-RPC error `-32601`. |
| MCP | Tool argument validation/execution failure, including a missing document | JSON-RPC error `-32000`. |

MCP errors generally still use HTTP 200. Inspect the JSON `error` field rather than rely only on curl's HTTP exit status. Batch/full reindexing is not atomic across all documents; complete a failed rebuild before serving search after a model change.

See the [model-switch procedure](embedding-models.md#switching-the-embedding-model), [architecture](architecture.md), and [testing instructions](../README.md#testing) for operational context and checks.
