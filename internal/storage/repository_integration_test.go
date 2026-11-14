package storage_test

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"path/filepath"
	"reflect"
	"runtime"
	"sort"
	"sync"
	"testing"
	"time"

	"myragnowlegwdatabase/internal/qdrant"
	"myragnowlegwdatabase/internal/storage"

	"github.com/testcontainers/testcontainers-go"
	"github.com/testcontainers/testcontainers-go/modules/postgres"
	"github.com/testcontainers/testcontainers-go/wait"
)

const model = "Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0"
const dimension = 1024

type repositoryStore interface {
	storage.Repository
	Close()
}

func TestRepositoryContract(t *testing.T) {
	for _, backend := range []string{"postgres", "qdrant"} {
		t.Run(backend, func(t *testing.T) {
			ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
			defer cancel()
			var open func() (repositoryStore, error)
			if backend == "postgres" {
				container, err := postgres.Run(ctx, "pgvector/pgvector:pg16", postgres.BasicWaitStrategies(), postgres.WithDatabase("rag"), postgres.WithUsername("rag"), postgres.WithPassword("rag"))
				if err != nil {
					t.Fatal(err)
				}
				t.Cleanup(func() { _ = container.Terminate(context.Background()) })
				dsn, err := container.ConnectionString(ctx, "sslmode=disable")
				if err != nil {
					t.Fatal(err)
				}
				open = func() (repositoryStore, error) { return storage.NewPostgres(ctx, dsn) }
				store, err := storage.NewPostgres(ctx, dsn)
				if err != nil {
					t.Fatal(err)
				}
				_, file, _, _ := runtime.Caller(0)
				if err := storage.RunMigrations(ctx, store.Pool(), filepath.Join(filepath.Dir(file), "..", "..", "migrations")); err != nil {
					store.Close()
					t.Fatal(err)
				}
				store.Close()
			} else {
				container, err := testcontainers.GenericContainer(ctx, testcontainers.GenericContainerRequest{ContainerRequest: testcontainers.ContainerRequest{Image: "qdrant/qdrant:v1.20.0", Env: map[string]string{"QDRANT__SERVICE__API_KEY": "contract-key"}, ExposedPorts: []string{"6333/tcp"}, WaitingFor: wait.ForHTTP("/readyz").WithPort("6333/tcp")}, Started: true})
				if err != nil {
					t.Fatal(err)
				}
				t.Cleanup(func() { _ = container.Terminate(context.Background()) })
				endpoint, err := container.PortEndpoint(ctx, "6333/tcp", "http")
				if err != nil {
					t.Fatal(err)
				}
				cfg := qdrant.Config{URL: endpoint, APIKey: "contract-key", Collection: "contract", ModelName: model, Dimension: dimension}
				// The HTTP and MCP processes can both initialize the collection at startup.
				var group sync.WaitGroup
				errors := make(chan error, 2)
				for range 2 {
					group.Add(1)
					go func() {
						defer group.Done()
						r, err := qdrant.New(ctx, cfg)
						if err == nil {
							r.Close()
						}
						errors <- err
					}()
				}
				group.Wait()
				close(errors)
				for err := range errors {
					if err != nil {
						t.Error(err)
					}
				}
				if t.Failed() {
					return
				}
				open = func() (repositoryStore, error) { return qdrant.New(ctx, cfg) }
				wrong := cfg
				wrong.ModelName = "different-model"
				if r, err := qdrant.New(ctx, wrong); err == nil {
					r.Close()
					t.Fatal("accepted incompatible model")
				}
				wrong = cfg
				wrong.Dimension = 2
				if r, err := qdrant.New(ctx, wrong); err == nil {
					r.Close()
					t.Fatal("accepted incompatible dimension")
				}
			}
			repo, err := open()
			if err != nil {
				t.Fatal(err)
			}
			defer repo.Close()
			peer, err := open()
			if err != nil {
				t.Fatal(err)
			}
			defer peer.Close()
			runContract(t, ctx, repo, peer)
			reopened, err := open()
			if err != nil {
				t.Fatal(err)
			}
			defer reopened.Close()
			docs, err := reopened.ListDocuments(ctx)
			if err != nil || len(docs) != 78 {
				t.Fatalf("persistent document count: %d, %v", len(docs), err)
			}
		})
	}
}

