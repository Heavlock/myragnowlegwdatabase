package rag

import (
	"context"
	"math"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"

	"myragnowlegwdatabase/internal/chunker"
	"myragnowlegwdatabase/internal/embeddings"
	"myragnowlegwdatabase/internal/storage"

	"github.com/testcontainers/testcontainers-go/modules/postgres"
)

type stubEmbeddingClient struct{}

func (stubEmbeddingClient) Embed(_ context.Context, inputs []string) ([][]float32, error) {
	result := make([][]float32, 0, len(inputs))
	for _, input := range inputs {
		vector := make([]float32, 1024)
		lower := strings.ToLower(input)
		for _, r := range lower {
			vector[int(r)%1024] += 1
		}
		result = append(result, vector)
	}

	return result, nil
}

type deterministicEmbeddingClient struct{}

func (deterministicEmbeddingClient) Embed(_ context.Context, inputs []string) ([][]float32, error) {
	result := make([][]float32, 0, len(inputs))
	for _, input := range inputs {
		switch {
		case input == embeddings.DefaultQueryPrefix+"кто администратор":
			result = append(result, sparseVector(1, 0))
		case strings.Contains(input, "vector-first candidate"):
			result = append(result, sparseVector(1, 0))
		case strings.Contains(input, "vector-second candidate"):
			result = append(result, sparseVector(0.8, 0.2))
		default:
			result = append(result, sparseVector(0.1, 0.9))
		}
	}

	return result, nil
}

func sparseVector(first, second float32) []float32 {
	vector := make([]float32, 1024)
	vector[0] = first
	vector[1] = second
	return vector
}

func TestServiceIntegration(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	container, err := postgres.Run(
		ctx,
		"pgvector/pgvector:pg16",
		postgres.BasicWaitStrategies(),
		postgres.WithDatabase("rag"),
		postgres.WithUsername("rag"),
		postgres.WithPassword("rag"),
	)
	if err != nil {
		t.Fatalf("start postgres container: %v", err)
	}
	defer func() {
		_ = container.Terminate(context.Background())
	}()

	dsn, err := container.ConnectionString(ctx, "sslmode=disable")
	if err != nil {
		t.Fatalf("get connection string: %v", err)
	}

	store, err := newTestStorage(ctx, dsn)
	if err != nil {
		t.Fatalf("create storage: %v", err)
	}
	defer store.Close()

	if err := storage.RunMigrations(ctx, store.Pool(), migrationsDir(t)); err != nil {
		t.Fatalf("run migrations: %v", err)
	}

	service := NewService(
		store,
		stubEmbeddingClient{},
		"Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0",
		1024,
		chunker.Config{
			ChunkSizeRunes:    1200,
			ChunkOverlapRunes: 200,
		},
		10,
		20,
	)

	first, err := service.UpsertDocument(ctx, UpsertDocumentInput{
		Title:      "Документ про pgvector",
		SourceURI:  "https://example.com/doc-001",
		SourceType: "manual",
		Language:   "en",
		Content:    strings.Repeat("pgvector помогает строить семантический поиск. ", 80),
		Metadata: map[string]any{
			"tags": []string{"rag"},
		},
	})
	if err != nil {
		t.Fatalf("upsert first document: %v", err)
	}

	if first.Status != "created" {
		t.Fatalf("unexpected status: %q", first.Status)
	}
	if first.ChunksCreated == 0 {
		t.Fatal("expected chunks to be created")
	}

	searchResult, err := service.Search(ctx, SearchInput{
		Query: "pgvector поиск",
		Limit: 5,
	})
	if err != nil {
		t.Fatalf("search: %v", err)
	}

	if len(searchResult.Results) == 0 {
		t.Fatal("expected search results")
	}
	if searchResult.Results[0].DocumentID != first.DocumentID {
		t.Fatalf("unexpected top result document_id: got %d want %d", searchResult.Results[0].DocumentID, first.DocumentID)
	}

	second, err := service.UpsertDocument(ctx, UpsertDocumentInput{
		DocumentID: first.DocumentID,
		Title:      "Обновленный документ про pgvector",
		SourceURI:  "https://example.com/doc-001",
		SourceType: "manual",
		Language:   "en",
		Content:    strings.Repeat("Новая версия документа с измененным содержанием. ", 20),
		Metadata: map[string]any{
			"tags": []string{"rag", "updated"},
		},
	})
	if err != nil {
		t.Fatalf("reindex document: %v", err)
	}

	if second.Status != "reindexed" {
		t.Fatalf("unexpected status after reindex: %q", second.Status)
	}

	var chunksCount int
	if err := store.Pool().QueryRow(ctx, `select count(*) from chunks where document_id = $1`, second.DocumentID).Scan(&chunksCount); err != nil {
		t.Fatalf("count chunks: %v", err)
	}
	if chunksCount != second.ChunksCreated {
		t.Fatalf("unexpected chunks count: got %d want %d", chunksCount, second.ChunksCreated)
	}

	var embeddingsCount int
	if err := store.Pool().QueryRow(ctx, `
		select count(*)
		from chunk_embeddings_v1 ce
		join chunks c on c.id = ce.chunk_id
		where c.document_id = $1
	`, second.DocumentID).Scan(&embeddingsCount); err != nil {
		t.Fatalf("count embeddings: %v", err)
	}
	if embeddingsCount != second.ChunksCreated {
		t.Fatalf("unexpected embeddings count: got %d want %d", embeddingsCount, second.ChunksCreated)
	}

	var oldChunkExists bool
	if err := store.Pool().QueryRow(ctx, `
		select exists (
			select 1
			from chunks
			where document_id = $1
			  and content like '%семантический поиск%'
		)
	`, second.DocumentID).Scan(&oldChunkExists); err != nil {
		t.Fatalf("check old chunks: %v", err)
	}
	if oldChunkExists {
		t.Fatal("expected old chunks to be replaced")
	}

	var avgNorm float64
	if err := store.Pool().QueryRow(ctx, `
		select coalesce(avg(embedding_norm), 0)
		from chunk_embeddings_v1 ce
		join chunks c on c.id = ce.chunk_id
		where c.document_id = $1
	`, second.DocumentID).Scan(&avgNorm); err != nil {
		t.Fatalf("avg norm: %v", err)
	}
	if math.Abs(avgNorm-1) > 0.0001 {
		t.Fatalf("expected embedding_norm close to 1, got %f", avgNorm)
	}
}

