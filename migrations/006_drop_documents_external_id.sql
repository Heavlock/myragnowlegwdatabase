alter table documents
    drop constraint if exists documents_external_id_key;

alter table documents
    drop column if exists external_id;
