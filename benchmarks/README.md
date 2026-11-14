# English retrieval evaluations

Optional tools for evaluating the application’s retrieval quality. Dataset inputs and runners live here; generated results, logs and HTML reports are written under the ignored `reports/` directory. A fresh checkout has no saved run results.

## Datasets and model configurations

| Dataset | Documents | Queries | Positive judgments | Prepared chunks | Purpose |
| --- | ---: | ---: | ---: | ---: | --- |
| BEIR SciFact test | 5,183 | 300 | 339 | 13,948 | Public English scientific-claim retrieval. |
| EXTRA-English-KB100 v1 | 100 | 320 | 340 | 200 | Original fictional workplace knowledge base, including paraphrases and questions requiring two articles. |

EXTRA is synthetic, not Wikipedia content. The same assistant authored articles and relevance labels, without independent human annotation. Its 100 articles cover ten topics; there are 100 direct, 100 paraphrased, 100 scenario, and 20 multi-article questions. The corpus, queries and relevance labels are in `data/extra-english-kb100-v1/`.

The configurations select Qwen3-Embedding-0.6B Q8_0 (1,024 dimensions), BGE-small-en-v1.5 Q8_0 (384), and all-MiniLM-L6-v2 Q8_0 (384). The runners use local CPU inference through llama.cpp. Model-file checksums and container commands are recorded in each new run’s `results.json`.

## Query formats and ranking units

The benchmark runner compares two query formats:

- `project`: the original common prefix `task: search result | query: ` for all models.
- `recommended`: each model's configured query convention. Qwen uses a fixed dataset-specific instruction; BGE uses its retrieval instruction; MiniLM has no prefix. Exact strings, including newlines/trailing spaces, are recorded in the report.

