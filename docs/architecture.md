# Architecture

myrag is a local document-retrieval service written in Go. Its web UI, HTTP API, and MCP endpoint call the same RAG service. The service uses a local embedding server and one implementation of `storage.Repository`: PostgreSQL/pgvector or Qdrant.

```text
document -> normalize -> split into chunks -> embed -> normalize vectors -> repository
query    -> normalize -> add configured prefix -> embed -> cosine search -> ranked chunks
```

The service returns retrieved text and source information. It has no answer-generation stage, separate reranking model, keyword search, or hybrid retrieval.

## Components

| Component | Responsibility | Source |
| --- | --- | --- |
| Application | Load configuration, select storage, wire services, and start HTTP/MCP or a maintenance command. | [internal/app](../internal/app/app.go) |
| RAG service | Validate input, embed documents/queries, search, and reindex. | [internal/rag](../internal/rag/service.go) |
| Chunker | Normalize text and split it into overlapping rune windows. | [internal/chunker](../internal/chunker/chunker.go) |
| Embedding client | Call the inference server's `/v1/embeddings` endpoint. | [internal/embeddings](../internal/embeddings/client.go) |
| Repository contract | Store/retrieve documents and return matching chunks independently of a backend. | [storage.Repository](../internal/storage/repository.go) |
| PostgreSQL adapter | Store documents, chunks, and embeddings in relational tables. | [internal/storage](../internal/storage/postgres.go) |
| Qdrant adapter | Store a document and its chunk multivector atomically in one point. | [internal/qdrant](../internal/qdrant/client.go) |

## Indexing and replacement

The default chunk size is 1,200 runes with 200 runes of overlap. A rune is a Unicode code point, not a model token. Titles and chunk text are embedded using `title: <title> | text: <chunk>`. The service L2-normalizes vectors and checks their dimension against configuration before storage.

An upsert without an existing ID creates a document. An upsert with an existing ID replaces that document and its chunks. PostgreSQL performs the replacement in a transaction. Qdrant replaces the document, chunk descriptors, and multivector in one point operation. This prevents old chunks from remaining after a completed replacement.

Reindexing reads original document bodies and regenerates their chunks/vectors. It preserves document IDs within the same store. It does not transfer documents to another database or collection.

## Search behavior

The default Qwen query prefix is `Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: `, with an actual newline and a trailing space. It follows the model's instruction-aware query format. `EMBEDDING_QUERY_PREFIX` can override it, including an explicitly empty prefix. Model-specific instructions must match the selected embedding model. Prefix-only changes do not change document embeddings and need no reindexing.

Both backends return chunks ordered by cosine similarity. `score = 1 - cosine distance`; it is a similarity score, not an answer-correctness probability. A result limit applies to chunks, so multiple results may belong to the same document. HTTP/UI default to 10 results and MCP to 5; the default maximum is 20.

PostgreSQL orders stored vectors by pgvector cosine distance. Its initialized schema has a 1,024-dimensional vector column and Qwen model/dimension constraints. The supplied model-switch transaction changes these explicitly before reindexing. A HNSW index is available; PostgreSQL chooses the query plan.

Qdrant stores one document per point with an unnamed chunk multivector. Exact MaxSim search with a single query vector selects the top documents; the adapter computes chunk scores from those candidate vectors and merges them into the global top chunks. Selecting at least K documents is sufficient for top-K chunks because each selected document's score is its best chunk score. This storage design prioritizes consistent document replacement; large-document/corpus throughput has not been established by smoke tests.

## Database identity and persistence

PostgreSQL normally allocates sequential document IDs. Qdrant allocates positive random IDs that fit exactly in JSON/JavaScript's safe-integer range. Clients must use returned IDs rather than assume sequential values.

The profiles have separate persistent volumes. Qdrant collections record the embedding model identity, dimension, distance metric, and layout version. Startup rejects incompatible collections. PostgreSQL's schema enforces its configured storage shape through constraints; the application also checks returned vector dimensions.

Model identity is a compatibility label, not weight discovery. The inference container loads the file named by `EMBEDDING_MODEL_FILE`. Changing only the label does not select another model or rebuild old embeddings.

## Maintenance commands

The container's `myrag` executable accepts these modes:

| Mode | Behavior |
| --- | --- |
| `app` | Serve the web UI and HTTP API; default mode. |
| `mcp` | Serve the MCP endpoint. |
| `export` | Write original documents as JSONL to stdout, without model-specific vectors. |
| `import` | Read an export from stdin and embed documents into an empty target; allocate new IDs and write results to stdout. |
| `reindex` | Rebuild every document's embeddings offline and write a JSON summary to stdout. |

Operational logs go to stderr so exported JSONL can be redirected to a file. Export/import and reindex use the same repository/RAG service as HTTP and MCP. They are maintenance operations: stop writers and follow the [model-switch guide](embedding-models.md#switching-the-embedding-model). Imports and full reindexing are not one transaction for the entire corpus; failures can leave a partial rebuild. Retry an import in a fresh target.

## Deployment boundaries

Both profiles in one Compose project share one embedding container and model settings. Use separate Compose projects and ports for independent models. Published ports bind to loopback. The default PostgreSQL credentials and optional Qdrant key are intended for the documented local setup; the UI/HTTP/MCP layer has no authentication or role system.

The Dockerfile currently builds a Linux amd64 binary. Native ARM builds require a compatible build configuration. For another architecture, adapt and validate the build rather than assume native support.

See [setup and configuration](../README.md) and the [API guide](api.md) for commands and operating details.
