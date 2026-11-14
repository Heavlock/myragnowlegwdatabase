package mcpserver

import (
	"context"
	"encoding/json"
	"fmt"

	"myragnowlegwdatabase/internal/rag"
)

type searchChunksArgs struct {
	Query string `json:"query"`
	Limit int    `json:"limit"`
}

type insertDocumentArgs struct {
	DocumentID int64          `json:"document_id"`
	Title      string         `json:"title"`
	SourceURI  string         `json:"source_uri"`
	SourceType string         `json:"source_type"`
	Language   string         `json:"language"`
	Content    string         `json:"content"`
	Metadata   map[string]any `json:"metadata"`
}

type getDocumentArgs struct {
	DocumentID int64 `json:"document_id"`
}

func ToolDefinitions() []map[string]any {
	return []map[string]any{
		{
			"name":        "search_chunks",
			"description": "Semantic search using local embeddings and cosine similarity.",
			"inputSchema": map[string]any{
				"type": "object",
				"properties": map[string]any{
					"query": map[string]any{
						"type": "string",
					},
					"limit": map[string]any{
						"type":    "integer",
						"default": 5,
						"maximum": 20,
					},
				},
				"required": []string{"query"},
			},
		},
		{
			"name":        "insert_document",
			"description": "Insert a new document or reindex an existing document by document_id.",
			"inputSchema": map[string]any{
				"type": "object",
				"properties": map[string]any{
					"document_id": map[string]any{"type": "integer"},
					"title":       map[string]any{"type": "string"},
					"source_uri":  map[string]any{"type": "string"},
					"source_type": map[string]any{"type": "string"},
					"language":    map[string]any{"type": "string"},
					"content":     map[string]any{"type": "string"},
					"metadata":    map[string]any{"type": "object"},
				},
				"required": []string{"title", "content"},
			},
		},
		{
			"name":        "get_document",
			"description": "Get a full document by document_id, including content and metadata.",
			"inputSchema": map[string]any{
				"type": "object",
				"properties": map[string]any{
					"document_id": map[string]any{"type": "integer"},
				},
				"required": []string{"document_id"},
			},
		},
	}
}

func (s *Server) callTool(ctx context.Context, params toolCallParams) (map[string]any, error) {
	switch params.Name {
	case "search_chunks":
		return s.callSearch(ctx, params.Arguments)
	case "insert_document":
		return s.callInsert(ctx, params.Arguments)
	case "get_document":
		return s.callGetDocument(ctx, params.Arguments)
	default:
		return nil, fmt.Errorf("tool %q not found", params.Name)
	}
}

func (s *Server) callSearch(ctx context.Context, raw json.RawMessage) (map[string]any, error) {
	var args searchChunksArgs
	if err := json.Unmarshal(raw, &args); err != nil {
		return nil, fmt.Errorf("invalid tool arguments")
	}

	if args.Limit == 0 {
		args.Limit = 5
	}
	if args.Limit > s.searchMaxLimit {
		return nil, fmt.Errorf("limit must be at most %d", s.searchMaxLimit)
	}

	result, err := s.service.Search(ctx, rag.SearchInput{
		Query: args.Query,
		Limit: args.Limit,
	})
	if err != nil {
		return nil, err
	}

	return toolResult(result), nil
}

func (s *Server) callInsert(ctx context.Context, raw json.RawMessage) (map[string]any, error) {
	var args insertDocumentArgs
	if err := json.Unmarshal(raw, &args); err != nil {
		return nil, fmt.Errorf("invalid tool arguments")
	}

	result, err := s.service.UpsertDocument(ctx, rag.UpsertDocumentInput{
		DocumentID: args.DocumentID,
		Title:      args.Title,
		SourceURI:  args.SourceURI,
		SourceType: args.SourceType,
		Language:   args.Language,
		Content:    args.Content,
		Metadata:   args.Metadata,
	})
	if err != nil {
		return nil, err
	}

	return toolResult(result), nil
}

func (s *Server) callGetDocument(ctx context.Context, raw json.RawMessage) (map[string]any, error) {
	var args getDocumentArgs
	if err := json.Unmarshal(raw, &args); err != nil {
		return nil, fmt.Errorf("invalid tool arguments")
	}

	result, err := s.service.GetDocument(ctx, rag.GetDocumentInput{
		DocumentID: args.DocumentID,
	})
	if err != nil {
		return nil, err
	}

	return toolResult(result), nil
}

func toolResult(payload any) map[string]any {
	jsonBytes, _ := json.Marshal(payload)
	return map[string]any{
		"content": []map[string]any{
			{
				"type": "text",
				"text": string(jsonBytes),
			},
		},
		"structuredContent": payload,
	}
}
