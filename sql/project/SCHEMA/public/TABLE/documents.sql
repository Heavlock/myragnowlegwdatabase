CREATE TABLE public.documents (
	id bigint DEFAULT nextval('public.documents_id_seq'::regclass) NOT NULL,
	title text NOT NULL,
	source_uri text DEFAULT ''::text NOT NULL,
	source_type text DEFAULT 'manual'::text NOT NULL,
	language text DEFAULT 'en'::text NOT NULL,
	content text NOT NULL,
	metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
	created_at timestamp with time zone DEFAULT now() NOT NULL,
	updated_at timestamp with time zone DEFAULT now() NOT NULL
);

--------------------------------------------------------------------------------

ALTER TABLE public.documents
	ADD CONSTRAINT documents_pkey PRIMARY KEY (id);
