package rag

type UpsertDocumentInput struct {
	DocumentID int64
	Title      string
	SourceURI  string
	SourceType string
	Language   string
	Content    string
	Metadata   map[string]any
}

type UpsertDocumentResult struct {
	Status        string `json:"status"`
	DocumentID    int64  `json:"document_id"`
	ChunksCreated int    `json:"chunks_created"`
}

type GetDocumentInput struct {
	DocumentID int64
}

type GetDocumentResult struct {
	DocumentID int64          `json:"document_id"`
	Title      string         `json:"title"`
	SourceURI  string         `json:"source_uri"`
	SourceType string         `json:"source_type"`
	Language   string         `json:"language"`
	Content    string         `json:"content"`
	Metadata   map[string]any `json:"metadata"`
}

type SearchInput struct {
	Query string
	Limit int
}

type SearchResult struct {
	Query   string             `json:"query"`
	Limit   int                `json:"limit"`
	Results []SearchResultItem `json:"results"`
}

type SearchResultItem struct {
	DocumentID int64   `json:"document_id"`
	Title      string  `json:"title"`
	SourceURI  string  `json:"source_uri"`
	ChunkID    int64   `json:"chunk_id"`
	ChunkNo    int     `json:"chunk_no"`
	ChunkText  string  `json:"chunk_text"`
	Score      float64 `json:"score"`
}

type ReindexDocumentsInput struct {
	All         bool
	DocumentIDs []int64
}

type ReindexDocumentsResult struct {
	DocumentIDs        []int64 `json:"document_ids"`
	DocumentsReindexed int     `json:"documents_reindexed"`
	ChunksCreatedTotal int     `json:"chunks_created_total"`
}
