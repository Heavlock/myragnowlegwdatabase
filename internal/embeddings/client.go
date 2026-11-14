package embeddings

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"
)

type Client struct {
	baseURL    string
	modelID    string
	httpClient *http.Client
}

type embedRequest struct {
	Input []string `json:"input"`
	Model string   `json:"model"`
}

type embedResponse struct {
	Data []struct {
		Embedding []float32 `json:"embedding"`
	} `json:"data"`
}

func NewClient(baseURL, modelID string) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		modelID: modelID,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (c *Client) ModelID() string {
	return c.modelID
}

func (c *Client) Embed(ctx context.Context, inputs []string) ([][]float32, error) {
	body, err := json.Marshal(embedRequest{
		Input: inputs,
		Model: c.modelID,
	})
	if err != nil {
		return nil, fmt.Errorf("marshal embedding request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/v1/embeddings", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("build embedding request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	log.Printf("embedding request to %s for %d inputs", c.baseURL, len(inputs))

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("call embedding service: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		payload, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		return nil, fmt.Errorf("embedding service returned status %d: %s", resp.StatusCode, strings.TrimSpace(string(payload)))
	}

	var response embedResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, fmt.Errorf("decode embedding response: %w", err)
	}

	vectors := make([][]float32, 0, len(response.Data))
	for _, item := range response.Data {
		vectors = append(vectors, item.Embedding)
	}

	if len(vectors) != len(inputs) {
		return nil, fmt.Errorf("embedding service returned %d vectors for %d inputs", len(vectors), len(inputs))
	}

	return vectors, nil
}
