package storage

import (
	"context"
	"fmt"

	"github.com/pgvector/pgvector-go"
)

func (p *Postgres) Search(ctx context.Context, params SearchParams) ([]SearchRow, error) {
	rows, err := p.pool.Query(ctx, `
		select
			d.id as document_id,
			d.title,
			d.source_uri,
			c.id as chunk_id,
			c.chunk_no,
			c.content as chunk_text,
			1 - (ce.embedding <=> $1) as score
		from chunk_embeddings_v1 ce
		join chunks c on c.id = ce.chunk_id
		join documents d on d.id = c.document_id
		order by ce.embedding <=> $1::vector
		limit $2
	`, pgvector.NewVector(params.Embedding).String(), params.Limit)
	if err != nil {
		return nil, fmt.Errorf("query search: %w", err)
	}
	defer rows.Close()

	var results []SearchRow
	for rows.Next() {
		var row SearchRow
		if err := rows.Scan(
			&row.DocumentID,
			&row.Title,
			&row.SourceURI,
			&row.ChunkID,
			&row.ChunkNo,
			&row.ChunkText,
			&row.Score,
		); err != nil {
			return nil, fmt.Errorf("scan search row: %w", err)
		}
		results = append(results, row)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate search rows: %w", err)
	}

	return results, nil
}
