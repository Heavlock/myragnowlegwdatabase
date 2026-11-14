package chunker

import (
	"strings"
	"testing"
)

func TestNormalizeText(t *testing.T) {
	input := "\tСтрока 1\r\n\r\n\r\nСтрока 2\rСтрока 3\t"
	got := NormalizeText(input)
	want := "Строка 1\n\nСтрока 2\nСтрока 3"

	if got != want {
		t.Fatalf("unexpected normalized text:\nwant: %q\ngot:  %q", want, got)
	}
}

func TestSplitUnicodeText(t *testing.T) {
	text := strings.Repeat("Абзац про pgvector и поиск.\n", 80)
	chunks := Split(text, Config{
		ChunkSizeRunes:    1200,
		ChunkOverlapRunes: 200,
	})

	if len(chunks) < 2 {
		t.Fatalf("expected more than one chunk, got %d", len(chunks))
	}

	for _, chunk := range chunks {
		if chunk.Content == "" {
			t.Fatal("chunk content must not be empty")
		}
		if chunk.TokenEstimate <= 0 {
			t.Fatal("token estimate must be positive")
		}
	}
}

func TestSplitLongTextWithoutNewlines(t *testing.T) {
	text := strings.Repeat("длинныйтекст", 300)
	chunks := Split(text, Config{
		ChunkSizeRunes:    1200,
		ChunkOverlapRunes: 200,
	})

	if len(chunks) < 2 {
		t.Fatalf("expected chunks for long text, got %d", len(chunks))
	}

	if chunks[0].CharEnd != 1200 {
		t.Fatalf("expected first chunk end at 1200, got %d", chunks[0].CharEnd)
	}
}
