package mcpserver

import (
	"context"
	"encoding/json"
	"testing"

	"myragnowlegwdatabase/internal/chunker"
	"myragnowlegwdatabase/internal/rag"
	"myragnowlegwdatabase/internal/storage"
)

type repositoryStub struct {
	documents []storage.DocumentRecord
}

func (s *repositoryStub) UpsertDocument(context.Context, storage.UpsertDocumentParams) (storage.UpsertDocumentResult, error) {
	return storage.UpsertDocumentResult{}, nil
}

func (s *repositoryStub) Search(context.Context, storage.SearchParams) ([]storage.SearchRow, error) {
	return nil, nil
}

func (s *repositoryStub) ListDocuments(context.Context) ([]storage.DocumentRecord, error) {
	return append([]storage.DocumentRecord(nil), s.documents...), nil
}

func (s *repositoryStub) GetDocumentsByIDs(_ context.Context, documentIDs []int64) ([]storage.DocumentRecord, error) {
	index := make(map[int64]storage.DocumentRecord, len(s.documents))
	for _, document := range s.documents {
		index[document.DocumentID] = document
	}

	result := make([]storage.DocumentRecord, 0, len(documentIDs))
	for _, documentID := range documentIDs {
		if document, ok := index[documentID]; ok {
			result = append(result, document)
		}
	}

	return result, nil
}

type embeddingClientStub struct{}

func (embeddingClientStub) Embed(context.Context, []string) ([][]float32, error) {
	return [][]float32{{1, 0}}, nil
}

func TestToolDefinitionsIncludesGetDocument(t *testing.T) {
	tools := ToolDefinitions()
	for _, tool := range tools {
		if tool["name"] == "get_document" {
			return
		}
	}

	t.Fatal("expected get_document tool definition")
}

func TestServerCallGetDocument(t *testing.T) {
	metadata, err := json.Marshal(map[string]any{"team": "platform"})
	if err != nil {
		t.Fatalf("marshal metadata: %v", err)
	}

	service := rag.NewService(
		&repositoryStub{
			documents: []storage.DocumentRecord{
				{
					DocumentID: 15,
					Title:      "Runbook",
					SourceURI:  "https://example.com/runbook",
					SourceType: "manual",
					Language:   "en",
					Content:    "Full document body",
					Metadata:   metadata,
				},
			},
		},
		embeddingClientStub{},
		"Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0",
		2,
		chunker.Config{},
		10,
		20,
	)

	server := NewServer(service, 20)
	result, err := server.callTool(context.Background(), toolCallParams{
		Name:      "get_document",
		Arguments: json.RawMessage(`{"document_id":15}`),
	})
	if err != nil {
		t.Fatalf("call get_document: %v", err)
	}

	payload, ok := result["structuredContent"].(rag.GetDocumentResult)
	if !ok {
		t.Fatalf("unexpected payload type: %T", result["structuredContent"])
	}
	if payload.DocumentID != 15 {
		t.Fatalf("unexpected document_id: got %d want 15", payload.DocumentID)
	}
	if payload.Content != "Full document body" {
		t.Fatalf("unexpected content: %q", payload.Content)
	}
	if payload.Metadata["team"] != "platform" {
		t.Fatalf("unexpected metadata.team: %#v", payload.Metadata["team"])
	}
}
