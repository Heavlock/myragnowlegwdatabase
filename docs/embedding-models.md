# Embedding models

Run commands from the repository root. Start with the [quick start](../README.md#quick-start) for the default Qwen model.

Use the [benchmark tools](../benchmarks/README.md) to compare retrieval quality and indexing speed for your dataset and hardware. Generated results are written under the ignored `reports/` directory.

### Model-specific query prefixes

Set the prefix for the selected model explicitly. The application does not infer these settings from the model ID. Keep the GGUF file, model ID, dimensions, pooling, and storage schema compatible as described in [model switching](#switching-the-embedding-model).

| Model | Dimensions | Pooling | Query prefix |
| --- | ---: | --- | --- |
| [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B#transformers-usage) | 1024 | `last` | `Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: ` |
| [BGE-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5#frequently-asked-questions) | 384 | `cls` | `Represent this sentence for searching relevant passages: ` |
| [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2#usage-sentence-transformers) | 384 | `mean` | Empty string |

Qwen uses a task instruction followed by an actual newline and `Query: `. BGE recommends its query instruction for short-query passage retrieval; v1.5 also supports queries without it. MiniLM's documented usage embeds plain text, so select an empty prefix. Apply these instructions only to queries; document payloads retain the application's `title: ... | text: ...` format.

Choose **one** of these Bash settings, preserving the final space in the Qwen/BGE values:

Qwen3:

<!-- query-prefix:qwen -->
```bash
export EMBEDDING_QUERY_PREFIX=$'Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: '
```

BGE-small:

<!-- query-prefix:bge -->
```bash
export EMBEDDING_QUERY_PREFIX='Represent this sentence for searching relevant passages: '
```

MiniLM:

<!-- query-prefix:minilm -->
```bash
export EMBEDDING_QUERY_PREFIX=''
```

For persistent Compose settings, keep the selected value alongside the model file, ID, dimensions, and pooling in the repository's ignored `.env` file. Compose supports double-quoted newline escapes, for example:

```dotenv
EMBEDDING_QUERY_PREFIX="Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: "
```

For BGE, use `EMBEDDING_QUERY_PREFIX='Represent this sentence for searching relevant passages: '`. For MiniLM, use `EMBEDDING_QUERY_PREFIX=''`; leaving it unset activates the Qwen default. Shell exports take precedence over `.env`, so clear conflicting exports when relying on the file. Check the effective selected profile with `make config PROFILE=postgres` or `PROFILE=qdrant`, then inspect its prefix with `docker compose --profile postgres config` or the corresponding Qdrant command before starting services. See [Compose environment-file syntax](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/#env-file-syntax).

## Switching the embedding model

The application supports alternative **embedding** models. Documents and queries must use the same model and vector space.

A compatible model must work with llama.cpp's `/v1/embeddings` endpoint and return one pooled vector per input. Match its GGUF file, model identity, output dimension, pooling, query instruction, and token limits. A chat-only model is not a replacement for an embedding model. `make model-download` remains specific to the default Qwen file; obtain other models separately.

The example below switches **Qwen3 (1,024 dimensions) → BGE-small-en-v1.5 Q8_0 (384 dimensions)**. Run the numbered steps in the same Bash session from the repository root. Set `PROFILE=qdrant` in step 1 for Qdrant. Use a maintenance window: the procedure stops application clients until document vectors have been rebuilt.

Both profiles share one embedding container and its model settings. The example stops clients for both profiles and restarts only the selected profile. Leave the other profile's clients stopped until its storage has also been migrated. For independent models at the same time, use separate Compose projects, model settings, and host ports. Do not mix old and new vectors, even if two models have the same dimension.

### 1. Select the existing Qwen stack and back up its documents

Start from a working stack built from this version of the project, with `EMBEDDING_MODEL_FILE` exported to your current Qwen file. The database must be running. The export/import/reindex CLI commands below use the same repository and RAG services as the application.

<!-- model-switch:backup -->
```bash
set -euo pipefail
export PROFILE="${PROFILE:-postgres}"  # Set PROFILE=qdrant before this block for Qdrant.
case "$PROFILE" in
  postgres) APP_SERVICE=app; MCP_SERVICE=mcp; BASE_URL="http://127.0.0.1:${POSTGRES_APP_PORT:-8080}" ;;
  qdrant) APP_SERVICE=app-qdrant; MCP_SERVICE=mcp-qdrant; BASE_URL="http://127.0.0.1:${QDRANT_APP_PORT:-8082}" ;;
  *) echo 'PROFILE must be postgres or qdrant' >&2; exit 2 ;;
esac
QWEN_MODEL_FILE="${EMBEDDING_MODEL_FILE:?Export the current Qwen GGUF path first}"
PREVIOUS_QDRANT_COLLECTION="${QDRANT_COLLECTION:-myrag_documents}"
mkdir -p backups
SWITCH_BACKUP_DIR=$(mktemp -d "$PWD/backups/model-switch.XXXXXX")
printf 'Keep this backup directory: %s\n' "$SWITCH_BACKUP_DIR"
docker compose --profile "$PROFILE" build "$APP_SERVICE" "$MCP_SERVICE"
docker compose --profile postgres --profile qdrant stop app mcp app-qdrant mcp-qdrant
if [ "$PROFILE" = postgres ]; then
  docker compose --profile postgres exec -T postgres pg_dump -U rag -d rag -Fc > "$SWITCH_BACKUP_DIR/postgres.dump"
else
  docker compose --profile qdrant run --rm -T --no-deps app-qdrant export > "$SWITCH_BACKUP_DIR/documents.jsonl"
fi
```

Backups contain document content and metadata; `backups/` is excluded from Git and Docker build contexts. Stop any external writers as well. PostgreSQL's dump includes its original schema/vectors. Qdrant's JSONL export contains original documents rather than vectors; the old collection remains in the Qdrant volume for rollback.

### 2. Download and verify the replacement model

This example uses a pinned [GGUF conversion](https://huggingface.co/CompendiumLabs/bge-small-en-v1.5-gguf/tree/d32f8c040ea3b516330eeb75b72bcc2d3a780ab7) of [BAAI's English BGE-small model](https://huggingface.co/BAAI/bge-small-en-v1.5). The checksum identifies the exact converted file used here.

<!-- model-switch:download -->
```bash
mkdir -p models
BGE_MODEL_FILE="$PWD/models/bge-small-en-v1.5-q8_0.gguf"
if [ ! -f "$BGE_MODEL_FILE" ]; then
  curl --fail --location --retry 3 \
    'https://huggingface.co/CompendiumLabs/bge-small-en-v1.5-gguf/resolve/d32f8c040ea3b516330eeb75b72bcc2d3a780ab7/bge-small-en-v1.5-q8_0.gguf' \
    --output "$BGE_MODEL_FILE.download"
  printf 'ec38e8da142596baa913124ae50550de284b6916bf59577ef2f0cb9660c2f514  %s\n' "$BGE_MODEL_FILE.download" | sha256sum --check
  mv "$BGE_MODEL_FILE.download" "$BGE_MODEL_FILE"
fi
printf 'ec38e8da142596baa913124ae50550de284b6916bf59577ef2f0cb9660c2f514  %s\n' "$BGE_MODEL_FILE" | sha256sum --check
```

### 3. Configure the new model and prepare storage

BGE uses CLS pooling and the query instruction below. The prefix's trailing space matters. The document format remains `title: ... | text: ...`. Smaller chunks suit BGE's 512-token input limit, but rune counts are not token counts: title and document text must still fit the model's token limit. This example is intended for English prose. See the [model instructions](https://huggingface.co/BAAI/bge-small-en-v1.5) and [llama.cpp pooling documentation](https://github.com/ggml-org/llama.cpp/tree/master/tools/server).

<!-- model-switch:configure -->
```bash
export EMBEDDING_MODEL_FILE="$BGE_MODEL_FILE"
export EMBEDDING_MODEL_ID='BAAI/bge-small-en-v1.5:Q8_0'
export EMBEDDING_DIM=384
export EMBEDDING_POOLING=cls
export EMBEDDING_QUERY_PREFIX='Represent this sentence for searching relevant passages: '
export CHUNK_SIZE_RUNES=800
export CHUNK_OVERLAP_RUNES=100
make model-check
make config PROFILE="$PROFILE"
if [ "$PROFILE" = postgres ]; then
  docker compose --profile postgres exec -T postgres psql -U rag -d rag \
    -v ON_ERROR_STOP=1 -v model_id="$EMBEDDING_MODEL_ID" -v embedding_dim="$EMBEDDING_DIM" \
    < deployments/postgres/switch_embedding_model.sql
else
  export QDRANT_COLLECTION="myrag_bge_small_$(date -u +%Y%m%d%H%M%S)_$$"
fi
```

For PostgreSQL, the explicit SQL transaction **clears derived embeddings**, changes the vector column and model/dimension constraints, and rebuilds the index. Original documents/chunks remain; the next step regenerates them. This SQL uses an HNSW `vector` index, so it accepts dimensions from 1 to 2,000. Larger embeddings need a different index/storage design. It is not a bootstrap migration and is never applied automatically.

For Qdrant, use a fresh collection. Startup rejects an existing collection with a different model identity or dimension. Reindexing an empty new collection alone would import nothing; step 4 imports the exported documents and embeds them with the new model. Imported documents receive new IDs. Import-result lines correspond to export lines in the same order. Preserve application references by recording those new IDs; the old IDs remain valid only in the old collection.

### 4. Load the model, rebuild vectors, and resume the application

<!-- model-switch:rebuild -->
```bash
docker compose --profile "$PROFILE" up -d --force-recreate --wait embeddings
if [ "$PROFILE" = postgres ]; then
  docker compose --profile postgres run --rm -T --no-deps app reindex \
    > "$SWITCH_BACKUP_DIR/reindex-result.json"
else
  docker compose --profile qdrant run --rm -T --no-deps app-qdrant import \
    < "$SWITCH_BACKUP_DIR/documents.jsonl" > "$SWITCH_BACKUP_DIR/import-results.jsonl"
fi
make up PROFILE="$PROFILE"
make status PROFILE="$PROFILE"
curl --fail-with-body --silent --show-error "$BASE_URL/api/search" \
  -H 'Content-Type: application/json' \
  -d '{"query":"How can PostgreSQL search similar vectors?","limit":10}'
```

Use a query appropriate to your documents; the example matches the vector-search document in the [README API example](../README.md#add-and-search-documents). Verify stored content, metadata, document counts, and search results before resuming other writers. Import accepts only an empty target to prevent accidental duplicates. A failed import can leave partial data; choose another fresh collection and retry the same export. Reindexing failures also require completing the rebuild before serving search. Backups and existing Qdrant collections are not deleted by this procedure.

Keep the new variables exported for future commands/new terminal sessions. `EMBEDDING_POOLING` is a Compose inference setting (default `last` for Qwen), while `EMBEDDING_QUERY_PREFIX` is an application setting. An explicitly empty prefix is supported for models that need none. Model identity is a storage compatibility label: it does not download or select weights independently of `EMBEDDING_MODEL_FILE`.

PostgreSQL schema management also needs to reflect the new column/constraints. The checked-in `sql/project` and bootstrap migrations describe default Qwen. **Do not run `make migrate` against the switched database using that old schema project.** If using pgCodeKeeper, export the new live schema with `make migration-pull` and review the changes before future migration generation/application. Bootstrap migrations still initialize new volumes for Qwen; a new BGE PostgreSQL volume must go through the explicit schema conversion before indexing documents.

### Returning to Qwen

Stop all application clients, restore Qwen settings, and rebuild the PostgreSQL vectors or select the original Qdrant collection. PostgreSQL IDs are retained; Qdrant returns to the original IDs when the original collection is selected.

<!-- model-switch:rollback -->
```bash
docker compose --profile postgres --profile qdrant stop app mcp app-qdrant mcp-qdrant
export EMBEDDING_MODEL_FILE="$QWEN_MODEL_FILE"
unset EMBEDDING_MODEL_ID EMBEDDING_DIM EMBEDDING_POOLING EMBEDDING_QUERY_PREFIX
unset CHUNK_SIZE_RUNES CHUNK_OVERLAP_RUNES
if [ "$PROFILE" = postgres ]; then
  docker compose --profile postgres exec -T postgres psql -U rag -d rag \
    -v ON_ERROR_STOP=1 -v model_id='Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0' -v embedding_dim=1024 \
    < deployments/postgres/switch_embedding_model.sql
else
  export QDRANT_COLLECTION="$PREVIOUS_QDRANT_COLLECTION"
fi
docker compose --profile "$PROFILE" up -d --force-recreate --wait embeddings
if [ "$PROFILE" = postgres ]; then
  docker compose --profile postgres run --rm -T --no-deps app reindex
fi
make up PROFILE="$PROFILE"
```

This rollback assumes the initial Qwen defaults. If you exported a BGE schema into `sql/project`, refresh that schema project again after returning to Qwen. If the model is unavailable or a rebuild cannot complete, keep clients stopped and recover PostgreSQL from the pre-switch dump rather than serving mixed/incomplete vectors. Changes to source documents made after a backup are not undone by regenerating their embeddings.
