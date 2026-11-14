CREATE SEQUENCE public.documents_id_seq
	START WITH 1
	INCREMENT BY 1
	NO MAXVALUE
	NO MINVALUE
	CACHE 1;

ALTER SEQUENCE public.documents_id_seq
	OWNED BY public.documents.id;
