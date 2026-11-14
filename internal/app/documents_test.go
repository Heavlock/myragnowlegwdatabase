package app

import (
	"bytes"
	"context"
	"encoding/json"
	"strings"
	"testing"

	"myragnowlegwdatabase/internal/chunker"
	"myragnowlegwdatabase/internal/rag"
	"myragnowlegwdatabase/internal/storage"
)

type transferRepository struct {
	storage.Repository
	documents []storage.DocumentRecord
	writes    []storage.UpsertDocumentParams
}

func (*transferRepository) Close() {}
func (s *transferRepository) ListDocuments(context.Context) ([]storage.DocumentRecord, error) {
	return s.documents, nil
}
func (s *transferRepository) UpsertDocument(_ context.Context, p storage.UpsertDocumentParams) (storage.UpsertDocumentResult, error) {
	s.writes = append(s.writes, p)
	return storage.UpsertDocumentResult{DocumentID: 999, Created: true, ChunksCreated: len(p.Chunks)}, nil
}

type transferEmbeddings struct{}

func (transferEmbeddings) Embed(_ context.Context, inputs []string) ([][]float32, error) {
	vectors := make([][]float32, len(inputs))
	for i := range vectors {
		vectors[i] = []float32{1, 0}
	}
	return vectors, nil
}
func TestDocumentTransferPreservesSourcesAndRegeneratesVectors(t *testing.T) {
	source := &transferRepository{documents: []storage.DocumentRecord{{DocumentID: 42, Title: "Backup policy", Content: "Backups are retained for fourteen days.", SourceURI: "manual:backup", SourceType: "manual", Language: "en", Metadata: json.RawMessage(`{"nested":{"value":7},"tags":["β"]}`)}}}
	var dump bytes.Buffer
	if err := (&App{storage: source}).ExportDocuments(context.Background(), &dump); err != nil {
		t.Fatal(err)
	}
	target := &transferRepository{}
	a := &App{storage: target, service: rag.NewService(target, transferEmbeddings{}, "new-model", 2, chunker.Config{ChunkSizeRunes: 100, ChunkOverlapRunes: 10}, 10, 20)}
	var output bytes.Buffer
	if err := a.ImportDocuments(context.Background(), bytes.NewReader(dump.Bytes()), &output); err != nil {
		t.Fatal(err)
	}
	if len(target.writes) != 1 {
		t.Fatal(target.writes)
	}
	p := target.writes[0]
	if p.DocumentID != 0 || p.ModelName != "new-model" || p.Content != source.documents[0].Content || len(p.Chunks) < 1 || p.Chunks[0].EmbeddingDim != 2 {
		t.Fatalf("wrong import: %+v", p)
	}
	if !strings.Contains(output.String(), `"document_id":999`) {
		t.Fatal(output.String())
	}
	var metadata map[string]any
	if err := json.Unmarshal(p.Metadata, &metadata); err != nil || metadata["nested"].(map[string]any)["value"] != float64(7) {
		t.Fatalf("metadata: %s %v", p.Metadata, err)
	}
	// Existing data must not be duplicated by rerunning import.
	target.documents = source.documents
	if err := a.ImportDocuments(context.Background(), bytes.NewReader(dump.Bytes()), &output); err == nil {
		t.Fatal("accepted populated target")
	}
	if len(target.writes) != 1 {
		t.Fatal("import wrote to populated target")
	}
	// Decode the complete export before any write, so trailing corrupt JSON cannot partially import it.
	target.documents = nil
	target.writes = nil
	if err := a.ImportDocuments(context.Background(), strings.NewReader(dump.String()+"invalid JSON"), &output); err == nil {
		t.Fatal("accepted corrupt export")
	}
	if len(target.writes) != 0 {
		t.Fatal("corrupt input caused partial writes")
	}
}
