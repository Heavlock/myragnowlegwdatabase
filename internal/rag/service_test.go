package rag

import (
	"context"
	"encoding/json"
	"testing"

	"myragnowlegwdatabase/internal/chunker"
	"myragnowlegwdatabase/internal/storage"
)

type searchRepositoryStub struct {
	rows             []storage.SearchRow
	lastSearchParams storage.SearchParams
	lastUpsertParams storage.UpsertDocumentParams
	documents        []storage.DocumentRecord
}

func (s *searchRepositoryStub) UpsertDocument(_ context.Context, params storage.UpsertDocumentParams) (storage.UpsertDocumentResult, error) {
	s.lastUpsertParams = params
	return storage.UpsertDocumentResult{
		DocumentID:    params.DocumentID,
		ChunksCreated: len(params.Chunks),
	}, nil
}

func (s *searchRepositoryStub) Search(_ context.Context, params storage.SearchParams) ([]storage.SearchRow, error) {
	s.lastSearchParams = params
	return s.rows, nil
}

func (s *searchRepositoryStub) ListDocuments(context.Context) ([]storage.DocumentRecord, error) {
	return append([]storage.DocumentRecord(nil), s.documents...), nil
}

func (s *searchRepositoryStub) GetDocumentsByIDs(_ context.Context, documentIDs []int64) ([]storage.DocumentRecord, error) {
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

type searchEmbeddingClientStub struct {
	vector []float32
}

func TestServiceUpsertDocumentLanguage(t *testing.T) {
	for _, tc := range []struct {
		name, language, want string
	}{
		{"omitted", "", "en"},
		{"blank", " \t", "en"},
		{"explicit", " fr ", "fr"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			repository := &searchRepositoryStub{}
			service := NewService(repository, searchEmbeddingClientStub{vector: []float32{1, 0}}, "test-model", 2, chunker.Config{}, 10, 20)
			_, err := service.UpsertDocument(context.Background(), UpsertDocumentInput{
				Title: "Example", Content: "A short document.", Language: tc.language,
			})
			if err != nil {
				t.Fatalf("upsert: %v", err)
			}
			if got := repository.lastUpsertParams.Language; got != tc.want {
				t.Fatalf("stored language = %q, want %q", got, tc.want)
			}
		})
	}
}

func (s searchEmbeddingClientStub) Embed(_ context.Context, _ []string) ([][]float32, error) {
	return [][]float32{s.vector}, nil
}

func TestServiceSearchKeepsVectorOrder(t *testing.T) {
	repository := &searchRepositoryStub{
		rows: []storage.SearchRow{
			{
				DocumentID: 10,
				Title:      "Документ 10",
				SourceURI:  "https://example.com/10",
				ChunkID:    101,
				ChunkNo:    0,
				ChunkText:  "Первый по vector search",
				Score:      0.88,
			},
			{
				DocumentID: 20,
				Title:      "Документ 20",
				SourceURI:  "https://example.com/20",
				ChunkID:    202,
				ChunkNo:    0,
				ChunkText:  "Второй по vector search",
				Score:      0.77,
			},
		},
	}

	service := NewService(
		repository,
		searchEmbeddingClientStub{vector: []float32{1, 0}},
		"Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0",
		2,
		chunker.Config{},
		10,
		20,
	)

	result, err := service.Search(context.Background(), SearchInput{
		Query: "vector only",
		Limit: 2,
	})
	if err != nil {
		t.Fatalf("search: %v", err)
	}

	if repository.lastSearchParams.Limit != 2 {
		t.Fatalf("unexpected retrieval limit: got %d want 2", repository.lastSearchParams.Limit)
	}
	if result.Results[0].DocumentID != 10 {
		t.Fatalf("unexpected first document_id: got %d want 10", result.Results[0].DocumentID)
	}
	if result.Results[0].Score != 0.88 {
		t.Fatalf("unexpected first score: got %f want 0.88", result.Results[0].Score)
	}
}

func TestServiceGetDocument(t *testing.T) {
	metadata, err := json.Marshal(map[string]any{
		"team":   "platform",
		"active": true,
	})
	if err != nil {
		t.Fatalf("marshal metadata: %v", err)
	}

	repository := &searchRepositoryStub{
		documents: []storage.DocumentRecord{
			{
				DocumentID: 7,
				Title:      "Регламент",
				SourceURI:  "https://example.com/documents/7",
				SourceType: "manual",
				Language:   "en",
				Content:    "Полный текст документа.",
				Metadata:   metadata,
			},
		},
	}

	service := NewService(
		repository,
		searchEmbeddingClientStub{vector: []float32{1, 0}},
		"Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0",
		2,
		chunker.Config{},
		10,
		20,
	)

	result, err := service.GetDocument(context.Background(), GetDocumentInput{
		DocumentID: 7,
	})
	if err != nil {
		t.Fatalf("get document: %v", err)
	}

	if result.DocumentID != 7 {
		t.Fatalf("unexpected document_id: got %d want 7", result.DocumentID)
	}
	if result.Content != "Полный текст документа." {
		t.Fatalf("unexpected content: %q", result.Content)
	}
	if result.Metadata["team"] != "platform" {
		t.Fatalf("unexpected metadata.team: %#v", result.Metadata["team"])
	}
	if result.Metadata["active"] != true {
		t.Fatalf("unexpected metadata.active: %#v", result.Metadata["active"])
	}
}

