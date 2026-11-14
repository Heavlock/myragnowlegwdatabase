# myrag

Local semantic search for your documents, written in Go. myrag splits documents into chunks, creates embeddings with a local model, and returns matching passages through a web UI, HTTP API, or MCP server. It provides retrieval for RAG applications; it does not generate answers.

Choose PostgreSQL with pgvector (the default) or Qdrant. Both use the same application and embedding service, with separate document stores. The default model is Qwen3-Embedding-0.6B Q8_0, served by llama.cpp.

Free for personal and other permitted noncommercial use under [PolyForm Noncommercial 1.0.0](LICENSE.md). Commercial use outside those permissions requires a separate license from the author. See [licensing](#license).

## Requirements

- Docker Engine and Compose v2 with `up --wait` support; the supplied build targets Linux amd64.
- Git, GNU Make, Bash, curl, and `sha256sum`.
- Several GB of disk space for images, model weights, and data, plus RAM for inference and the database.
- Python 3 for the repository client and smoke tests; Go 1.25+ for local builds and Go tests.

A GPU is optional. Docker supplies the database, llama.cpp, and build toolchain. See [installation](docs/installation.md) for Ubuntu setup and optional CUDA support.

## Quick start

```bash
git clone https://github.com/Heavlock/myragnowlegwdatabase.git
cd myragnowlegwdatabase
export EMBEDDING_MODEL_FILE="$PWD/models/Qwen3-Embedding-0.6B-Q8_0.gguf"
make model-download
make up
```

Open **http://127.0.0.1:8080**. The database starts empty; add a document in the UI or use the [API example](#add-and-search-documents).

`make model-download` downloads the public Qwen GGUF from a pinned revision and verifies its SHA-256. It reuses a matching file and refuses to overwrite a different file. If you already have the model, set `EMBEDDING_MODEL_FILE` to its absolute path and skip the download. `make up` checks for the file but does not download it.

Keep the model path exported in later terminal sessions, or save it in the repository's ignored `.env` file. With no override, Compose uses `./models/Qwen3-Embedding-0.6B-Q8_0.gguf`.

### Database profiles

| Profile | Web UI / HTTP API | MCP endpoint |
| --- | --- | --- |
| `postgres` (default) | `http://127.0.0.1:8080` | `http://127.0.0.1:8081/mcp` |
| `qdrant` | `http://127.0.0.1:8082` | `http://127.0.0.1:8083/mcp` |

```bash
make up PROFILE=qdrant
make status PROFILE=qdrant
make logs PROFILE=qdrant
make down
```

Both profiles can run together and share the embedding service. Their documents remain separate; switching profiles does not migrate data. `make down` stops both profiles and preserves their database volumes. Plain `docker compose up` without a profile starts only the embedding service.

Published ports bind to `127.0.0.1`. The application has no authentication; keep it local unless you add an authenticated access layer.

| Port variable | Default | Service |
| --- | ---: | --- |
| `POSTGRES_PORT` | 6432 | PostgreSQL |
| `POSTGRES_APP_PORT` / `POSTGRES_MCP_PORT` | 8080 / 8081 | PostgreSQL HTTP / MCP |
| `QDRANT_PORT` | 6333 | Qdrant REST API |
| `QDRANT_APP_PORT` / `QDRANT_MCP_PORT` | 8082 / 8083 | Qdrant HTTP / MCP |

## Add and search documents

Run these examples in the same Bash session. For Qdrant, change the base URL to `http://127.0.0.1:8082`.

```bash
export BASE_URL=http://127.0.0.1:8080
curl --fail-with-body --silent --show-error "$BASE_URL/api/documents/upsert" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Vector search","source_type":"manual","language":"en","content":"pgvector adds vector storage and similarity search to PostgreSQL.","metadata":{"tags":["example"]}}'

curl --fail-with-body --silent --show-error "$BASE_URL/api/search" \
  -H 'Content-Type: application/json' \
  -d '{"query":"How can PostgreSQL search similar vectors?","limit":10}'
```

Save the returned `document_id` to retrieve or update a document. An upsert without an ID creates a document; an existing ID replaces the entire document and its embeddings. Read the complete document first and preserve fields you want to retain.

Search returns chunks ranked by cosine similarity. The default chunk size is 1,200 runes with 200 runes of overlap; HTTP search returns up to 10 results by default, with a configured maximum of 20. See the [HTTP and MCP guide](docs/api.md) for retrieval, reindexing, validation, and complete request examples.

## MCP and agent skills

Connect your MCP client to the endpoint for your selected profile. The server exposes `search_chunks`, `insert_document`, and `get_document`. See [MCP requests](docs/api.md#mcp-requests) for protocol examples.

The repository includes `myrag-save`, `myrag-update`, `myrag-search`, and `myrag-install` skills for Codex and Claude Code. Start your agent in this directory; use `$myrag-search` in Codex or `/myrag-search` in Claude Code. No global skill installation is needed.

The repository client also works directly:

```bash
python3 scripts/myrag_client.py --profile postgres search --query 'backup retention' --limit 5
```

See [knowledge contracts](docs/knowledge-contracts.md) for profile selection and save/update behavior.

## Configuration

Compose reads the model path and host-port variables above, plus `EMBEDDING_MODEL_ID`, `EMBEDDING_DIM`, `EMBEDDING_QUERY_PREFIX`, `EMBEDDING_POOLING`, `CHUNK_SIZE_RUNES`, `CHUNK_OVERLAP_RUNES`, `QDRANT_COLLECTION` (default `myrag_documents`), and optional `QDRANT_API_KEY`. In Compose, the API key is passed to both Qdrant and its application clients.

Other application settings are defined in `docker-compose.yml`. Change those values or use a Compose override file; exporting an arbitrary application variable in the host shell does not override a fixed Compose environment value.

When running the Go application outside Compose, configure reachable service addresses through environment variables:

| Variable | Application default |
| --- | --- |
| `STORAGE_BACKEND` | `postgres` (`postgres` or `qdrant`) |
| `POSTGRES_DSN` | `postgres://rag:rag@postgres:5432/rag?sslmode=disable` |
| `QDRANT_URL` | `http://qdrant:6333` |
| `QDRANT_COLLECTION` | `myrag_documents` |
| `QDRANT_API_KEY` | Empty |
| `EMBEDDINGS_BASE_URL` | `http://embeddings:8080` |
| `EMBEDDING_MODEL_ID` | `Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0` |
| `EMBEDDING_DIM` | `1024` |
| `EMBEDDING_QUERY_PREFIX` | `Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: ` (`\n` is an actual newline; trailing space included) |
| `APP_HTTP_ADDR` | `:8080` |
| `MCP_HTTP_ADDR` | `:8081` |
| `CHUNK_SIZE_RUNES` / `CHUNK_OVERLAP_RUNES` | `1200` / `200` |
| `SEARCH_DEFAULT_LIMIT` / `SEARCH_MAX_LIMIT` | `10` / `20` |

Compose service hostnames resolve inside the Compose network. Host processes need host-accessible addresses instead. The embedding service has no published host port by default. Changing the embedding model requires compatible vector storage and reindexing; switching the model name alone does not convert existing vectors.

The default query instruction follows [Qwen's documented format](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B#transformers-usage). To override it in Bash, use an actual newline, for example `export EMBEDDING_QUERY_PREFIX=$'Instruct: Retrieve passages relevant to this question\nQuery: '`. A prefix-only change affects search queries while existing document vectors remain valid. Apply it with `make up PROFILE=postgres` or `make up PROFILE=qdrant`; no reindexing is required. Set the query prefix explicitly when selecting another embedding model; changing `EMBEDDING_MODEL_ID` does not select a matching prefix automatically.

## CPU and GPU inference

CPU inference is the default. Inspect the machine and select a supplied preset:

```bash
make hardware
make compute MODE=cpu
make up PROFILE=postgres
```

For a compatible NVIDIA GPU, use `make compute MODE=gpu` after completing the [CUDA setup](docs/installation.md#cpu-or-gpu-inference). The choice persists in `.env`; `make up` applies it. Both database profiles share the selected device. Changing only the device does not require reindexing.

AMD, Intel, and Apple GPUs need a separate compatible backend; see [backend selection](docs/gpu-backends.md).

## Embedding models and database maintenance

See [embedding models](docs/embedding-models.md) for Qwen, BGE, and MiniLM query settings and a complete model migration procedure with backups and rollback. Changing the model requires compatible storage and rebuilt vectors, even when the vector dimensions match.

Fresh PostgreSQL volumes load the schema from `migrations/`. Existing volumes require an explicit schema update; see [PostgreSQL schema management](docs/installation.md#postgresql-schema-management). Review the generated diff before applying it.

## Everyday commands

| Command | Purpose |
| --- | --- |
| `make up PROFILE=postgres` | Build and start a profile, waiting for dependency health. |
| `make status PROFILE=postgres` | Show containers. |
| `make logs PROFILE=postgres` | Print recent logs. |
| `make logs PROFILE=postgres FOLLOW=true` | Follow logs until Ctrl-C. |
| `make down` | Stop both profiles and retain data. |
| `make config PROFILE=postgres` | Validate Compose configuration. |
| `make model-check` | Check that the local GGUF file exists. |
| `make help` | List all targets, including maintenance and test commands. |

## Troubleshooting

- **Model missing:** check `EMBEDDING_MODEL_FILE` and run `make model-check`. Use `make model-download` for the default Qwen model.
- **Docker permission denied:** confirm `docker info` works; see [installation](docs/installation.md#install-the-required-tools).
- **Port occupied:** change the relevant port variable above and update your HTTP/MCP client URL.
- **Embedding service unhealthy:** inspect `make logs`; check the model path and available RAM.
- **Incompatible Qdrant collection:** follow the [model migration guide](docs/embedding-models.md#switching-the-embedding-model) to create and populate a compatible collection.
- **Outdated PostgreSQL schema:** review a [schema diff](docs/installation.md#postgresql-schema-management) before applying changes to an existing database.

## Testing

```bash
make docs-check
make build
make test
make smoke-test-all
```

Go integration tests start real PostgreSQL and Qdrant containers through Testcontainers. Docker is required; check test output for skips if it is unavailable.

Compose smoke tests require the default Qwen model and run in disposable projects with separate ports and volumes. They cover HTTP, MCP, the UI, reindexing, validation, and persistence. Use `make skills-test` to check knowledge contracts or `make compute-test` to compare CPU and CUDA with compatible hardware. Tests remove their own containers and volumes; generated reports go under the ignored `reports/` directory.

To exercise the [model migration instructions](docs/embedding-models.md#switching-the-embedding-model) in disposable stacks:

```bash
EMBEDDING_MODEL_FILE=/absolute/path/to/Qwen3-Embedding-0.6B-Q8_0.gguf python3 scripts/model_switch_smoke.py
```

This test downloads/reuses the BGE model and retains exports under the ignored `backups/` directory. See [benchmarks](benchmarks/README.md) for retrieval quality evaluation.

## Documentation

- [Installation and maintenance](docs/installation.md)
- [HTTP and MCP API](docs/api.md)
- [Embedding models and migration](docs/embedding-models.md)
- [GPU backend selection](docs/gpu-backends.md)
- [Architecture](docs/architecture.md)
- [Agent skills and knowledge contracts](docs/knowledge-contracts.md)
- [Benchmarks](benchmarks/README.md)

## License

Copyright 2026 [Heavlock](https://github.com/Heavlock).

Licensed under [PolyForm Noncommercial 1.0.0](LICENSE.md) (`PolyForm-Noncommercial-1.0.0`). Personal and other permitted noncommercial uses are free. The license also expressly permits use by the organizations listed in its Noncommercial Organizations section, including educational and government institutions.

Commercial use outside the license's permitted purposes requires a separate written license from Heavlock. [Open a licensing request](https://github.com/Heavlock/myragnowlegwdatabase/issues/new?title=Commercial%20license%20request) describing the intended use; submitting a request does not grant permission.

This is source-available software. Dependencies, container images, embedding models, and third-party datasets retain their own licenses. See [licensing details and sources](docs/licensing.md).
