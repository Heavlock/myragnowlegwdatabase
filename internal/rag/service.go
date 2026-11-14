package rag

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"myragnowlegwdatabase/internal/chunker"
	"myragnowlegwdatabase/internal/embeddings"
	"myragnowlegwdatabase/internal/storage"
)

type EmbeddingClient interface {
	Embed(ctx context.Context, inputs []string) ([][]float32, error)
}

type Service struct {
	repository         storage.Repository
	embeddingClient    EmbeddingClient
	embeddingModelID   string
	embeddingDim       int
	queryPrefix        string
	chunkerConfig      chunker.Config
	searchDefaultLimit int
	searchMaxLimit     int
}

func NewService(
	repository storage.Repository,
	embeddingClient EmbeddingClient,
	embeddingModelID string,
	embeddingDim int,
	chunkerConfig chunker.Config,
	searchDefaultLimit int,
	searchMaxLimit int,
) *Service {
	return &Service{
		repository:         repository,
		embeddingClient:    embeddingClient,
		embeddingModelID:   embeddingModelID,
		embeddingDim:       embeddingDim,
		queryPrefix:        embeddings.DefaultQueryPrefix,
		chunkerConfig:      chunkerConfig,
		searchDefaultLimit: searchDefaultLimit,
		searchMaxLimit:     searchMaxLimit,
	}
}

// WithQueryPrefix configures query formatting before the service is used.
func (s *Service) WithQueryPrefix(prefix string) *Service {
	s.queryPrefix = prefix
	return s
}

func (s *Service) UpsertDocument(ctx context.Context, input UpsertDocumentInput) (UpsertDocumentResult, error) {
	input, err := s.normalizeUpsertInput(input)
	if err != nil {
		return UpsertDocumentResult{}, err
	}

	chunks := chunker.Split(input.Content, s.chunkerConfig)
	chunkPayloads := make([]string, 0, len(chunks))
	for _, chunk := range chunks {
		payload, err := embeddings.FormatChunk(input.Title, chunk.Content)
		if err != nil {
			return UpsertDocumentResult{}, fmt.Errorf("format chunk embedding input: %w", err)
		}
		chunkPayloads = append(chunkPayloads, payload)
	}

	vectors, err := s.embeddingClient.Embed(ctx, chunkPayloads)
	if err != nil {
		return UpsertDocumentResult{}, fmt.Errorf("embed document chunks: %w", err)
	}

	metadataJSON, err := json.Marshal(input.Metadata)
	if err != nil {
		return UpsertDocumentResult{}, fmt.Errorf("marshal metadata: %w", err)
	}

	chunkParams := make([]storage.ChunkInsert, 0, len(chunks))
	for i, chunk := range chunks {
		normalizedVector, _, err := embeddings.NormalizeVector(vectors[i])
		if err != nil {
			return UpsertDocumentResult{}, fmt.Errorf("normalize chunk embedding: %w", err)
		}
		if len(normalizedVector) != s.embeddingDim {
			return UpsertDocumentResult{}, fmt.Errorf("unexpected embedding dim %d", len(normalizedVector))
		}

		chunkParams = append(chunkParams, storage.ChunkInsert{
			ChunkNo:       chunk.ChunkNo,
			Content:       chunk.Content,
			CharStart:     chunk.CharStart,
			CharEnd:       chunk.CharEnd,
			TokenEstimate: chunk.TokenEstimate,
			Embedding:     normalizedVector,
			EmbeddingDim:  s.embeddingDim,
			EmbeddingNorm: 1,
		})
	}

	result, err := s.repository.UpsertDocument(ctx, storage.UpsertDocumentParams{
		DocumentID: input.DocumentID,
		Title:      input.Title,
		SourceURI:  input.SourceURI,
		SourceType: input.SourceType,
		Language:   input.Language,
		Content:    input.Content,
		Metadata:   metadataJSON,
		ModelName:  s.embeddingModelID,
		Chunks:     chunkParams,
	})
	if err != nil {
		return UpsertDocumentResult{}, fmt.Errorf("store document: %w", err)
	}

	status := "reindexed"
	if result.Created {
		status = "created"
	}

	return UpsertDocumentResult{
		Status:        status,
		DocumentID:    result.DocumentID,
		ChunksCreated: result.ChunksCreated,
	}, nil
}

