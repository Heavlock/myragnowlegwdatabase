delete from chunk_embeddings_v1;

drop index if exists chunk_embeddings_v1_embedding_hnsw_idx;

alter table chunk_embeddings_v1
    drop constraint if exists chunk_embeddings_v1_model_name_check;

alter table chunk_embeddings_v1
    drop constraint if exists chunk_embeddings_v1_embedding_dim_check;

alter table chunk_embeddings_v1
    alter column embedding type vector(1024);

alter table chunk_embeddings_v1
    add constraint chunk_embeddings_v1_model_name_check
        check (model_name = 'Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0');

alter table chunk_embeddings_v1
    add constraint chunk_embeddings_v1_embedding_dim_check
        check (embedding_dim = 1024);

create index if not exists chunk_embeddings_v1_embedding_hnsw_idx
    on chunk_embeddings_v1
    using hnsw (embedding vector_cosine_ops);
