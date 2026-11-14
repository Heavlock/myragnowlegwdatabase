package embeddings

import "testing"

func TestModelQueryFormatting(t *testing.T) {
	for _, tc := range []struct{ name, prefix, want string }{
		{"qwen", DefaultQueryPrefix, "Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: employee access"},
		{"bge", "Represent this sentence for searching relevant passages: ", "Represent this sentence for searching relevant passages: employee access"},
		{"unprefixed", "", "employee access"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got, err := FormatSearchQuery("  employee\taccess  ", tc.prefix)
			if err != nil || got != tc.want {
				t.Fatalf("embedding input: got %q, want %q; error: %v", got, tc.want, err)
			}
		})
	}
}

func TestDocumentFormattingDoesNotUseQueryInstruction(t *testing.T) {
	got, err := FormatChunk("Backup policy", "Keep backups for 30 days.")
	const want = "title: Backup policy | text: Keep backups for 30 days."
	if err != nil || got != want {
		t.Fatalf("document input: got %q, want %q; error: %v", got, want, err)
	}
}
