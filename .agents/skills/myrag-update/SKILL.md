---
name: myrag-update
description: Correct or replace information in an existing myrag document while retaining its document identity and fields the user did not ask to change.
---

# Update information in myrag

Follow the [update contract](../../../docs/knowledge-contracts.md#update-information). Updating uses the existing `insert_document` tool with an explicit existing ID; the server has no PATCH operation.

- Resolve the target in the selected profile. If the user has no ID, search and read the candidate full documents. Do not choose a target from a similar title alone; ask only if the intended document remains ambiguous.
- Fetch the complete current source with `get_document`. Construct the complete revised body from that source and the requested change. A matching chunk is not the whole document.
- Preserve title, source URI/type, language, content, and metadata unless the user asks to change those fields. Send all retained fields plus the existing positive `document_id` when calling MCP directly. Omitting fields from a direct update resets/defaults them; it does not preserve them.
- Verify the returned ID is unchanged and read back the full result. A missing document is an error, never permission to create a replacement under a new ID.
- The API has no conditional version/ETag update. Fetch immediately before applying changes and coordinate with other writers when necessary; do not promise protection from concurrent overwrites.

The [repository client](../../../scripts/myrag_client.py) reads the current source and merges a JSON patch before replacement. It recursively merges metadata objects by default, replacing lists/scalars only where supplied:

```bash
python3 scripts/myrag_client.py --profile postgres update --document-id 123 --input /path/to/patch.json
```

The ID above is illustrative; use a real ID from this store. `--replace-metadata` replaces the entire metadata object when explicitly requested. Report the updated ID, fields changed, selected store, and read-back result. Do not describe reindexing alone as correcting source information.
