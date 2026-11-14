package qdrant

import (
	"context"
	"fmt"
	"math"
	"net/http"
	"slices"

	"myragnowlegwdatabase/internal/storage"
)

func (r *Repository) Search(ctx context.Context, params storage.SearchParams) ([]storage.SearchRow, error) {
	if params.Limit < 1 {
		return nil, fmt.Errorf("search limit must be positive")
	}
	if len(params.Embedding) != r.dimension {
		return nil, fmt.Errorf("unexpected search embedding dimension")
	}
	var queryNorm float64
	for _, v := range params.Embedding {
		if math.IsNaN(float64(v)) || math.IsInf(float64(v), 0) {
			return nil, fmt.Errorf("search embedding must be finite")
		}
		queryNorm += float64(v) * float64(v)
	}
	if queryNorm == 0 {
		return nil, fmt.Errorf("search embedding must be nonzero")
	}
	// With a single query vector, MaxSim ranks a document by its best chunk.
	// Global top K chunks must belong to these top K documents. Exact candidate
	// search preserves that bound; score each candidate's stored chunk vectors
	// locally and merge them to keep the repository's chunk-level contract.
	body := map[string]any{"query": [][]float32{params.Embedding}, "limit": params.Limit, "with_payload": true, "with_vector": true, "params": map[string]bool{"exact": true}}
	var response struct {
		Points []point `json:"points"`
	}
	if err := r.request(ctx, http.MethodPost, r.collectionPath+"/points/query", body, &response); err != nil {
		return nil, fmt.Errorf("search qdrant documents: %w", err)
	}
	var result []storage.SearchRow
	for _, p := range response.Points {
		vectors := p.Vector
		if len(vectors) != len(p.Payload.Chunks) || p.Payload.ModelName != r.modelName {
			return nil, fmt.Errorf("qdrant document %d has inconsistent chunks or embedding model", p.ID)
		}
		for i, chunk := range p.Payload.Chunks {
			vector := vectors[i]
			if len(vector) != r.dimension {
				return nil, fmt.Errorf("qdrant document %d has invalid vector dimension", p.ID)
			}
			var dot, norm float64
			for j, v := range vector {
				dot += float64(v) * float64(params.Embedding[j])
				norm += float64(v) * float64(v)
			}
			if norm == 0 {
				return nil, fmt.Errorf("qdrant document %d has a zero vector", p.ID)
			}
			score := dot / math.Sqrt(queryNorm*norm)
			result = append(result, storage.SearchRow{DocumentID: p.ID, Title: p.Payload.Document.Title, SourceURI: p.Payload.Document.SourceURI, ChunkID: chunk.ID, ChunkNo: chunk.No, ChunkText: chunk.Content, Score: score})
		}
	}
	slices.SortFunc(result, func(a, b storage.SearchRow) int {
		if a.Score > b.Score {
			return -1
		}
		if a.Score < b.Score {
			return 1
		}
		if a.DocumentID < b.DocumentID {
			return -1
		}
		if a.DocumentID > b.DocumentID {
			return 1
		}
		if a.ChunkNo < b.ChunkNo {
			return -1
		}
		if a.ChunkNo > b.ChunkNo {
			return 1
		}
		return 0
	})
	return result[:min(len(result), params.Limit)], nil
}
