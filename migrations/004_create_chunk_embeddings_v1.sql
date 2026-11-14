create table if not exists chunk_embeddings_v1 (
    chunk_id bigint primary key references chunks(id) on delete cascade,
    model_name text not null,
    embedding_dim integer not null,
    embedding_norm real not null,
    embedding vector(768) not null,
    created_at timestamptz not null default now(),
    constraint chunk_embeddings_v1_model_name_check
        check (model_name = 'google/embeddinggemma-300m'),
    constraint chunk_embeddings_v1_embedding_dim_check
        check (embedding_dim = 768)
);

create index if not exists chunk_embeddings_v1_embedding_hnsw_idx
    on chunk_embeddings_v1
    using hnsw (embedding vector_cosine_ops);
