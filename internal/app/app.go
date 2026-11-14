package app

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"time"

	"myragnowlegwdatabase/internal/chunker"
	"myragnowlegwdatabase/internal/config"
	"myragnowlegwdatabase/internal/embeddings"
	"myragnowlegwdatabase/internal/httpapi"
	"myragnowlegwdatabase/internal/mcpserver"
	"myragnowlegwdatabase/internal/qdrant"
	"myragnowlegwdatabase/internal/rag"
	"myragnowlegwdatabase/internal/storage"
	"myragnowlegwdatabase/internal/web"
)

type managedRepository interface {
	storage.Repository
	Close()
}

type App struct {
	config  config.Config
	storage managedRepository
	service *rag.Service
}

func New(ctx context.Context, cfg config.Config) (*App, error) {
	var store managedRepository
	var err error
	switch cfg.StorageBackend {
	case "postgres":
		store, err = storage.NewPostgres(ctx, cfg.PostgresDSN)
	case "qdrant":
		store, err = qdrant.New(ctx, qdrant.Config{URL: cfg.QdrantURL, APIKey: cfg.QdrantAPIKey, Collection: cfg.QdrantCollection, ModelName: cfg.EmbeddingModelID, Dimension: cfg.EmbeddingDim})
	default:
		return nil, fmt.Errorf("unsupported storage backend %q", cfg.StorageBackend)
	}
	if err != nil {
		return nil, err
	}
	log.Printf("using %s repository", cfg.StorageBackend)

	service := rag.NewService(
		store,
		embeddings.NewClient(cfg.EmbeddingsBaseURL, cfg.EmbeddingModelID),
		cfg.EmbeddingModelID,
		cfg.EmbeddingDim,
		chunker.Config{
			ChunkSizeRunes:    cfg.ChunkSizeRunes,
			ChunkOverlapRunes: cfg.ChunkOverlapRunes,
		},
		cfg.SearchDefaultLimit,
		cfg.SearchMaxLimit,
	).WithQueryPrefix(cfg.EmbeddingQueryPrefix)

	return &App{
		config:  cfg,
		storage: store,
		service: service,
	}, nil
}

func (a *App) Close() {
	if a.storage != nil {
		a.storage.Close()
	}
}

func (a *App) RunHTTP(ctx context.Context) error {
	webHandler, err := web.NewHandler(
		a.service,
		a.config.SearchDefaultLimit,
		a.config.SearchMaxLimit,
		"internal/web/templates/*.html",
	)
	if err != nil {
		return err
	}

	apiHandlers := httpapi.NewHandlers(a.service, a.config.SearchDefaultLimit, a.config.SearchMaxLimit)
	server := &http.Server{
		Addr:              a.config.AppHTTPAddr,
		Handler:           httpapi.NewRouter(apiHandlers, webHandler),
		ReadHeaderTimeout: 10 * time.Second,
	}

	log.Printf("starting HTTP API on %s", a.config.AppHTTPAddr)

	return runServer(ctx, server)
}

func (a *App) RunMCP(ctx context.Context) error {
	server := &http.Server{
		Addr:              a.config.MCPHTTPAddr,
		Handler:           routeMCP(mcpserver.NewServer(a.service, a.config.SearchMaxLimit)),
		ReadHeaderTimeout: 10 * time.Second,
	}

	log.Printf("starting MCP server on %s", a.config.MCPHTTPAddr)

	return runServer(ctx, server)
}

func routeMCP(handler http.Handler) http.Handler {
	mux := http.NewServeMux()
	mux.Handle("/mcp", handler)
	return mux
}

func runServer(ctx context.Context, server *http.Server) error {
	errCh := make(chan error, 1)

	go func() {
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			errCh <- err
			return
		}
		errCh <- nil
	}()

	select {
	case <-ctx.Done():
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_ = server.Shutdown(shutdownCtx)
		return nil
	case err := <-errCh:
		return err
	}
}