func vector(first, second float32) []float32 {
	v := make([]float32, dimension)
	v[0] = first
	v[1] = second
	return v
}
func chunk(no int, text string, first, second float32) storage.ChunkInsert {
	return storage.ChunkInsert{ChunkNo: no, Content: text, Embedding: vector(first, second), EmbeddingDim: dimension, EmbeddingNorm: 1}
}
func document(title string, chunks ...storage.ChunkInsert) storage.UpsertDocumentParams {
	return storage.UpsertDocumentParams{Title: title, SourceURI: "source:" + title, SourceType: "manual", Language: "en", Content: "Full document: " + title, Metadata: []byte(`{"team":"platform","nested":{"n":7},"tags":["alpha","β"]}`), ModelName: model, Chunks: chunks}
}

func runContract(t *testing.T, ctx context.Context, repo, peer storage.Repository) {
	t.Helper()
	docs, err := repo.ListDocuments(ctx)
	if err != nil || len(docs) != 0 {
		t.Fatalf("empty list: %v %v", docs, err)
	}
	missing, err := repo.GetDocumentsByIDs(ctx, []int64{999999})
	if err != nil || len(missing) != 0 {
		t.Fatalf("missing lookup: %v %v", missing, err)
	}
	empty, err := repo.Search(ctx, storage.SearchParams{Embedding: vector(1, 0), Limit: 5})
	if err != nil || len(empty) != 0 {
		t.Fatalf("empty search: %v %v", empty, err)
	}
	a := document("A", chunk(1, "A first", 1, 0), chunk(2, "A second", .99, .01))
	first, err := repo.UpsertDocument(ctx, a)
	if err != nil {
		t.Fatal(err)
	}
	if !first.Created || first.DocumentID <= 0 || first.ChunksCreated != 2 || first.DocumentID > 1<<53-1 {
		t.Fatalf("invalid creation: %+v", first)
	}
	b := document("B", chunk(1, "B first", .8, .2))
	second, err := peer.UpsertDocument(ctx, b)
	if err != nil {
		t.Fatal(err)
	}
	found, err := repo.GetDocumentsByIDs(ctx, []int64{second.DocumentID, first.DocumentID, first.DocumentID, 999999})
	if err != nil || len(found) != 2 {
		t.Fatalf("batch lookup: %+v %v", found, err)
	}
	if found[0].DocumentID >= found[1].DocumentID {
		t.Fatal("documents not sorted")
	}
	for _, d := range found {
		var metadata map[string]any
		if err := json.Unmarshal(d.Metadata, &metadata); err != nil {
			t.Fatal(err)
		}
		if metadata["team"] != "platform" || d.Content != "Full document: "+d.Title || d.Language != "en" || d.SourceURI != "source:"+d.Title {
			t.Fatalf("document round-trip: %+v", d)
		}
	}
	hits, err := repo.Search(ctx, storage.SearchParams{Embedding: vector(1, 0), Limit: 2})
	if err != nil {
		t.Fatal(err)
	}
	if len(hits) != 2 || hits[0].DocumentID != first.DocumentID || hits[1].DocumentID != first.DocumentID || hits[0].ChunkText != "A first" || hits[1].ChunkText != "A second" || math.Abs(hits[0].Score-1) > 1e-5 {
		t.Fatalf("global chunk ranking, including repeat document: %+v", hits)
	}
	originalIDs := map[int64]bool{hits[0].ChunkID: true, hits[1].ChunkID: true}
	broken := document("broken", chunk(1, "bad vector", 1, 0))
	broken.DocumentID = first.DocumentID
	broken.Chunks[0].Embedding = []float32{1, 0}
	if _, err := repo.UpsertDocument(ctx, broken); err == nil {
		t.Fatal("accepted wrong dimension")
	}
	unchanged, err := repo.GetDocumentsByIDs(ctx, []int64{first.DocumentID})
	if err != nil || len(unchanged) != 1 || unchanged[0].Title != "A" {
		t.Fatalf("failed update changed document: %v %v", unchanged, err)
	}
	updated := document("new A", chunk(1, "replacement only", -1, 0))
	updated.DocumentID = first.DocumentID
	saved, err := peer.UpsertDocument(ctx, updated)
	if err != nil {
		t.Fatal(err)
	}
	if saved.Created || saved.DocumentID != first.DocumentID || saved.ChunksCreated != 1 {
		t.Fatalf("replacement: %+v", saved)
	}
	all, err := repo.Search(ctx, storage.SearchParams{Embedding: vector(-1, 0), Limit: 20})
	if err != nil {
		t.Fatal(err)
	}
	if len(all) != 2 || all[0].ChunkText != "replacement only" || all[0].Title != "new A" {
		t.Fatalf("replacement search: %+v", all)
	}
	for _, hit := range all {
		if originalIDs[hit.ChunkID] {
			t.Fatal("stale chunk remained after replacement")
		}
	}
	missingUpdate := document("absent", chunk(1, "absent", 1, 0))
	missingUpdate.DocumentID = 999999
	if _, err := repo.UpsertDocument(ctx, missingUpdate); err == nil {
		t.Fatal("updated nonexistent document")
	}
	// Concurrent writers use independent connections, matching app and MCP.
	failures := make(chan error, 20)
	var writers sync.WaitGroup
	for i := range 8 {
		writers.Add(1)
		go func(i int) {
			defer writers.Done()
			title := fmt.Sprintf("revision-%d", i)
			params := document(title, chunk(1, title, -1, 0))
			params.DocumentID = first.DocumentID
			_, err := peer.UpsertDocument(ctx, params)
			if err != nil {
				failures <- err
			}
		}(i)
	}
	for range 12 {
		current, err := repo.Search(ctx, storage.SearchParams{Embedding: vector(-1, 0), Limit: 1})
		if err != nil {
			failures <- err
			continue
		}
		if len(current) != 1 || (current[0].Title != "new A" && current[0].Title != current[0].ChunkText) {
			failures <- fmt.Errorf("mixed document/chunk revision: %+v", current)
		}
	}
	writers.Wait()
	close(failures)
	for err := range failures {
		t.Error(err)
	}
	// Exceed the adapter's scroll page size and exercise concurrent creates.
	for i := range 68 {
		params := document(fmt.Sprintf("page-%d", i), chunk(1, "page chunk", 0, 1))
		if _, err := repo.UpsertDocument(ctx, params); err != nil {
			t.Fatal(err)
		}
	}
	creations := make(chan storage.UpsertDocumentResult, 8)
	createErrors := make(chan error, 8)
	for i := range 8 {
		writers.Add(1)
		go func(i int) {
			defer writers.Done()
			saved, err := peer.UpsertDocument(ctx, document(fmt.Sprintf("concurrent-%d", i), chunk(1, "created concurrently", 0, 1)))
			if err != nil {
				createErrors <- err
				return
			}
			creations <- saved
		}(i)
	}
	writers.Wait()
	close(creations)
	close(createErrors)
	for err := range createErrors {
		t.Error(err)
	}
	seen := map[int64]bool{}
	for created := range creations {
		if !created.Created || seen[created.DocumentID] {
			t.Fatalf("concurrent creation ID conflict: %+v", created)
		}
		seen[created.DocumentID] = true
	}
	listed, err := repo.ListDocuments(ctx)
	if err != nil || len(listed) != 78 {
		t.Fatalf("paged list: %d %v", len(listed), err)
	}
	listedIDs := make([]int64, len(listed))
	for i, d := range listed {
		listedIDs[i] = d.DocumentID
	}
	expected := append([]int64(nil), listedIDs...)
	sort.Slice(expected, func(i, j int) bool { return expected[i] < expected[j] })
	if !reflect.DeepEqual(listedIDs, expected) {
		t.Fatal("paged document list not ordered")
	}
}
