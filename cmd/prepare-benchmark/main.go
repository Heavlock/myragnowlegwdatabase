// prepare-benchmark applies the application's chunker and document formatting
// to a BEIR corpus. The output is consumed by benchmarks/retrieval.py.
package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"

	"myragnowlegwdatabase/internal/chunker"
	"myragnowlegwdatabase/internal/embeddings"
)

func main() {
	corpus := flag.String("corpus", "", "BEIR corpus.jsonl")
	flag.Parse()
	file, err := os.Open(*corpus)
	if err != nil {
		log.Fatal(err)
	}
	defer file.Close()
	scanner := bufio.NewScanner(file)
	scanner.Buffer(make([]byte, 65536), 16*1024*1024)
	out := bufio.NewWriter(os.Stdout)
	defer out.Flush()
	encoder := json.NewEncoder(out)
	count := 0
	for scanner.Scan() {
		var doc struct {
			ID    string `json:"_id"`
			Title string `json:"title"`
			Text  string `json:"text"`
		}
		if err := json.Unmarshal(scanner.Bytes(), &doc); err != nil {
			log.Fatal(err)
		}
		for _, chunk := range chunker.Split(doc.Text, chunker.Config{ChunkSizeRunes: 1200, ChunkOverlapRunes: 200}) {
			payload, err := embeddings.FormatChunk(doc.Title, chunk.Content)
			if err != nil {
				log.Fatal(err)
			}
			err = encoder.Encode(struct {
				Index      int    `json:"index"`
				DocumentID string `json:"document_id"`
				ChunkNo    int    `json:"chunk_no"`
				Payload    string `json:"payload"`
			}{count, doc.ID, chunk.ChunkNo, payload})
			if err != nil {
				log.Fatal(err)
			}
			count++
		}
	}
	if err := scanner.Err(); err != nil {
		log.Fatal(err)
	}
	fmt.Fprintf(os.Stderr, "prepared %d chunks\n", count)
}