These modes are historical experiment labels, not a switch that changes the current application. The application now defaults to a general Qwen instruction in the `Instruct: ...\nQuery: ` format and supports `EMBEDDING_QUERY_PREFIX` overrides. The original `project` mode still records the earlier common prefix; `recommended` uses dataset-specific instructions, so neither score is a measurement of the new general default. The [model-switch instructions](../docs/embedding-models.md#switching-the-embedding-model) configure the actual application separately.

The main benchmark tables use exact cosine retrieval and rank unique documents by their best chunk. The application returns chunks and can repeat documents. Separate raw-chunk tables show that behavior with a HNSW index available; PostgreSQL chooses its query plan. Do not substitute document-level scores for chunk-return behavior or assume these measurements benchmark the Qdrant adapter.

Both modes use the project document payload `title: <title> | text: <chunk>` and the original Go chunker at 1,200 runes/200 overlap. BGE uses CLS pooling and a 512-token limit; MiniLM uses mean pooling and a 256-token limit. Their benchmark runner truncates overlength input while retaining the final SEP token. The application chunker uses rune windows and does not implement that benchmark token-truncation step.

## Metrics and interpretation

| Indicator | Interpretation | Display |
| --- | --- | --- |
| Correct first result / Hit@1 | Fraction of queries whose first result is relevant. | Percentage. |
| Recall@10 | Fraction of each query's relevant documents found in the first ten, averaged over queries. | Percentage. |
| MRR@10 | Reciprocal rank of the first relevant result within ten; zero if absent. | Score from 0 to 1. |
| nDCG@10 | Relevance gain discounted by rank and normalized against an ideal ranking. | Score from 0 to 1. |
| ANN chunk Recall@20 | Overlap between approximate and exact top-20 chunk IDs. | Percentage; this is search approximation fidelity, not relevance recall. |

For a question with two relevant articles, finding one first can give Hit@1 = 100% for that question while Recall@10 = 50% if the other is missing. nDCG also considers the positions of all relevant results.

Unjudged documents count as non-relevant. Metrics average queries equally. Duplicate documents consume raw chunk-result positions and receive relevance credit only once. Confidence intervals use 2,000 query bootstrap resamples with seed 20261112. Repeated questions about the same article make EXTRA queries dependent; query-level intervals may be optimistic. Paired model-difference intervals are more useful than comparing separate interval endpoints.

Keep datasets separate when interpreting scores. Record hardware, runtime settings and concurrent work when measuring CPU timings.

## Install dependencies and verify a completed run

Use the pinned optional benchmark dependencies, separate from the Go application. Use Python 3.11 for the pinned benchmark dependencies. If necessary, install [uv using its official instructions](https://docs.astral.sh/uv/getting-started/installation/); it can prepare that interpreter and environment:

```bash
BENCH_ENV="${XDG_CACHE_HOME:-$HOME/.cache}/myrag-benchmark/venv"
if [ ! -x "$BENCH_ENV/bin/python" ]; then
  uv venv --python 3.11 "$BENCH_ENV"
fi
uv pip install --python "$BENCH_ENV/bin/python" -r benchmarks/requirements.txt
"$BENCH_ENV/bin/python" -m unittest discover -s benchmarks -p 'test_*.py'
"$BENCH_ENV/bin/python" benchmarks/validate.py /path/to/completed-run/results.json
```

The validator compares document-level metrics with `pytrec-eval-terrier` and writes `metric-validation.json` beside the results. It does not rerun retrieval. Run this command after retrieval has created the selected results file.

## Run a new experiment

Inference runs are optional and can be expensive. The original harness is tied to the standard local Compose project/network and Qwen embedding service. It is not a general isolated benchmark deployment tool. Restore the default Qwen configuration first; do not run setup against an application currently switched to another model. Example configurations use paths relative to the repository root. Copy them to ignored `benchmarks/*.local.json` files for local paths, ports and container names.

1. Start the standard `myragnowlegwdatabase` Compose project with PostgreSQL and Qwen, following the main README. Confirm the Qwen path and host PostgreSQL port. The default Qwen container name is `myragnowlegwdatabase-embeddings-1`; update the configuration if your Compose project has another name. Setup discovers its network from the container.
2. Copy the JSON configurations to a new experiment directory. Choose a **new output directory, cache, benchmark database name, and BGE/MiniLM container names**. Existing benchmark tables can be replaced by the runner; never point it at the application database or a historical benchmark database you need to retain.
3. Keep model hashes/runtime settings and dataset version fixed when reproducing the same comparison. Use a new dataset version for any article, question, or relevance-label change. The v1 builder deliberately refuses to overwrite its frozen manifest.
4. Run setup with the SciFact configuration once to fetch verified artifacts and prepare SciFact chunks. EXTRA uses the already frozen files under `benchmarks/data/extra-english-kb100-v1`; do not pass its configuration to `setup.py`, which expects SciFact download fields.
5. Run retrieval and independent metric validation for each new configuration. Rendering a new run with its original renderer writes only to that run's new output path; retain its source/configuration snapshot.

The runner entry points, after paths and prerequisites are prepared, are:

```bash
"$BENCH_ENV/bin/python" benchmarks/setup.py --config /path/to/new-scifact-config.json
OPENBLAS_NUM_THREADS=1 "$BENCH_ENV/bin/python" benchmarks/retrieval.py --config /path/to/new-scifact-config.json
OPENBLAS_NUM_THREADS=1 "$BENCH_ENV/bin/python" benchmarks/retrieval.py --config /path/to/new-extra-config.json
"$BENCH_ENV/bin/python" benchmarks/validate.py /path/to/new-run/results.json
```

The paths in this final example are placeholders, not existing project files. Setup may download models and datasets and create benchmark containers; retrieval creates its selected database/tables. Caches are resumable and preserve recorded batch timings, so use a fresh cache to measure fresh inference. Timing reproduction should record hardware, concurrent work, model/container identity, token limits, query format, and whether services/caches were warm.

After a new run, stop/remove only the benchmark containers you created. Keep or remove its database/cache explicitly according to whether you need the evidence. Do not remove the application's shared embedding service or volumes as benchmark cleanup.

## Generated outputs

A retrieval run writes `results.json`, TREC rankings and source/configuration metadata to its configured output directory. Validate that run before interpreting metrics. To generate its HTML report:

```bash
"$BENCH_ENV/bin/python" benchmarks/report.py /path/to/scifact-run/results.json
"$BENCH_ENV/bin/python" benchmarks/extra_report.py /path/to/extra-run/results.json
```

The paths above are placeholders for completed runs. Renderers also write analysis files next to the results. Generated outputs can be removed without changing application code or the dataset inputs kept here.
