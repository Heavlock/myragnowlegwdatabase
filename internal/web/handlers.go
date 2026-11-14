package web

import (
	"encoding/json"
	"fmt"
	"html/template"
	"net/http"
	"strconv"
	"strings"

	"myragnowlegwdatabase/internal/rag"
)

type Handler struct {
	service            *rag.Service
	searchDefaultLimit int
	searchMaxLimit     int
	templates          *template.Template
}

type PageData struct {
	DocumentForm  DocumentFormData
	ReindexForm   ReindexFormData
	SearchForm    SearchFormData
	UpsertResult  *rag.UpsertDocumentResult
	ReindexResult *rag.ReindexDocumentsResult
	SearchResult  *rag.SearchResult
	ErrorMessage  string
	SuccessNotice string
}

type DocumentFormData struct {
	DocumentID string
	Title      string
	SourceURI  string
	SourceType string
	Language   string
	Content    string
	Metadata   string
}

type SearchFormData struct {
	Query string
	Limit int
}

type ReindexFormData struct {
	Mode        string
	DocumentIDs string
}

func NewHandler(service *rag.Service, searchDefaultLimit, searchMaxLimit int, templateGlob string) (*Handler, error) {
	templates, err := template.ParseGlob(templateGlob)
	if err != nil {
		return nil, fmt.Errorf("parse templates: %w", err)
	}

	return &Handler{
		service:            service,
		searchDefaultLimit: searchDefaultLimit,
		searchMaxLimit:     searchMaxLimit,
		templates:          templates,
	}, nil
}

func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodGet:
		h.render(w, PageData{
			DocumentForm: defaultDocumentForm(),
			ReindexForm:  defaultReindexForm(),
			SearchForm: SearchFormData{
				Limit: h.searchDefaultLimit,
			},
		}, http.StatusOK)
	case http.MethodPost:
		h.handlePost(w, r)
	default:
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}

func (h *Handler) handlePost(w http.ResponseWriter, r *http.Request) {
	if err := r.ParseForm(); err != nil {
		h.render(w, PageData{
			DocumentForm: defaultDocumentForm(),
			ReindexForm:  defaultReindexForm(),
			SearchForm: SearchFormData{
				Limit: h.searchDefaultLimit,
			},
			ErrorMessage: "Could not read the form",
		}, http.StatusBadRequest)
		return
	}

	switch r.FormValue("form_kind") {
	case "insert":
		h.handleInsert(w, r)
	case "reindex":
		h.handleReindex(w, r)
	case "search":
		h.handleSearch(w, r)
	default:
		h.render(w, PageData{
			DocumentForm: defaultDocumentForm(),
			ReindexForm:  defaultReindexForm(),
			SearchForm: SearchFormData{
				Limit: h.searchDefaultLimit,
			},
			ErrorMessage: "Unknown form type",
		}, http.StatusBadRequest)
	}
}

func (h *Handler) handleInsert(w http.ResponseWriter, r *http.Request) {
	form := DocumentFormData{
		DocumentID: r.FormValue("document_id"),
		Title:      r.FormValue("title"),
		SourceURI:  r.FormValue("source_uri"),
		SourceType: r.FormValue("source_type"),
		Language:   r.FormValue("language"),
		Content:    r.FormValue("content"),
		Metadata:   r.FormValue("metadata"),
	}

	metadataText := strings.TrimSpace(form.Metadata)
	if metadataText == "" {
		metadataText = "{}"
	}

	metadata := map[string]any{}
	if err := json.Unmarshal([]byte(metadataText), &metadata); err != nil {
		h.render(w, PageData{
			DocumentForm: form,
			ReindexForm:  defaultReindexForm(),
			SearchForm: SearchFormData{
				Limit: h.searchDefaultLimit,
			},
			ErrorMessage: "metadata must be a valid JSON object",
		}, http.StatusBadRequest)
		return
	}

	var documentID int64
	documentIDText := strings.TrimSpace(form.DocumentID)
	if documentIDText != "" {
		parsedDocumentID, err := strconv.ParseInt(documentIDText, 10, 64)
		if err != nil || parsedDocumentID < 0 {
			h.render(w, PageData{
				DocumentForm: form,
				ReindexForm:  defaultReindexForm(),
				SearchForm: SearchFormData{
					Limit: h.searchDefaultLimit,
				},
				ErrorMessage: "document_id must be an integer greater than or equal to 0",
			}, http.StatusBadRequest)
			return
		}
		documentID = parsedDocumentID
	}

	result, err := h.service.UpsertDocument(r.Context(), rag.UpsertDocumentInput{
		DocumentID: documentID,
		Title:      form.Title,
		SourceURI:  form.SourceURI,
		SourceType: form.SourceType,
		Language:   form.Language,
		Content:    form.Content,
		Metadata:   metadata,
	})
	if err != nil {
		h.render(w, PageData{
			DocumentForm: form,
			ReindexForm:  defaultReindexForm(),
			SearchForm: SearchFormData{
				Limit: h.searchDefaultLimit,
			},
			ErrorMessage: err.Error(),
		}, http.StatusBadRequest)
		return
	}

	h.render(w, PageData{
		DocumentForm: DocumentFormData{
			DocumentID: strconv.FormatInt(result.DocumentID, 10),
			Title:      form.Title,
			SourceURI:  form.SourceURI,
			SourceType: form.SourceType,
			Language:   form.Language,
			Content:    form.Content,
			Metadata:   metadataText,
		},
		ReindexForm: defaultReindexForm(),
		SearchForm: SearchFormData{
			Limit: h.searchDefaultLimit,
		},
		UpsertResult:  &result,
		SuccessNotice: "Document saved",
	}, http.StatusOK)
}

