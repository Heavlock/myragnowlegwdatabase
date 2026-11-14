-- Run during maintenance with app and mcp stopped. Variables: model_id, embedding_dim.
-- The transaction preserves original documents/chunks but clears derived vectors.
\set ON_ERROR_STOP on
BEGIN;
LOCK TABLE documents, chunks, chunk_embeddings_v1 IN ACCESS EXCLUSIVE MODE;
SELECT 1 / CASE WHEN :'embedding_dim'::integer BETWEEN 1 AND 2000
                     AND length(:'model_id') > 0 THEN 1 ELSE 0 END AS valid_settings;
DELETE FROM chunk_embeddings_v1;
DROP INDEX IF EXISTS chunk_embeddings_v1_embedding_hnsw_idx;
ALTER TABLE chunk_embeddings_v1
  DROP CONSTRAINT IF EXISTS chunk_embeddings_v1_model_name_check,
  DROP CONSTRAINT IF EXISTS chunk_embeddings_v1_embedding_dim_check;
SELECT format('ALTER TABLE chunk_embeddings_v1 ALTER COLUMN embedding TYPE vector(%s)', :'embedding_dim'::integer) \gexec
ALTER TABLE chunk_embeddings_v1
  ADD CONSTRAINT chunk_embeddings_v1_model_name_check CHECK (model_name = :'model_id'),
  ADD CONSTRAINT chunk_embeddings_v1_embedding_dim_check CHECK (embedding_dim = :'embedding_dim'::integer);
CREATE INDEX chunk_embeddings_v1_embedding_hnsw_idx
  ON chunk_embeddings_v1 USING hnsw (embedding vector_cosine_ops);
COMMIT;