func TestServiceIntegrationVectorRanking(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	container, err := postgres.Run(
		ctx,
		"pgvector/pgvector:pg16",
		postgres.BasicWaitStrategies(),
		postgres.WithDatabase("rag"),
		postgres.WithUsername("rag"),
		postgres.WithPassword("rag"),
	)
	if err != nil {
		t.Fatalf("start postgres container: %v", err)
	}
	defer func() {
		_ = container.Terminate(context.Background())
	}()

	dsn, err := container.ConnectionString(ctx, "sslmode=disable")
	if err != nil {
		t.Fatalf("get connection string: %v", err)
	}

	store, err := newTestStorage(ctx, dsn)
	if err != nil {
		t.Fatalf("create storage: %v", err)
	}
	defer store.Close()

	if err := storage.RunMigrations(ctx, store.Pool(), migrationsDir(t)); err != nil {
		t.Fatalf("run migrations: %v", err)
	}

	service := NewService(
		store,
		deterministicEmbeddingClient{},
		"Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0",
		1024,
		chunker.Config{
			ChunkSizeRunes:    4096,
			ChunkOverlapRunes: 0,
		},
		10,
		20,
	)

	first, err := service.UpsertDocument(ctx, UpsertDocumentInput{
		Title:      "Первый кандидат",
		SourceURI:  "https://example.com/doc-1",
		SourceType: "manual",
		Language:   "en",
		Content:    "vector-first candidate",
		Metadata:   map[string]any{},
	})
	if err != nil {
		t.Fatalf("upsert first candidate: %v", err)
	}

	second, err := service.UpsertDocument(ctx, UpsertDocumentInput{
		Title:      "Второй кандидат",
		SourceURI:  "https://example.com/doc-2",
		SourceType: "manual",
		Language:   "en",
		Content:    "vector-second candidate",
		Metadata:   map[string]any{},
	})
	if err != nil {
		t.Fatalf("upsert second candidate: %v", err)
	}

	searchResult, err := service.Search(ctx, SearchInput{
		Query: "кто администратор",
		Limit: 2,
	})
	if err != nil {
		t.Fatalf("vector search: %v", err)
	}

	if len(searchResult.Results) != 2 {
		t.Fatalf("unexpected results count: got %d want 2", len(searchResult.Results))
	}
	if searchResult.Results[0].DocumentID != first.DocumentID {
		t.Fatalf("unexpected top result document_id: got %d want %d", searchResult.Results[0].DocumentID, first.DocumentID)
	}
	if math.Abs(searchResult.Results[0].Score-1) > 0.0001 {
		t.Fatalf("unexpected cosine score: got %f want 1", searchResult.Results[0].Score)
	}
	if searchResult.Results[1].DocumentID != second.DocumentID || searchResult.Results[1].Score >= searchResult.Results[0].Score {
		t.Fatalf("expected second candidate after first by cosine similarity: %+v", searchResult.Results)
	}

	limited, err := service.Search(ctx, SearchInput{Query: "кто администратор", Limit: 1})
	if err != nil {
		t.Fatalf("limited vector search: %v", err)
	}
	if len(limited.Results) != 1 || limited.Results[0].DocumentID != first.DocumentID {
		t.Fatalf("expected only the nearest candidate: %+v", limited.Results)
	}
}

func migrationsDir(t *testing.T) string {
	t.Helper()

	_, filename, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot resolve caller path")
	}

	return filepath.Clean(filepath.Join(filepath.Dir(filename), "..", "..", "migrations"))
}

func newTestStorage(ctx context.Context, dsn string) (*storage.Postgres, error) {
	var lastErr error
	for range 20 {
		store, err := storage.NewPostgres(ctx, dsn)
		if err == nil {
			return store, nil
		}

		lastErr = err
		time.Sleep(500 * time.Millisecond)
	}

	return nil, lastErr
}