func (s *Service) GetDocument(ctx context.Context, input GetDocumentInput) (GetDocumentResult, error) {
	input, err := s.normalizeGetDocumentInput(input)
	if err != nil {
		return GetDocumentResult{}, err
	}

	documents, err := s.repository.GetDocumentsByIDs(ctx, []int64{input.DocumentID})
	if err != nil {
		return GetDocumentResult{}, fmt.Errorf("get documents by ids: %w", err)
	}
	if len(documents) == 0 {
		return GetDocumentResult{}, fmt.Errorf("document %d not found", input.DocumentID)
	}

	document := documents[0]
	metadata := map[string]any{}
	if len(document.Metadata) > 0 {
		if err := json.Unmarshal(document.Metadata, &metadata); err != nil {
			return GetDocumentResult{}, fmt.Errorf("unmarshal metadata for document %d: %w", document.DocumentID, err)
		}
	}

	return GetDocumentResult{
		DocumentID: document.DocumentID,
		Title:      document.Title,
		SourceURI:  document.SourceURI,
		SourceType: document.SourceType,
		Language:   document.Language,
		Content:    document.Content,
		Metadata:   metadata,
	}, nil
}

func (s *Service) Search(ctx context.Context, input SearchInput) (SearchResult, error) {
	input, err := s.normalizeSearchInput(input)
	if err != nil {
		return SearchResult{}, err
	}

	payload, err := embeddings.FormatSearchQuery(input.Query, s.queryPrefix)
	if err != nil {
		return SearchResult{}, fmt.Errorf("format search query: %w", err)
	}

	vectors, err := s.embeddingClient.Embed(ctx, []string{payload})
	if err != nil {
		return SearchResult{}, fmt.Errorf("embed search query: %w", err)
	}

	normalizedVector, _, err := embeddings.NormalizeVector(vectors[0])
	if err != nil {
		return SearchResult{}, fmt.Errorf("normalize search embedding: %w", err)
	}
	if len(normalizedVector) != s.embeddingDim {
		return SearchResult{}, fmt.Errorf("unexpected embedding dim %d", len(normalizedVector))
	}

	rows, err := s.repository.Search(ctx, storage.SearchParams{
		Embedding: normalizedVector,
		Limit:     input.Limit,
	})
	if err != nil {
		return SearchResult{}, fmt.Errorf("search chunks: %w", err)
	}

	result := SearchResult{
		Query: input.Query,
		Limit: input.Limit,
	}

	if len(rows) == 0 {
		return result, nil
	}

	for _, row := range rows[:min(len(rows), input.Limit)] {
		result.Results = append(result.Results, SearchResultItem{
			DocumentID: row.DocumentID,
			Title:      row.Title,
			SourceURI:  row.SourceURI,
			ChunkID:    row.ChunkID,
			ChunkNo:    row.ChunkNo,
			ChunkText:  row.ChunkText,
			Score:      row.Score,
		})
	}

	return result, nil
}

