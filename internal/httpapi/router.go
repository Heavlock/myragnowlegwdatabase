package httpapi

import "net/http"

func NewRouter(api *Handlers, webHandler http.Handler) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/documents/upsert", api.HandleDocumentUpsert)
	mux.HandleFunc("/api/documents/reindex", api.HandleDocumentsReindex)
	mux.HandleFunc("/api/search", api.HandleSearch)
	mux.Handle("/", webHandler)

	return mux
}
