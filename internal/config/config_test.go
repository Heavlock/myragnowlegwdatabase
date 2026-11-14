package config

import (
	"os"
	"testing"
)

func TestStorageBackendSelection(t *testing.T) {
	t.Setenv("STORAGE_BACKEND", "")
	cfg, err := Load()
	if err != nil || cfg.StorageBackend != "postgres" {
		t.Fatalf("default backend: %+v %v", cfg, err)
	}
	t.Setenv("STORAGE_BACKEND", "qdrant")
	t.Setenv("QDRANT_COLLECTION", "alternate")
	t.Setenv("QDRANT_URL", "http://localhost:6333")
	cfg, err = Load()
	if err != nil || cfg.StorageBackend != "qdrant" || cfg.QdrantCollection != "alternate" || cfg.QdrantURL != "http://localhost:6333" {
		t.Fatalf("qdrant selection: %+v %v", cfg, err)
	}
	t.Setenv("STORAGE_BACKEND", "unknown")
	if _, err := Load(); err == nil {
		t.Fatal("accepted unsupported backend")
	}
}

func TestEmbeddingQueryPrefixAllowsEmpty(t *testing.T) {
	for _, prefix := range []string{"", "Represent this sentence for searching relevant passages: "} {
		t.Setenv("EMBEDDING_QUERY_PREFIX", prefix)
		cfg, err := Load()
		if err != nil || cfg.EmbeddingQueryPrefix != prefix {
			t.Fatalf("prefix %q: %+v %v", prefix, cfg, err)
		}
	}
	t.Setenv("EMBEDDING_DIM", "0")
	if _, err := Load(); err == nil {
		t.Fatal("accepted zero embedding dimension")
	}
}

func TestEmbeddingQueryPrefixDefault(t *testing.T) {
	// Register cleanup for any inherited value, then exercise the unset case.
	t.Setenv("EMBEDDING_QUERY_PREFIX", "")
	if err := os.Unsetenv("EMBEDDING_QUERY_PREFIX"); err != nil {
		t.Fatal(err)
	}
	cfg, err := Load()
	const want = "Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: "
	if err != nil || cfg.EmbeddingQueryPrefix != want {
		t.Fatalf("default query prefix: got %q, want %q; error: %v", cfg.EmbeddingQueryPrefix, want, err)
	}
}
