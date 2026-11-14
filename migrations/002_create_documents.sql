create table if not exists documents (
    id bigserial primary key,
    title text not null,
    source_uri text not null default '',
    source_type text not null default 'manual',
    language text not null default 'en',
    content text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
