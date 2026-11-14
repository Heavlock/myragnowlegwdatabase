package storage

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/pgvector/pgvector-go"
)

func (p *Postgres) UpsertDocument(ctx context.Context, params UpsertDocumentParams) (UpsertDocumentResult, error) {
	tx, err := p.pool.BeginTx(ctx, pgx.TxOptions{})
	if err != nil {
		return UpsertDocumentResult{}, fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback(ctx)

	var result UpsertDocumentResult

	if params.DocumentID == 0 {
		err = tx.QueryRow(ctx, `
			insert into documents (
				title,
				source_uri,
				source_type,
				language,
				content,
				metadata
			)
			values ($1, $2, $3, $4, $5, $6::jsonb)
			returning id
		`,
			params.Title,
			params.SourceURI,
			params.SourceType,
			params.Language,
			params.Content,
			string(params.Metadata),
		).Scan(&result.DocumentID)
		if err != nil {
			return UpsertDocumentResult{}, fmt.Errorf("insert document: %w", err)
		}

		result.Created = true
	} else {
		err = tx.QueryRow(ctx, `
			update documents
			set
				title = $2,
				source_uri = $3,
				source_type = $4,
				language = $5,
				content = $6,
				metadata = $7::jsonb,
				updated_at = now()
			where id = $1
			returning id
		`,
			params.DocumentID,
			params.Title,
			params.SourceURI,
			params.SourceType,
			params.Language,
			params.Content,
			string(params.Metadata),
		).Scan(&result.DocumentID)
		if err != nil {
			if err == pgx.ErrNoRows {
				return UpsertDocumentResult{}, fmt.Errorf("document %d not found", params.DocumentID)
			}
			return UpsertDocumentResult{}, fmt.Errorf("update document: %w", err)
		}
	}

	if _, err := tx.Exec(ctx, `delete from chunks where document_id = $1`, result.DocumentID); err != nil {
		return UpsertDocumentResult{}, fmt.Errorf("delete chunks: %w", err)
	}

	for _, chunk := range params.Chunks {
		var chunkID int64
		err := tx.QueryRow(ctx, `
			insert into chunks (
				document_id,
				chunk_no,
				content,
				char_start,
				char_end,
				token_estimate
			)
			values ($1, $2, $3, $4, $5, $6)
			returning id
		`,
			result.DocumentID,
			chunk.ChunkNo,
			chunk.Content,
			chunk.CharStart,
			chunk.CharEnd,
			chunk.TokenEstimate,
		).Scan(&chunkID)
		if err != nil {
			return UpsertDocumentResult{}, fmt.Errorf("insert chunk: %w", err)
		}

		_, err = tx.Exec(ctx, `
			insert into chunk_embeddings_v1 (
				chunk_id,
				model_name,
				embedding_dim,
				embedding_norm,
				embedding
			)
			values ($1, $2, $3, $4, $5::vector)
		`,
			chunkID,
			params.ModelName,
			chunk.EmbeddingDim,
			chunk.EmbeddingNorm,
			pgvector.NewVector(chunk.Embedding).String(),
		)
		if err != nil {
			return UpsertDocumentResult{}, fmt.Errorf("insert chunk embedding: %w", err)
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return UpsertDocumentResult{}, fmt.Errorf("commit tx: %w", err)
	}

	result.ChunksCreated = len(params.Chunks)

	return result, nil
}