func (h *Handler) handleReindex(w http.ResponseWriter, r *http.Request) {
	form := ReindexFormData{
		Mode:        strings.TrimSpace(r.FormValue("reindex_mode")),
		DocumentIDs: strings.TrimSpace(r.FormValue("document_ids")),
	}
	if form.Mode == "" {
		form.Mode = "single"
	}

	input, err := parseReindexForm(form)
	if err != nil {
		h.render(w, PageData{
			DocumentForm: defaultDocumentForm(),
			ReindexForm:  form,
			SearchForm: SearchFormData{
				Limit: h.searchDefaultLimit,
			},
			ErrorMessage: err.Error(),
		}, http.StatusBadRequest)
		return
	}

	result, err := h.service.ReindexDocuments(r.Context(), input)
	if err != nil {
		h.render(w, PageData{
			DocumentForm: defaultDocumentForm(),
			ReindexForm:  form,
			SearchForm: SearchFormData{
				Limit: h.searchDefaultLimit,
			},
			ErrorMessage: err.Error(),
		}, http.StatusBadRequest)
		return
	}

	h.render(w, PageData{
		DocumentForm:  defaultDocumentForm(),
		ReindexForm:   form,
		ReindexResult: &result,
		SearchForm: SearchFormData{
			Limit: h.searchDefaultLimit,
		},
		SuccessNotice: "Reindexing complete",
	}, http.StatusOK)
}

func (h *Handler) handleSearch(w http.ResponseWriter, r *http.Request) {
	limit := h.searchDefaultLimit
	if rawLimit := strings.TrimSpace(r.FormValue("limit")); rawLimit != "" {
		parsedLimit, err := strconv.Atoi(rawLimit)
		if err != nil {
			h.render(w, PageData{
				DocumentForm: defaultDocumentForm(),
				ReindexForm:  defaultReindexForm(),
				SearchForm: SearchFormData{
					Query: r.FormValue("query"),
					Limit: h.searchDefaultLimit,
				},
				ErrorMessage: "limit must be an integer",
			}, http.StatusBadRequest)
			return
		}
		limit = parsedLimit
	}

	searchForm := SearchFormData{
		Query: r.FormValue("query"),
		Limit: limit,
	}

	result, err := h.service.Search(r.Context(), rag.SearchInput{
		Query: searchForm.Query,
		Limit: searchForm.Limit,
	})
	if err != nil {
		h.render(w, PageData{
			DocumentForm: defaultDocumentForm(),
			ReindexForm:  defaultReindexForm(),
			SearchForm:   searchForm,
			ErrorMessage: err.Error(),
		}, http.StatusBadRequest)
		return
	}

	h.render(w, PageData{
		DocumentForm: defaultDocumentForm(),
		ReindexForm:  defaultReindexForm(),
		SearchForm:   searchForm,
		SearchResult: &result,
	}, http.StatusOK)
}

func (h *Handler) render(w http.ResponseWriter, data PageData, status int) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(status)
	_ = h.templates.ExecuteTemplate(w, "layout", data)
}

func defaultDocumentForm() DocumentFormData {
	return DocumentFormData{
		SourceType: "manual",
		Language:   "en",
		Metadata:   "{}",
	}
}

func defaultReindexForm() ReindexFormData {
	return ReindexFormData{
		Mode: "single",
	}
}

func parseReindexForm(form ReindexFormData) (rag.ReindexDocumentsInput, error) {
	switch form.Mode {
	case "all":
		return rag.ReindexDocumentsInput{All: true}, nil
	case "single", "list":
		if form.DocumentIDs == "" {
			return rag.ReindexDocumentsInput{}, fmt.Errorf("Enter a document ID or a list of document IDs")
		}

		parts := strings.Split(form.DocumentIDs, ",")
		documentIDs := make([]int64, 0, len(parts))
		for _, part := range parts {
			part = strings.TrimSpace(part)
			if part == "" {
				continue
			}

			documentID, err := strconv.ParseInt(part, 10, 64)
			if err != nil || documentID < 1 {
				return rag.ReindexDocumentsInput{}, fmt.Errorf("document_ids must contain positive integers")
			}
			documentIDs = append(documentIDs, documentID)
		}

		if len(documentIDs) == 0 {
			return rag.ReindexDocumentsInput{}, fmt.Errorf("Enter a document ID or a list of document IDs")
		}

		if form.Mode == "single" && len(documentIDs) != 1 {
			return rag.ReindexDocumentsInput{}, fmt.Errorf("Single mode requires exactly one document ID")
		}

		return rag.ReindexDocumentsInput{DocumentIDs: documentIDs}, nil
	default:
		return rag.ReindexDocumentsInput{}, fmt.Errorf("Unknown reindex mode")
	}
}