func TestServiceGetDocumentNotFound(t *testing.T) {
	service := NewService(
		&searchRepositoryStub{},
		searchEmbeddingClientStub{vector: []float32{1, 0}},
		"Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0",
		2,
		chunker.Config{},
		10,
		20,
	)

	_, err := service.GetDocument(context.Background(), GetDocumentInput{
		DocumentID: 99,
	})
	if err == nil {
		t.Fatal("expected error")
	}
	if err.Error() != "document 99 not found" {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestServiceReindexDocumentsByIDs(t *testing.T) {
	metadata, err := json.Marshal(map[string]any{"team": "platform"})
	if err != nil {
		t.Fatalf("marshal metadata: %v", err)
	}

	repository := &searchRepositoryStub{
		documents: []storage.DocumentRecord{
			{
				DocumentID: 7,
				Title:      "Начало",
				SourceURI:  "https://example.com/start",
				SourceType: "manual",
				Language:   "en",
				Content:    "Мы создали RAG систему. Администратор управляет документами.",
				Metadata:   metadata,
			},
		},
	}

	service := NewService(
		repository,
		searchEmbeddingClientStub{vector: []float32{1, 0}},
		"Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0",
		2,
		chunker.Config{
			ChunkSizeRunes:    4096,
			ChunkOverlapRunes: 0,
		},
		10,
		20,
	)

	result, err := service.ReindexDocuments(context.Background(), ReindexDocumentsInput{
		DocumentIDs: []int64{7},
	})
	if err != nil {
		t.Fatalf("reindex documents: %v", err)
	}

	if result.DocumentsReindexed != 1 {
		t.Fatalf("unexpected documents_reindexed: got %d want 1", result.DocumentsReindexed)
	}
	if len(result.DocumentIDs) != 1 || result.DocumentIDs[0] != 7 {
		t.Fatalf("unexpected document_ids: %+v", result.DocumentIDs)
	}
	if result.ChunksCreatedTotal != 1 {
		t.Fatalf("unexpected chunks_created_total: got %d want 1", result.ChunksCreatedTotal)
	}
}

func TestServiceReindexDocumentsMissingDocument(t *testing.T) {
	repository := &searchRepositoryStub{}

	service := NewService(
		repository,
		searchEmbeddingClientStub{vector: []float32{1, 0}},
		"Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0",
		2,
		chunker.Config{},
		10,
		20,
	)

	_, err := service.ReindexDocuments(context.Background(), ReindexDocumentsInput{
		DocumentIDs: []int64{99},
	})
	if err == nil {
		t.Fatal("expected error")
	}
	if err.Error() != "documents not found: 99" {
		t.Fatalf("unexpected error: %v", err)
	}
}

type recordingQueryEmbeddings struct{ input string }

func (c *recordingQueryEmbeddings) Embed(_ context.Context, inputs []string) ([][]float32, error) {
	c.input = inputs[0]
	return [][]float32{{1, 0}}, nil
}

func TestServiceUsesDefaultQwenQueryInstruction(t *testing.T) {
	client := &recordingQueryEmbeddings{}
	service := NewService(&searchRepositoryStub{}, client, "Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0", 2, chunker.Config{}, 10, 20)
	if _, err := service.Search(context.Background(), SearchInput{Query: "  user permissions ", Limit: 1}); err != nil {
		t.Fatal(err)
	}
	const want = "Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: user permissions"
	if client.input != want {
		t.Fatalf("wrong default query input: got %q, want %q", client.input, want)
	}
}

func TestServiceUsesConfiguredQueryPrefix(t *testing.T) {
	for _, prefix := range []string{"", "Represent this sentence for searching relevant passages: "} {
		client := &recordingQueryEmbeddings{}
		service := NewService(&searchRepositoryStub{}, client, "alternate-model", 2, chunker.Config{}, 10, 20).WithQueryPrefix(prefix)
		if _, err := service.Search(context.Background(), SearchInput{Query: "  user permissions ", Limit: 1}); err != nil {
			t.Fatal(err)
		}
		if client.input != prefix+"user permissions" {
			t.Fatalf("wrong embedding input: %q", client.input)
		}
	}
}
