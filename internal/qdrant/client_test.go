package qdrant

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"myragnowlegwdatabase/internal/storage"
)

func TestCollectionRaceAndAPIKey(t *testing.T) {
	calls := 0
	model := "test/model:1"
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls++
		if r.Header.Get("api-key") != "test-key" {
			t.Error("API key missing")
		}
		w.Header().Set("Content-Type", "application/json")
		switch calls {
		case 1:
			http.Error(w, `{"status":{"error":"not found"}}`, 404)
		case 2:
			if r.Method != http.MethodPut {
				t.Error("expected create")
			}
			http.Error(w, `{"status":{"error":"already exists"}}`, 409)
		case 3:
			_ = json.NewEncoder(w).Encode(map[string]any{"result": map[string]any{"config": map[string]any{"metadata": map[string]any{"model_name": model, "layout_version": 1}, "params": map[string]any{"vectors": map[string]any{"size": 2, "distance": "Cosine", "multivector_config": map[string]any{"comparator": "max_sim"}}}}}})
		default:
			http.Error(w, `{"status":{"error":"backend failed"}}`, 500)
		}
	}))
	defer server.Close()
	repo, err := New(context.Background(), Config{URL: server.URL, APIKey: "test-key", Collection: "test", ModelName: model, Dimension: 2})
	if err != nil {
		t.Fatal(err)
	}
	defer repo.Close()
	_, err = repo.Search(context.Background(), storage.SearchParams{Embedding: []float32{1, 0}, Limit: 1})
	if err == nil || !strings.Contains(err.Error(), "500") {
		t.Fatalf("search hid backend failure: %v", err)
	}
}

func TestInvalidConfiguration(t *testing.T) {
	for _, cfg := range []Config{
		{URL: "file:///tmp/db", Collection: "test", ModelName: "m", Dimension: 2},
		{URL: "http://user:password@localhost:6333", Collection: "test", ModelName: "m", Dimension: 2},
		{URL: "http://localhost:6333", Collection: "../other", ModelName: "m", Dimension: 2},
		{URL: "http://localhost:6333", Collection: "test", ModelName: "m", Dimension: 0},
	} {
		if repo, err := New(context.Background(), cfg); err == nil {
			repo.Close()
			t.Fatalf("accepted invalid configuration: %+v", cfg)
		}
	}
}

func TestCollectionStartupFailureDoesNotCreate(t *testing.T) {
	calls := 0
	creates := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { calls++; http.Error(w, "unavailable", 503) }))
	defer server.Close()
	if _, err := New(context.Background(), Config{URL: server.URL, Collection: "test", ModelName: "m", Dimension: 2}); err == nil || !strings.Contains(err.Error(), "503") {
		t.Fatalf("startup failure: %v", err)
	}
	if creates != 0 || calls < 1 {
		t.Fatalf("created collection after server error: %d creates, %d requests", creates, calls)
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	_, err := New(ctx, Config{URL: server.URL, Collection: "test", ModelName: "m", Dimension: 2})
	if !errors.Is(err, context.Canceled) {
		t.Fatalf("request lost cancellation: %v", err)
	}
}
