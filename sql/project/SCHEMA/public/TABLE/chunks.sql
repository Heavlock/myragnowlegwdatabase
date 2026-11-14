CREATE TABLE public.chunks (
	id bigint DEFAULT nextval('public.chunks_id_seq'::regclass) NOT NULL,
	document_id bigint NOT NULL,
	chunk_no integer NOT NULL,
	content text NOT NULL,
	char_start integer NOT NULL,
	char_end integer NOT NULL,
	token_estimate integer NOT NULL,
	created_at timestamp with time zone DEFAULT now() NOT NULL
);

--------------------------------------------------------------------------------

CREATE INDEX chunks_document_id_idx ON public.chunks USING btree (document_id);

--------------------------------------------------------------------------------

ALTER TABLE public.chunks
	ADD CONSTRAINT chunks_document_id_chunk_no_key UNIQUE (document_id, chunk_no);

--------------------------------------------------------------------------------

ALTER TABLE public.chunks
	ADD CONSTRAINT chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;

--------------------------------------------------------------------------------

ALTER TABLE public.chunks
	ADD CONSTRAINT chunks_pkey PRIMARY KEY (id);
