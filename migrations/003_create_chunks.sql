create table if not exists chunks (
    id bigserial primary key,
    document_id bigint not null references documents(id) on delete cascade,
    chunk_no integer not null,
    content text not null,
    char_start integer not null,
    char_end integer not null,
    token_estimate integer not null,
    created_at timestamptz not null default now(),
    unique (document_id, chunk_no)
);

create index if not exists chunks_document_id_idx on chunks (document_id);
