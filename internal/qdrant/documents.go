package qdrant

import (
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"math"
	"math/big"
	"net/http"
	"slices"

	"myragnowlegwdatabase/internal/storage"
)

// One Qdrant point holds the document, chunk descriptors and a multivector of
// chunk embeddings. A single upsert replaces all three together: no delete-then-
// insert gap and no stale chunk cleanup, including concurrent app/MCP writes.
type payload struct {
	Document      storage.DocumentRecord `json:"document"`
	ModelName     string                 `json:"model_name"`
	Chunks        []storedChunk          `json:"chunks"`
	CreationToken string                 `json:"creation_token"`
}
type storedChunk struct {
	ID      int64  `json:"id"`
	No      int    `json:"no"`
	Content string `json:"content"`
}
type point struct {
	ID      int64       `json:"id"`
	Payload payload     `json:"payload"`
	Vector  [][]float32 `json:"vector,omitempty"`
}

func randomID() (int64, error) {
	// Safe integer IDs survive JSON/JavaScript/MCP round trips exactly.
	n, err := rand.Int(rand.Reader, big.NewInt(1<<53-1))
	if err != nil {
		return 0, fmt.Errorf("generate storage identifier: %w", err)
	}
	return n.Int64() + 1, nil
}

func (r *Repository) UpsertDocument(ctx context.Context, params storage.UpsertDocumentParams) (storage.UpsertDocumentResult, error) {
	if params.DocumentID < 0 {
		return storage.UpsertDocumentResult{}, fmt.Errorf("document_id must be at least 0")
	}
	if params.ModelName != r.modelName {
		return storage.UpsertDocumentResult{}, fmt.Errorf("embedding model does not match qdrant collection")
	}
	if len(params.Chunks) == 0 {
		return storage.UpsertDocumentResult{}, fmt.Errorf("document must have chunks")
	}
	if !json.Valid(params.Metadata) {
		return storage.UpsertDocumentResult{}, fmt.Errorf("invalid document metadata")
	}
	vectors := make([][]float32, 0, len(params.Chunks))
	chunks := make([]storedChunk, 0, len(params.Chunks))
	ids := map[int64]bool{}
	for _, chunk := range params.Chunks {
		if len(chunk.Embedding) != r.dimension || chunk.EmbeddingDim != r.dimension {
			return storage.UpsertDocumentResult{}, fmt.Errorf("unexpected embedding dimension")
		}
		var norm float64
		for _, v := range chunk.Embedding {
			if math.IsNaN(float64(v)) || math.IsInf(float64(v), 0) {
				return storage.UpsertDocumentResult{}, fmt.Errorf("embedding must be finite")
			}
			norm += float64(v) * float64(v)
		}
		if norm == 0 {
			return storage.UpsertDocumentResult{}, fmt.Errorf("embedding must be nonzero")
		}
		id, err := randomID()
		if err != nil {
			return storage.UpsertDocumentResult{}, err
		}
		for ids[id] {
			id, err = randomID()
			if err != nil {
				return storage.UpsertDocumentResult{}, err
			}
		}
		ids[id] = true
		chunks = append(chunks, storedChunk{ID: id, No: chunk.ChunkNo, Content: chunk.Content})
		vectors = append(vectors, chunk.Embedding)
	}
	p := point{ID: params.DocumentID, Payload: payload{Document: storage.DocumentRecord{DocumentID: params.DocumentID, Title: params.Title, SourceURI: params.SourceURI, SourceType: params.SourceType, Language: params.Language, Content: params.Content, Metadata: params.Metadata}, ModelName: params.ModelName, Chunks: chunks}, Vector: vectors}
	created := params.DocumentID == 0
	if !created {
		existing, err := r.retrieve(ctx, []int64{params.DocumentID})
		if err != nil {
			return storage.UpsertDocumentResult{}, err
		}
		if len(existing) == 0 {
			return storage.UpsertDocumentResult{}, fmt.Errorf("document %d not found", params.DocumentID)
		}
		p.Payload.CreationToken = existing[0].Payload.CreationToken
	}
	for attempt := 0; attempt < 5; attempt++ {
		mode := "update_only"
		if created {
			id, err := randomID()
			if err != nil {
				return storage.UpsertDocumentResult{}, err
			}
			p.ID = id
			p.Payload.Document.DocumentID = id
			token := make([]byte, 16)
			if _, err := rand.Read(token); err != nil {
				return storage.UpsertDocumentResult{}, err
			}
			p.Payload.CreationToken = fmt.Sprintf("%x", token)
			mode = "insert_only"
		}
		body := map[string]any{"points": []point{p}, "update_mode": mode}
		if err := r.request(ctx, http.MethodPut, r.collectionPath+"/points?wait=true&ordering=strong", body, nil); err != nil {
			return storage.UpsertDocumentResult{}, fmt.Errorf("store qdrant document: %w", err)
		}
		if created {
			stored, err := r.retrieve(ctx, []int64{p.ID})
			if err != nil {
				return storage.UpsertDocumentResult{}, err
			}
			if len(stored) != 1 || stored[0].Payload.CreationToken != p.Payload.CreationToken {
				continue
			}
		}
		return storage.UpsertDocumentResult{DocumentID: p.ID, Created: created, ChunksCreated: len(chunks)}, nil
	}
	return storage.UpsertDocumentResult{}, fmt.Errorf("could not allocate a unique document ID")
}

