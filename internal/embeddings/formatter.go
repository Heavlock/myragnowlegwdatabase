package embeddings

import (
	"fmt"
	"math"
	"unicode/utf8"

	"myragnowlegwdatabase/internal/chunker"
)

// DefaultQueryPrefix follows Qwen3-Embedding's instruction-aware query format.
// Documents are embedded separately, without this query instruction.
const DefaultQueryPrefix = "Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: "

func FormatSearchQuery(query, prefix string) (string, error) {
	normalized := chunker.NormalizeText(query)
	if !utf8.ValidString(normalized) {
		return "", fmt.Errorf("search query is not valid utf-8")
	}

	return prefix + normalized, nil
}

func FormatChunk(title, chunkText string) (string, error) {
	normalizedTitle := chunker.NormalizeText(title)
	normalizedChunk := chunker.NormalizeText(chunkText)
	if !utf8.ValidString(normalizedTitle) || !utf8.ValidString(normalizedChunk) {
		return "", fmt.Errorf("chunk payload is not valid utf-8")
	}

	return fmt.Sprintf("title: %s | text: %s", normalizedTitle, normalizedChunk), nil
}

func NormalizeVector(values []float32) ([]float32, float32, error) {
	if len(values) == 0 {
		return nil, 0, fmt.Errorf("embedding vector is empty")
	}

	var sum float64
	for _, value := range values {
		sum += float64(value * value)
	}

	norm := float32(math.Sqrt(sum))
	if norm == 0 {
		return nil, 0, fmt.Errorf("embedding vector norm is zero")
	}

	normalized := make([]float32, len(values))
	for i, value := range values {
		normalized[i] = value / norm
	}

	return normalized, norm, nil
}
