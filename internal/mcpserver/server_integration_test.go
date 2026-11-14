package mcpserver

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"

	"myragnowlegwdatabase/internal/chunker"
	"myragnowlegwdatabase/internal/rag"
	"myragnowlegwdatabase/internal/storage"

	"github.com/testcontainers/testcontainers-go/modules/postgres"
)

type integrationEmbeddingClient struct{}

func (integrationEmbeddingClient) Embed(_ context.Context, inputs []string) ([][]float32, error) {
	result := make([][]float32, 0, len(inputs))
	for _, input := range inputs {
		vector := make([]float32, 1024)
		for _, r := range strings.ToLower(input) {
			vector[int(r)%1024] += 1
		}
		result = append(result, vector)
	}

	return result, nil
}

func TestServerIntegrationGetDocument(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	server, service := newIntegrationServer(t, ctx)

	upsertResult, err := service.UpsertDocument(ctx, rag.UpsertDocumentInput{
		Title:      "Документ MCP",
		SourceURI:  "https://example.com/mcp-doc",
		SourceType: "manual",
		Language:   "en",
		Content:    "Полный текст документа для MCP integration test.",
		Metadata: map[string]any{
			"team": "platform",
			"kind": "runbook",
		},
	})
	if err != nil {
		t.Fatalf("upsert document: %v", err)
	}

	response := callRPC(t, server, rpcRequest{
		JSONRPC: "2.0",
		ID:      json.RawMessage(`1`),
		Method:  "tools/call",
		Params: mustJSON(t, toolCallParams{
			Name:      "get_document",
			Arguments: json.RawMessage(`{"document_id": ` + jsonNumber(t, upsertResult.DocumentID) + `}`),
		}),
	})
	if response.Error != nil {
		t.Fatalf("unexpected rpc error: %+v", response.Error)
	}

	payloadMap, ok := response.Result.(map[string]any)
	if !ok {
		t.Fatalf("unexpected result type: %T", response.Result)
	}

	structuredContent, ok := payloadMap["structuredContent"].(map[string]any)
	if !ok {
		t.Fatalf("unexpected structuredContent type: %T", payloadMap["structuredContent"])
	}

	if got := int64(structuredContent["document_id"].(float64)); got != upsertResult.DocumentID {
		t.Fatalf("unexpected document_id: got %d want %d", got, upsertResult.DocumentID)
	}
	if got := structuredContent["content"].(string); got != "Полный текст документа для MCP integration test." {
		t.Fatalf("unexpected content: %q", got)
	}

	metadata, ok := structuredContent["metadata"].(map[string]any)
	if !ok {
		t.Fatalf("unexpected metadata type: %T", structuredContent["metadata"])
	}
	if got := metadata["team"].(string); got != "platform" {
		t.Fatalf("unexpected metadata.team: %q", got)
	}
}

func TestServerIntegrationGetDocumentNotFound(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	server, _ := newIntegrationServer(t, ctx)

	response := callRPC(t, server, rpcRequest{
		JSONRPC: "2.0",
		ID:      json.RawMessage(`2`),
		Method:  "tools/call",
		Params: mustJSON(t, toolCallParams{
			Name:      "get_document",
			Arguments: json.RawMessage(`{"document_id": 999999}`),
		}),
	})
	if response.Error == nil {
		t.Fatal("expected rpc error")
	}
	if response.Error.Message != "document 999999 not found" {
		t.Fatalf("unexpected rpc error message: %q", response.Error.Message)
	}
}

func newIntegrationServer(t *testing.T, ctx context.Context) (*Server, *rag.Service) {
	t.Helper()

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
	t.Cleanup(func() {
		_ = container.Terminate(context.Background())
	})

	dsn, err := container.ConnectionString(ctx, "sslmode=disable")
	if err != nil {
		t.Fatalf("get connection string: %v", err)
	}

	store, err := newIntegrationStorage(ctx, dsn)
	if err != nil {
		t.Fatalf("create storage: %v", err)
	}
	t.Cleanup(store.Close)

	if err := storage.RunMigrations(ctx, store.Pool(), integrationMigrationsDir(t)); err != nil {
		t.Fatalf("run migrations: %v", err)
	}

	service := rag.NewService(
		store,
		integrationEmbeddingClient{},
		"Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0",
		1024,
		chunker.Config{
			ChunkSizeRunes:    1200,
			ChunkOverlapRunes: 200,
		},
		10,
		20,
	)

	return NewServer(service, 20), service
}

func integrationMigrationsDir(t *testing.T) string {
	t.Helper()

	_, filename, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot resolve caller path")
	}

	return filepath.Clean(filepath.Join(filepath.Dir(filename), "..", "..", "migrations"))
}

func newIntegrationStorage(ctx context.Context, dsn string) (*storage.Postgres, error) {
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

func callRPC(t *testing.T, server http.Handler, request rpcRequest) rpcResponse {
	t.Helper()

	body, err := json.Marshal(request)
	if err != nil {
		t.Fatalf("marshal rpc request: %v", err)
	}

	req := httptest.NewRequest(http.MethodPost, "/mcp", bytes.NewReader(body))
	recorder := httptest.NewRecorder()

	server.ServeHTTP(recorder, req)

	var response rpcResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &response); err != nil {
		t.Fatalf("decode rpc response: %v", err)
	}

	return response
}

func mustJSON(t *testing.T, value any) json.RawMessage {
	t.Helper()

	data, err := json.Marshal(value)
	if err != nil {
		t.Fatalf("marshal json: %v", err)
	}

	return data
}

func jsonNumber(t *testing.T, value int64) string {
	t.Helper()

	data, err := json.Marshal(value)
	if err != nil {
		t.Fatalf("marshal number: %v", err)
	}

	return string(data)
}
