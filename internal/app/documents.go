package app

import (
	"context"
	"encoding/json"
	"fmt"
	"io"

	"myragnowlegwdatabase/internal/rag"
	"myragnowlegwdatabase/internal/storage"
)

// ExportDocuments writes original documents, without model-specific chunks/vectors.
func (a *App) ExportDocuments(ctx context.Context, output io.Writer) error {
	documents, err := a.storage.ListDocuments(ctx)
	if err != nil {
		return err
	}
	encoder := json.NewEncoder(output)
	for _, document := range documents {
		if err := encoder.Encode(document); err != nil {
			return err
		}
	}
	return nil
}

// ImportDocuments rebuilds embeddings in an empty target. New IDs are allocated.
// An embedding/storage error can leave a partial import; retry in a fresh target.
func (a *App) ImportDocuments(ctx context.Context, input io.Reader, output io.Writer) error {
	existing, err := a.storage.ListDocuments(ctx)
	if err != nil {
		return err
	}
	if len(existing) != 0 {
		return fmt.Errorf("import requires an empty target; use a new collection/database to avoid duplicates")
	}
	decoder := json.NewDecoder(input)
	var documents []rag.UpsertDocumentInput
	for {
		var document storage.DocumentRecord
		if err := decoder.Decode(&document); err == io.EOF {
			break
		} else if err != nil {
			return fmt.Errorf("decode document %d: %w", len(documents)+1, err)
		}
		metadata := map[string]any{}
		if len(document.Metadata) != 0 {
			if err := json.Unmarshal(document.Metadata, &metadata); err != nil {
				return fmt.Errorf("decode metadata: %w", err)
			}
		}
		documents = append(documents, rag.UpsertDocumentInput{Title: document.Title, SourceURI: document.SourceURI, SourceType: document.SourceType, Language: document.Language, Content: document.Content, Metadata: metadata})
	}
	encoder := json.NewEncoder(output)
	for i, document := range documents {
		result, err := a.service.UpsertDocument(ctx, document)
		if err != nil {
			return fmt.Errorf("import document %d: %w", i+1, err)
		}
		if err := encoder.Encode(result); err != nil {
			return err
		}
	}
	return nil
}

// ReindexDocuments rebuilds all embeddings while the HTTP/MCP services are stopped.
func (a *App) ReindexDocuments(ctx context.Context, output io.Writer) error {
	result, err := a.service.ReindexDocuments(ctx, rag.ReindexDocumentsInput{All: true})
	if err != nil {
		return err
	}
	return json.NewEncoder(output).Encode(result)
}
