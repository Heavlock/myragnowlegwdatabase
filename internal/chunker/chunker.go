package chunker

import (
	"strings"
	"unicode"
)

type Config struct {
	ChunkSizeRunes    int
	ChunkOverlapRunes int
}

type Chunk struct {
	ChunkNo       int
	Content       string
	CharStart     int
	CharEnd       int
	TokenEstimate int
}

func NormalizeText(input string) string {
	normalized := strings.ReplaceAll(input, "\r\n", "\n")
	normalized = strings.ReplaceAll(normalized, "\r", "\n")
	normalized = strings.ReplaceAll(normalized, "\t", " ")
	normalized = strings.TrimSpace(normalized)

	runes := []rune(normalized)
	if len(runes) == 0 {
		return ""
	}

	var builder strings.Builder
	builder.Grow(len(normalized))

	newlineCount := 0
	for _, r := range runes {
		if r == '\n' {
			newlineCount++
			if newlineCount <= 2 {
				builder.WriteRune(r)
			}
			continue
		}

		newlineCount = 0
		builder.WriteRune(r)
	}

	return builder.String()
}

func Split(input string, cfg Config) []Chunk {
	normalized := NormalizeText(input)
	runes := []rune(normalized)
	if len(runes) == 0 {
		return nil
	}

	if cfg.ChunkSizeRunes <= 0 {
		cfg.ChunkSizeRunes = 1200
	}
	if cfg.ChunkOverlapRunes < 0 {
		cfg.ChunkOverlapRunes = 0
	}

	var chunks []Chunk
	start := 0
	chunkNo := 1

	for start < len(runes) {
		windowEnd := min(start+cfg.ChunkSizeRunes, len(runes))
		selectedEnd := chooseChunkEnd(runes, start, windowEnd)

		trimmedStart, trimmedEnd := trimBounds(runes, start, selectedEnd)
		if trimmedStart < trimmedEnd {
			content := string(runes[trimmedStart:trimmedEnd])
			chunks = append(chunks, Chunk{
				ChunkNo:       chunkNo,
				Content:       content,
				CharStart:     trimmedStart,
				CharEnd:       trimmedEnd,
				TokenEstimate: estimateTokens(trimmedEnd - trimmedStart),
			})
			chunkNo++
		}

		nextStart := selectedEnd - cfg.ChunkOverlapRunes
		if nextStart <= start {
			nextStart = selectedEnd
		}
		start = nextStart
	}

	return chunks
}

func chooseChunkEnd(runes []rune, start, windowEnd int) int {
	newlineFrom := min(start+800, windowEnd)
	for i := windowEnd - 1; i >= newlineFrom; i-- {
		if runes[i] == '\n' {
			return i + 1
		}
	}

	punctuationFrom := min(start+900, windowEnd)
	for i := windowEnd - 1; i >= punctuationFrom; i-- {
		switch runes[i] {
		case '.', '!', '?', ';', ':':
			return i + 1
		}
	}

	return windowEnd
}

func trimBounds(runes []rune, start, end int) (int, int) {
	trimmedStart := start
	trimmedEnd := end

	for trimmedStart < trimmedEnd && unicode.IsSpace(runes[trimmedStart]) {
		trimmedStart++
	}
	for trimmedEnd > trimmedStart && unicode.IsSpace(runes[trimmedEnd-1]) {
		trimmedEnd--
	}

	return trimmedStart, trimmedEnd
}

func estimateTokens(runeCount int) int {
	if runeCount <= 0 {
		return 0
	}

	return (runeCount + 3) / 4
}

func min(a, b int) int {
	if a < b {
		return a
	}

	return b
}
