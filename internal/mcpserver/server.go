package mcpserver

import (
	"encoding/json"
	"fmt"
	"net/http"

	"myragnowlegwdatabase/internal/rag"
)

type Server struct {
	service        *rag.Service
	searchMaxLimit int
}

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

type rpcResponse struct {
	JSONRPC string    `json:"jsonrpc"`
	ID      any       `json:"id,omitempty"`
	Result  any       `json:"result,omitempty"`
	Error   *rpcError `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type toolCallParams struct {
	Name      string          `json:"name"`
	Arguments json.RawMessage `json:"arguments"`
}

func NewServer(service *rag.Service, searchMaxLimit int) *Server {
	return &Server{
		service:        service,
		searchMaxLimit: searchMaxLimit,
	}
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var request rpcRequest
	if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
		s.writeError(w, nil, -32700, "parse error")
		return
	}

	if request.JSONRPC == "" {
		request.JSONRPC = "2.0"
	}

	switch request.Method {
	case "initialize":
		s.writeResult(w, request.ID, map[string]any{
			"protocolVersion": "2024-11-05",
			"serverInfo": map[string]any{
				"name":    "myrag-mcp",
				"version": "1.0.0",
			},
			"capabilities": map[string]any{
				"tools": map[string]any{
					"listChanged": false,
				},
			},
		})
	case "notifications/initialized":
		w.WriteHeader(http.StatusAccepted)
	case "tools/list":
		s.writeResult(w, request.ID, map[string]any{
			"tools": ToolDefinitions(),
		})
	case "tools/call":
		var params toolCallParams
		if err := json.Unmarshal(request.Params, &params); err != nil {
			s.writeError(w, request.ID, -32602, "invalid params")
			return
		}

		result, err := s.callTool(r.Context(), params)
		if err != nil {
			s.writeError(w, request.ID, -32000, err.Error())
			return
		}

		s.writeResult(w, request.ID, result)
	default:
		s.writeError(w, request.ID, -32601, fmt.Sprintf("method %q not found", request.Method))
	}
}

func (s *Server) writeResult(w http.ResponseWriter, id json.RawMessage, result any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")

	var decodedID any
	if len(id) > 0 {
		_ = json.Unmarshal(id, &decodedID)
	}

	_ = json.NewEncoder(w).Encode(rpcResponse{
		JSONRPC: "2.0",
		ID:      decodedID,
		Result:  result,
	})
}

func (s *Server) writeError(w http.ResponseWriter, id json.RawMessage, code int, message string) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")

	var decodedID any
	if len(id) > 0 {
		_ = json.Unmarshal(id, &decodedID)
	}

	_ = json.NewEncoder(w).Encode(rpcResponse{
		JSONRPC: "2.0",
		ID:      decodedID,
		Error: &rpcError{
			Code:    code,
			Message: message,
		},
	})
}
