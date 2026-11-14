package config

import (
	"fmt"
	"os"
	"strconv"

	"myragnowlegwdatabase/internal/embeddings"
)

type Config struct {
	AppHTTPAddr          string
	MCPHTTPAddr          string
	PostgresDSN          string
	StorageBackend       string
	QdrantURL            string
	QdrantAPIKey         string
	QdrantCollection     string
	EmbeddingsBaseURL    string
	EmbeddingModelID     string
	EmbeddingDim         int
	EmbeddingQueryPrefix string
	ChunkSizeRunes       int
	ChunkOverlapRunes    int
	SearchDefaultLimit   int
	SearchMaxLimit       int
}

func Load() (Config, error) {
	cfg := Config{
		StorageBackend:     getEnv("STORAGE_BACKEND", "postgres"),
		QdrantURL:          getEnv("QDRANT_URL", "http://qdrant:6333"),
		QdrantAPIKey:       os.Getenv("QDRANT_API_KEY"),
		QdrantCollection:   getEnv("QDRANT_COLLECTION", "myrag_documents"),
		AppHTTPAddr:        getEnv("APP_HTTP_ADDR", ":8080"),
		MCPHTTPAddr:        getEnv("MCP_HTTP_ADDR", ":8081"),
		PostgresDSN:        getEnv("POSTGRES_DSN", "postgres://rag:rag@postgres:5432/rag?sslmode=disable"),
		EmbeddingsBaseURL:  getEnv("EMBEDDINGS_BASE_URL", "http://embeddings:8080"),
		EmbeddingModelID:   getEnv("EMBEDDING_MODEL_ID", "Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0"),
		SearchDefaultLimit: 10,
		SearchMaxLimit:     20,
	}

	if cfg.StorageBackend != "postgres" && cfg.StorageBackend != "qdrant" {
		return Config{}, fmt.Errorf("STORAGE_BACKEND must be postgres or qdrant")
	}

	cfg.EmbeddingQueryPrefix = embeddings.DefaultQueryPrefix
	if prefix, ok := os.LookupEnv("EMBEDDING_QUERY_PREFIX"); ok {
		cfg.EmbeddingQueryPrefix = prefix
	}

	var err error

	cfg.EmbeddingDim, err = getEnvInt("EMBEDDING_DIM", 1024)
	if err != nil {
		return Config{}, err
	}

	if cfg.EmbeddingDim < 1 {
		return Config{}, fmt.Errorf("EMBEDDING_DIM must be positive")
	}

	cfg.ChunkSizeRunes, err = getEnvInt("CHUNK_SIZE_RUNES", 1200)
	if err != nil {
		return Config{}, err
	}

	cfg.ChunkOverlapRunes, err = getEnvInt("CHUNK_OVERLAP_RUNES", 200)
	if err != nil {
		return Config{}, err
	}

	cfg.SearchDefaultLimit, err = getEnvInt("SEARCH_DEFAULT_LIMIT", 10)
	if err != nil {
		return Config{}, err
	}

	cfg.SearchMaxLimit, err = getEnvInt("SEARCH_MAX_LIMIT", 20)
	if err != nil {
		return Config{}, err
	}

	return cfg, nil
}

func getEnv(key, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}

	return value
}

func getEnvInt(key string, fallback int) (int, error) {
	raw := os.Getenv(key)
	if raw == "" {
		return fallback, nil
	}

	value, err := strconv.Atoi(raw)
	if err != nil {
		return 0, fmt.Errorf("%s must be int: %w", key, err)
	}

	return value, nil
}
