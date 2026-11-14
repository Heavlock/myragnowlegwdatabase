// Package qdrant implements storage.Repository without a relational dependency.
package qdrant

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"

	"myragnowlegwdatabase/internal/storage"
)

type Config struct {
	URL        string
	APIKey     string
	Collection string
	ModelName  string
	Dimension  int
}

type Repository struct {
	client         *http.Client
	baseURL        string
	collectionPath string
	modelName      string
	dimension      int
}

var _ storage.Repository = (*Repository)(nil)
var collectionName = regexp.MustCompile(`^[A-Za-z0-9_-]{1,200}$`)

type apiError struct {
	status  int
	message string
}

func (e *apiError) Error() string { return fmt.Sprintf("qdrant HTTP %d: %s", e.status, e.message) }

func New(ctx context.Context, cfg Config) (*Repository, error) {
	parsed, err := url.Parse(cfg.URL)
	if err != nil || parsed == nil || parsed.Host == "" || (parsed.Scheme != "http" && parsed.Scheme != "https") || parsed.User != nil || parsed.RawQuery != "" || parsed.Fragment != "" {
		return nil, fmt.Errorf("QDRANT_URL must be an http(s) URL without credentials, query or fragment")
	}
	if !collectionName.MatchString(cfg.Collection) {
		return nil, fmt.Errorf("invalid QDRANT_COLLECTION")
	}
	if cfg.Dimension < 1 || cfg.ModelName == "" {
		return nil, fmt.Errorf("embedding model and positive dimension are required")
	}
	transport := http.DefaultTransport.(*http.Transport).Clone()
	transport.Proxy = nil
	r := &Repository{client: &http.Client{Transport: transport, Timeout: 30 * time.Second}, baseURL: strings.TrimRight(cfg.URL, "/"), collectionPath: "/collections/" + cfg.Collection, modelName: cfg.ModelName, dimension: cfg.Dimension}
	// Credentials belong to the transport so they cannot enter request URLs/errors.
	r.client.Transport = &authenticatedTransport{base: transport, key: cfg.APIKey}
	if err := r.ensureCollection(ctx); err != nil {
		r.Close()
		return nil, err
	}
	return r, nil
}

type authenticatedTransport struct {
	base *http.Transport
	key  string
}

func (t *authenticatedTransport) RoundTrip(request *http.Request) (*http.Response, error) {
	if t.key != "" {
		request = request.Clone(request.Context())
		request.Header.Set("api-key", t.key)
	}
	return t.base.RoundTrip(request)
}
func (t *authenticatedTransport) CloseIdleConnections() { t.base.CloseIdleConnections() }
func (r *Repository) Close()                            { r.client.CloseIdleConnections() }

func (r *Repository) request(ctx context.Context, method, path string, body, result any) error {
	var reader io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("encode qdrant request: %w", err)
		}
		reader = bytes.NewReader(data)
	}
	request, err := http.NewRequestWithContext(ctx, method, r.baseURL+path, reader)
	if err != nil {
		return fmt.Errorf("build qdrant request: %w", err)
	}
	if body != nil {
		request.Header.Set("Content-Type", "application/json")
	}
	response, err := r.client.Do(request)
	if err != nil {
		return fmt.Errorf("request qdrant: %w", err)
	}
	defer response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		message, _ := io.ReadAll(io.LimitReader(response.Body, 4096))
		return &apiError{status: response.StatusCode, message: strings.TrimSpace(string(message))}
	}
	if result == nil {
		_, err = io.Copy(io.Discard, response.Body)
		return err
	}
	var envelope struct {
		Result json.RawMessage `json:"result"`
	}
	if err := json.NewDecoder(io.LimitReader(response.Body, 64<<20)).Decode(&envelope); err != nil {
		return fmt.Errorf("decode qdrant response: %w", err)
	}
	if len(envelope.Result) == 0 {
		return fmt.Errorf("qdrant response has no result")
	}
	if err := json.Unmarshal(envelope.Result, result); err != nil {
		return fmt.Errorf("decode qdrant result: %w", err)
	}
	return nil
}

type vectorConfig struct {
	Size        int    `json:"size"`
	Distance    string `json:"distance"`
	Multivector struct {
		Comparator string `json:"comparator"`
	} `json:"multivector_config"`
}
type collectionInfo struct {
	Config struct {
		Params struct {
			Vectors vectorConfig `json:"vectors"`
		} `json:"params"`
		Metadata struct {
			ModelName     string `json:"model_name"`
			LayoutVersion int    `json:"layout_version"`
		} `json:"metadata"`
	} `json:"config"`
}

func (r *Repository) ensureCollection(ctx context.Context) error {
	var info collectionInfo
	err := r.inspectCollection(ctx, &info, false)
	var failure *apiError
	if errors.As(err, &failure) && failure.status == http.StatusNotFound {
		params := vectorConfig{Size: r.dimension, Distance: "Cosine"}
		params.Multivector.Comparator = "max_sim"
		createErr := r.request(ctx, http.MethodPut, r.collectionPath, map[string]any{"vectors": params, "metadata": map[string]any{"model_name": r.modelName, "layout_version": 1}}, nil)
		// App and MCP may both discover the missing collection. Re-read after either
		// creation outcome, validating the winning schema instead of altering it.
		err = r.inspectCollection(ctx, &info, true)
		if err != nil && createErr != nil {
			return fmt.Errorf("create qdrant collection: %w (inspection: %v)", createErr, err)
		}
	}
	if err != nil {
		return fmt.Errorf("inspect qdrant collection: %w", err)
	}
	vector := info.Config.Params.Vectors
	if info.Config.Metadata.ModelName != r.modelName || info.Config.Metadata.LayoutVersion != 1 || vector.Size != r.dimension || vector.Distance != "Cosine" || vector.Multivector.Comparator != "max_sim" {
		return fmt.Errorf("qdrant collection is incompatible with embedding model %q, dimension %d, or document layout", r.modelName, r.dimension)
	}
	return nil
}

// Collection registration can precede shard readiness when app and MCP start
// together. Retry transient inspection errors without retrying document writes.
func (r *Repository) inspectCollection(ctx context.Context, info *collectionInfo, creating bool) error {
	for attempt := 0; ; attempt++ {
		err := r.request(ctx, http.MethodGet, r.collectionPath, nil, info)
		var failure *apiError
		if !errors.As(err, &failure) || attempt == 19 {
			return err
		}
		transient := failure.status == 500 || failure.status == 503 || (creating && failure.status == 404)
		if !transient {
			return err
		}
		timer := time.NewTimer(100 * time.Millisecond)
		select {
		case <-ctx.Done():
			timer.Stop()
			return ctx.Err()
		case <-timer.C:
		}
	}
}
