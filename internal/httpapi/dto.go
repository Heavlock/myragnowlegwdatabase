package httpapi

import (
	"fmt"
	"strings"

	"myragnowlegwdatabase/internal/rag"
)

type UpsertDocumentRequest struct {
	DocumentID int64          `json:"document_id"`
	Title      string         `json:"title"`
	SourceURI  string         `json:"source_uri"`
	SourceType string         `json:"source_type"`
	Language   string         `json:"language"`
	Content    string         `json:"content"`
	Metadata   map[string]any `json:"metadata"`
}

type SearchRequest struct {
	Query string `json:"query"`
	Limit int    `json:"limit"`
}

type ReindexDocumentsRequest struct {
	All         bool    `json:"all"`
	DocumentIDs []int64 `json:"document_ids"`
}

func (r UpsertDocumentRequest) Validate() (rag.UpsertDocumentInput, error) {
	input := rag.UpsertDocumentInput{
		DocumentID: r.DocumentID,
		Title:      strings.TrimSpace(r.Title),
		SourceURI:  strings.TrimSpace(r.SourceURI),
		SourceType: strings.TrimSpace(r.SourceType),
		Language:   strings.TrimSpace(r.Language),
		Content:    strings.TrimSpace(r.Content),
		Metadata:   r.Metadata,
	}

	if input.DocumentID < 0 {
		return rag.UpsertDocumentInput{}, fmt.Errorf("document_id must be at least 0")
	}
	if input.Title == "" {
		return rag.UpsertDocumentInput{}, fmt.Errorf("title is required")
	}
	if input.Content == "" {
		return rag.UpsertDocumentInput{}, fmt.Errorf("content is required")
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

func (r SearchRequest) Validate(defaultLimit, maxLimit int) (rag.SearchInput, error) {
	input := rag.SearchInput{
		Query: strings.TrimSpace(r.Query),
		Limit: r.Limit,
	}

	if input.Query == "" {
		return rag.SearchInput{}, fmt.Errorf("query is required")
	}
	if input.Limit == 0 {
		input.Limit = defaultLimit
	}
	if input.Limit < 1 {
		return rag.SearchInput{}, fmt.Errorf("limit must be at least 1")
	}
	if input.Limit > maxLimit {
		return rag.SearchInput{}, fmt.Errorf("limit must be at most %d", maxLimit)
	}

	return input, nil
}

func (r ReindexDocumentsRequest) Validate() (rag.ReindexDocumentsInput, error) {
	input := rag.ReindexDocumentsInput{
		All:         r.All,
		DocumentIDs: append([]int64(nil), r.DocumentIDs...),
	}

	if input.All {
		if len(input.DocumentIDs) > 0 {
			return rag.ReindexDocumentsInput{}, fmt.Errorf("document_ids must be empty when all=true")
		}

		return input, nil
	}

	if len(input.DocumentIDs) == 0 {
		return rag.ReindexDocumentsInput{}, fmt.Errorf("document_ids are required when all=false")
	}

	for _, documentID := range input.DocumentIDs {
		if documentID < 1 {
			return rag.ReindexDocumentsInput{}, fmt.Errorf("document_id must be at least 1")
		}
	}

	return input, nil
}