func (r *Repository) retrieve(ctx context.Context, ids []int64) ([]point, error) {
	if len(ids) == 0 {
		return nil, nil
	}
	var result []point
	body := map[string]any{"ids": ids, "with_payload": true, "with_vector": false}
	if err := r.request(ctx, http.MethodPost, r.collectionPath+"/points", body, &result); err != nil {
		return nil, fmt.Errorf("retrieve qdrant documents: %w", err)
	}
	return result, nil
}

func (r *Repository) GetDocumentsByIDs(ctx context.Context, ids []int64) ([]storage.DocumentRecord, error) {
	for _, id := range ids {
		if id <= 0 {
			return nil, fmt.Errorf("document IDs must be positive")
		}
	}
	unique := make([]int64, 0, len(ids))
	seen := make(map[int64]bool, len(ids))
	for _, id := range ids {
		if !seen[id] {
			unique = append(unique, id)
			seen[id] = true
		}
	}
	points, err := r.retrieve(ctx, unique)
	if err != nil {
		return nil, err
	}
	return records(points), nil
}

func records(points []point) []storage.DocumentRecord {
	result := make([]storage.DocumentRecord, 0, len(points))
	for _, p := range points {
		result = append(result, p.Payload.Document)
	}
	slices.SortFunc(result, func(a, b storage.DocumentRecord) int {
		if a.DocumentID < b.DocumentID {
			return -1
		}
		if a.DocumentID > b.DocumentID {
			return 1
		}
		return 0
	})
	return result
}

func (r *Repository) ListDocuments(ctx context.Context) ([]storage.DocumentRecord, error) {
	var result []storage.DocumentRecord
	var offset *int64
	for {
		body := map[string]any{"limit": 64, "with_payload": true, "with_vector": false}
		if offset != nil {
			body["offset"] = *offset
		}
		var page struct {
			Points []point `json:"points"`
			Next   *int64  `json:"next_page_offset"`
		}
		if err := r.request(ctx, http.MethodPost, r.collectionPath+"/points/scroll", body, &page); err != nil {
			return nil, fmt.Errorf("list qdrant documents: %w", err)
		}
		result = append(result, records(page.Points)...)
		if page.Next == nil {
			return result, nil
		}
		if offset != nil && *page.Next <= *offset {
			return nil, fmt.Errorf("qdrant scroll did not advance")
		}
		offset = page.Next
	}
}
