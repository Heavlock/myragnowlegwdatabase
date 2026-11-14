// Package storage defines the backend-neutral document repository contract.
package storage

import (
	"context"
	"encoding/json"
)

// Repository stores complete documents and returns their most similar chunks.
// UpsertDocument replaces a document and its chunks together. Implementations
// return missing IDs as absent records and sort document lists by numeric ID.
type Repository interface {
	UpsertDocument(context.Context, UpsertDocumentParams) (UpsertDocumentResult, error)
	Search(context.Context, SearchParams) ([]SearchRow, error)
	ListDocuments(context.Context) ([]DocumentRecord, error)
	GetDocumentsByIDs(context.Context, []int64) ([]DocumentRecord, error)
}

type UpsertDocumentParams struct {
	DocumentID int64
	Title      string
	SourceURI  string
	SourceType string
	Language   string
	Content    string
	Metadata   []byte
	ModelName  string
	Chunks     []ChunkInsert
}

type ChunkInsert struct {
	ChunkNo       int
	Content       string
	CharStart     int
	CharEnd       int
	TokenEstimate int
	Embedding     []float32
	EmbeddingDim  int
	EmbeddingNorm float32
}

type UpsertDocumentResult struct {
	DocumentID    int64
	ChunksCreated int
	Created       bool
}

type SearchParams struct {
	Embedding []float32
	Limit     int
}

type SearchRow struct {
	DocumentID int64
	Title      string
	SourceURI  string
	ChunkID    int64
	ChunkNo    int
	ChunkText  string
	Score      float64
}

type DocumentRecord struct {
	DocumentID int64           `json:"document_id"`
	Title      string          `json:"title"`
	SourceURI  string          `json:"source_uri"`
	SourceType string          `json:"source_type"`
	Language   string          `json:"language"`
	Content    string          `json:"content"`
	Metadata   json.RawMessage `json:"metadata"`
}
