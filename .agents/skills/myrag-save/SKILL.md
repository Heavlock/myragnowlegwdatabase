---
name: myrag-save
description: Save new information, notes, or source documents in this repository's myrag knowledge database when the user asks to persist them for later retrieval.
---

# Save information in myrag

Use the [save contract](../../../docs/knowledge-contracts.md#save-information) for a new document. For an existing document, use the local `myrag-update` skill instead.

- Use the user's selected database profile/endpoint. The repository default is PostgreSQL. A connected `myrag` MCP tool is suitable only when its endpoint is known to be that store; otherwise use the repository client.
- Store the full supplied source text unless the user asks to save a summary. Use a specific title, an explicit content language, and real source information. Do not invent metadata or substitute a URL for its document text.
- Call `insert_document` without a positive `document_id`. Save is creation, not an update or an idempotent upsert by `source_uri`.
- Read the returned ID with `get_document` and verify the stored content/source fields. Report the title, document ID, selected store, and successful indexing only after verification.
- If a write times out, inspect/search for the possible stored document before resending; repeated creates can duplicate it. Do not write unrelated repository files to the knowledge base just because this skill is installed.

The [repository client](../../../scripts/myrag_client.py) implements creation and read-back without any global MCP configuration. From the repository root:

```bash
python3 scripts/myrag_client.py --profile postgres save --input /path/to/document.json
```

Use `--profile qdrant` for that store. Native MCP arguments and the JSON file have the same document fields; the contract contains an example.