func (s *Service) ReindexDocuments(ctx context.Context, input ReindexDocumentsInput) (ReindexDocumentsResult, error) {
	input, err := s.normalizeReindexInput(input)
	if err != nil {
		return ReindexDocumentsResult{}, err
	}

	var documents []storage.DocumentRecord
	if input.All {
		documents, err = s.repository.ListDocuments(ctx)
		if err != nil {
			return ReindexDocumentsResult{}, fmt.Errorf("list documents: %w", err)
		}
	} else {
		documents, err = s.repository.GetDocumentsByIDs(ctx, input.DocumentIDs)
		if err != nil {
			return ReindexDocumentsResult{}, fmt.Errorf("get documents by ids: %w", err)
		}

		if len(documents) != len(input.DocumentIDs) {
			found := make(map[int64]struct{}, len(documents))
			for _, document := range documents {
				found[document.DocumentID] = struct{}{}
			}

			var missing []string
			for _, documentID := range input.DocumentIDs {
				if _, ok := found[documentID]; !ok {
					missing = append(missing, fmt.Sprintf("%d", documentID))
				}
			}

			return ReindexDocumentsResult{}, fmt.Errorf("documents not found: %s", strings.Join(missing, ", "))
		}
	}

	result := ReindexDocumentsResult{
		DocumentIDs: make([]int64, 0, len(documents)),
	}

	for _, document := range documents {
		metadata := map[string]any{}
		if len(document.Metadata) > 0 {
			if err := json.Unmarshal(document.Metadata, &metadata); err != nil {
				return ReindexDocumentsResult{}, fmt.Errorf("unmarshal metadata for document %d: %w", document.DocumentID, err)
			}
		}

		upsertResult, err := s.UpsertDocument(ctx, UpsertDocumentInput{
			DocumentID: document.DocumentID,
			Title:      document.Title,
			SourceURI:  document.SourceURI,
			SourceType: document.SourceType,
			Language:   document.Language,
			Content:    document.Content,
			Metadata:   metadata,
		})
		if err != nil {
			return ReindexDocumentsResult{}, fmt.Errorf("reindex document %d: %w", document.DocumentID, err)
		}

		result.DocumentIDs = append(result.DocumentIDs, upsertResult.DocumentID)
		result.DocumentsReindexed++
		result.ChunksCreatedTotal += upsertResult.ChunksCreated
	}

	return result, nil
}

func (s *Service) normalizeUpsertInput(input UpsertDocumentInput) (UpsertDocumentInput, error) {
	input.Title = strings.TrimSpace(input.Title)
	input.SourceURI = strings.TrimSpace(input.SourceURI)
	input.SourceType = strings.TrimSpace(input.SourceType)
	input.Language = strings.TrimSpace(input.Language)
	input.Content = strings.TrimSpace(input.Content)

	if input.DocumentID < 0 {
		return UpsertDocumentInput{}, fmt.Errorf("document_id must be at least 0")
	}
	if input.Title == "" {
		return UpsertDocumentInput{}, fmt.Errorf("title is required")
	}
	if input.Content == "" {
		return UpsertDocumentInput{}, fmt.Errorf("content is required")
	}
	if input.SourceType == "" {
		input.SourceType = "manual"
	}
	if input.Language == "" {
		input.Language = "en"
	}
	if input.Metadata == nil {
		input.Metadata = map[string]any{}
	}

	return input, nil
}

func (s *Service) normalizeGetDocumentInput(input GetDocumentInput) (GetDocumentInput, error) {
	if input.DocumentID < 1 {
		return GetDocumentInput{}, fmt.Errorf("document_id must be at least 1")
	}

	return input, nil
}

func (s *Service) normalizeSearchInput(input SearchInput) (SearchInput, error) {
	input.Query = strings.TrimSpace(input.Query)
	if input.Query == "" {
		return SearchInput{}, fmt.Errorf("query is required")
	}

	if input.Limit == 0 {
		input.Limit = s.searchDefaultLimit
	}
	if input.Limit < 1 {
		return SearchInput{}, fmt.Errorf("limit must be at least 1")
	}
	if input.Limit > s.searchMaxLimit {
		return SearchInput{}, fmt.Errorf("limit must be at most %d", s.searchMaxLimit)
	}

	return input, nil
}

func (s *Service) normalizeReindexInput(input ReindexDocumentsInput) (ReindexDocumentsInput, error) {
	if input.All {
		if len(input.DocumentIDs) > 0 {
			return ReindexDocumentsInput{}, fmt.Errorf("document_ids must be empty when all=true")
		}
		return input, nil
	}

	if len(input.DocumentIDs) == 0 {
		return ReindexDocumentsInput{}, fmt.Errorf("document_ids are required when all=false")
	}

	seen := make(map[int64]struct{}, len(input.DocumentIDs))
	normalizedIDs := make([]int64, 0, len(input.DocumentIDs))
	for _, documentID := range input.DocumentIDs {
		if documentID < 1 {
			return ReindexDocumentsInput{}, fmt.Errorf("document_id must be at least 1")
		}
		if _, exists := seen[documentID]; exists {
			continue
		}
		seen[documentID] = struct{}{}
		normalizedIDs = append(normalizedIDs, documentID)
	}

	input.DocumentIDs = normalizedIDs

	return input, nil
}
