package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"myragnowlegwdatabase/internal/app"
	"myragnowlegwdatabase/internal/config"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("load config: %v", err)
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	application, err := app.New(ctx, cfg)
	if err != nil {
		log.Fatalf("build application: %v", err)
	}
	defer application.Close()

	mode := "app"
	if len(os.Args) > 1 {
		mode = os.Args[1]
	}

	switch mode {
	case "app":
		if err := application.RunHTTP(ctx); err != nil {
			log.Fatalf("run http server: %v", err)
		}
	case "reindex":
		if err := application.ReindexDocuments(ctx, os.Stdout); err != nil {
			log.Fatalf("reindex documents: %v", err)
		}
	case "export":
		if err := application.ExportDocuments(ctx, os.Stdout); err != nil {
			log.Fatalf("export documents: %v", err)
		}
	case "import":
		if err := application.ImportDocuments(ctx, os.Stdin, os.Stdout); err != nil {
			log.Fatalf("import documents: %v", err)
		}
	case "mcp":
		if err := application.RunMCP(ctx); err != nil {
			log.Fatalf("run mcp server: %v", err)
		}
	default:
		log.Fatalf("unknown mode %q", mode)
	}
}
