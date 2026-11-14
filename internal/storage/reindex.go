package storage

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5"
)

func (p *Postgres) ListDocuments(ctx context.Context) ([]DocumentRecord, error) {
	rows, err := p.pool.Query(ctx, `
		select
			id,
			title,
			source_uri,
			source_type,
			language,
			content,
			metadata::text
		from documents
		order by id
	`)
	if err != nil {
		return nil, fmt.Errorf("query documents: %w", err)
	}
	defer rows.Close()

	return scanDocuments(rows)
}

func (p *Postgres) GetDocumentsByIDs(ctx context.Context, documentIDs []int64) ([]DocumentRecord, error) {
	rows, err := p.pool.Query(ctx, `
		select
			id,
			title,
			source_uri,
			source_type,
			language,
			content,
			metadata::text
		from documents
		where id = any($1)
		order by id
	`, documentIDs)
	if err != nil {
		return nil, fmt.Errorf("query documents by ids: %w", err)
	}
	defer rows.Close()

	return scanDocuments(rows)
}

func scanDocuments(rows pgx.Rows) ([]DocumentRecord, error) {
	var documents []DocumentRecord
	for rows.Next() {
		var record DocumentRecord
		if err := rows.Scan(
			&record.DocumentID,
			&record.Title,
			&record.SourceURI,
			&record.SourceType,
			&record.Language,
			&record.Content,
			&record.Metadata,
		); err != nil {
			return nil, fmt.Errorf("scan document row: %w", err)
		}
		documents = append(documents, record)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate document rows: %w", err)
	}

	return documents, nil
}
