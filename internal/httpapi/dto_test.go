package httpapi

import "testing"

func TestUpsertDocumentRequestValidate(t *testing.T) {
	request := UpsertDocumentRequest{
		DocumentID: 12,
		Title:      " title ",
		Content:    " body ",
	}

	input, err := request.Validate()
	if err != nil {
		t.Fatalf("validate returned error: %v", err)
	}

	if input.DocumentID != 12 {
		t.Fatalf("unexpected document_id: %d", input.DocumentID)
	}
	if input.SourceType != "manual" {
		t.Fatalf("unexpected source_type: %q", input.SourceType)
	}
	if input.Language != "en" {
		t.Fatalf("unexpected language: %q", input.Language)
	}
}

func TestUpsertDocumentRequestValidateError(t *testing.T) {
	_, err := (UpsertDocumentRequest{}).Validate()
	if err == nil {
		t.Fatal("expected validation error")
	}
}

func TestUpsertDocumentRequestValidateDocumentIDError(t *testing.T) {
	_, err := (UpsertDocumentRequest{
		DocumentID: -1,
		Title:      "title",
		Content:    "body",
	}).Validate()
	if err == nil {
		t.Fatal("expected validation error")
	}
}

func TestSearchRequestValidate(t *testing.T) {
	request := SearchRequest{
		Query: " pgvector ",
	}

	input, err := request.Validate(10, 20)
	if err != nil {
		t.Fatalf("validate returned error: %v", err)
	}

	if input.Query != "pgvector" {
		t.Fatalf("unexpected query: %q", input.Query)
	}
	if input.Limit != 10 {
		t.Fatalf("unexpected limit: %d", input.Limit)
	}
}

func TestSearchRequestValidateLimitError(t *testing.T) {
	_, err := (SearchRequest{Query: "x", Limit: 21}).Validate(10, 20)
	if err == nil {
		t.Fatal("expected validation error")
	}
}

func TestReindexDocumentsRequestValidateSingle(t *testing.T) {
	input, err := (ReindexDocumentsRequest{
		DocumentIDs: []int64{1, 2},
	}).Validate()
	if err != nil {
		t.Fatalf("validate returned error: %v", err)
	}

	if input.All {
		t.Fatal("expected all=false")
	}
	if len(input.DocumentIDs) != 2 {
		t.Fatalf("unexpected document_ids len: %d", len(input.DocumentIDs))
	}
}

func TestReindexDocumentsRequestValidateAll(t *testing.T) {
	input, err := (ReindexDocumentsRequest{
		All: true,
	}).Validate()
	if err != nil {
		t.Fatalf("validate returned error: %v", err)
	}

	if !input.All {
		t.Fatal("expected all=true")
	}
}

func TestReindexDocumentsRequestValidateError(t *testing.T) {
	_, err := (ReindexDocumentsRequest{}).Validate()
	if err == nil {
		t.Fatal("expected validation error")
	}
}
