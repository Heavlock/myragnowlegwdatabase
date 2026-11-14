CREATE TABLE public.chunk_embeddings_v1 (
	chunk_id bigint NOT NULL,
	model_name text NOT NULL,
	embedding_dim integer NOT NULL,
	embedding_norm real NOT NULL,
	embedding public.vector(1024) NOT NULL,
	created_at timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT chunk_embeddings_v1_embedding_dim_check CHECK ((embedding_dim = 1024)),
	CONSTRAINT chunk_embeddings_v1_model_name_check CHECK ((model_name = 'Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0'::text))
);

--------------------------------------------------------------------------------

CREATE INDEX chunk_embeddings_v1_embedding_hnsw_idx ON public.chunk_embeddings_v1 USING hnsw (embedding public.vector_cosine_ops);

--------------------------------------------------------------------------------

ALTER TABLE public.chunk_embeddings_v1
	ADD CONSTRAINT chunk_embeddings_v1_pkey PRIMARY KEY (chunk_id);

--------------------------------------------------------------------------------

ALTER TABLE public.chunk_embeddings_v1
	ADD CONSTRAINT chunk_embeddings_v1_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.chunks(id) ON DELETE CASCADE;
