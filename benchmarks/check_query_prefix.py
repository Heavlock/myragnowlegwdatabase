"""Compare the current query default with the legacy prefix on frozen EXTRA data.

Uses the original read-only Qwen corpus/query caches; only new query embeddings
are computed. No application or benchmark database is read or written.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import numpy as np

from encode import encode
from retrieval import metric_values, normalize_text


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=Path('.cache/benchmarks/extra-english-kb100/embeddings/qwen-q8'))
    parser.add_argument('--new-cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--container', default='myragnowlegwdatabase-embeddings-1')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    data = root / 'benchmarks/data/extra-english-kb100-v1'
    frozen = json.loads((data / 'manifest.json').read_text())
    for name, digest in frozen['files'].items():
        assert sha(data / name) == digest, name
    chunks = [json.loads(line) for line in (data / 'chunks.jsonl').read_text().splitlines()]
    queries = {q['_id']: q['text'] for q in map(json.loads, (data / 'queries.jsonl').read_text().splitlines())}
    qids = sorted(queries, key=int)
    relevant = {}
    for row in (data / 'qrels/test.tsv').read_text().splitlines()[1:]:
        qid, docid, grade = row.split('\t')
        relevant.setdefault(qid, {})[docid] = int(grade)
    literal = re.search(r'const DefaultQueryPrefix = (".*")', (root / 'internal/embeddings/formatter.go').read_text()).group(1)
    prefix = json.loads(literal)
    legacy = 'task: search result | query: '
    container = json.loads(subprocess.check_output(['docker', 'inspect', args.container], text=True))[0]
    fingerprint = json.loads((args.cache / 'model-fingerprint.json').read_text())
    assert container['Image'] == fingerprint['image'], 'Cached corpus used a different runtime image'
    model_path = Path(next(m['Source'] for m in container['Mounts'] if m['Destination'] == '/models/model.gguf'))
    assert sha(model_path) == fingerprint['file_sha256'], 'Cached corpus used different model weights'
    for mode, texts in [('corpus', [c['payload'] for c in chunks]), ('project-queries', [legacy + normalize_text(queries[q]) for q in qids])]:
        signature = hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode()).hexdigest()
        assert json.loads((args.cache / mode / 'summary.json').read_text())['input_sha256'] == signature, mode
    corpus = np.load(args.cache / 'corpus/vectors.npy')
    old_queries = np.load(args.cache / 'project-queries/vectors.npy')
    ip = next(iter(container['NetworkSettings']['Networks'].values()))['IPAddress']
    new_queries, encoding = encode('http://' + ip + ':8080', [prefix + normalize_text(queries[q]) for q in qids], args.new_cache, 1)
    assert corpus.shape == (200, 1024) and old_queries.shape == new_queries.shape == (320, 1024)
    results = {}
    for mode, vectors in [('legacy', old_queries), ('current_default', new_queries)]:
        rows = []
        for qid, vector in zip(qids, vectors):
            order = np.argsort(-(corpus @ vector), kind='stable')
            ranking = list(dict.fromkeys(chunks[int(i)]['document_id'] for i in order))[:20]
            rows.append({'query_id': qid, 'top20': ranking, 'metrics': metric_values(ranking, relevant[qid])})
        metrics = {name: float(np.mean([r['metrics'][name] for r in rows])) for name in rows[0]['metrics']}
        results[mode] = {'metrics': metrics, 'queries': rows}
    previous = json.loads((root / 'reports/extra-english-kb100/results.json').read_text())
    baseline = next(r['document_metrics'] for r in previous['runs'] if r['model_id'] == 'qwen-q8' and r['mode'] == 'project')
    for name, value in baseline.items():
        assert abs(results['legacy']['metrics'][name] - value) < 1e-10, name
    differences = np.array([b['metrics']['ndcg_at_10'] - a['metrics']['ndcg_at_10'] for a, b in zip(results['legacy']['queries'], results['current_default']['queries'])])
    rng = np.random.default_rng(20261112)
    samples = [float(rng.choice(differences, size=len(differences), replace=True).mean()) for _ in range(2000)]
    report = {
        'dataset': 'EXTRA-English-KB100 v1', 'documents': 100, 'chunks': 200, 'queries': 320,
        'method': 'In-memory exact cosine ranking of unique documents by best chunk; cached corpus identical for both query formats. Legacy metrics cross-checked against the saved PostgreSQL run.',
        'limits': 'One synthetic English dataset; task-specific results do not establish universal improvement. This is not an ANN, database, or timing benchmark.',
        'prefixes': {'legacy': legacy, 'current_default': prefix},
        'model': fingerprint, 'dataset_manifest_sha256': sha(data / 'manifest.json'),
        'corpus_vectors_sha256': sha(args.cache / 'corpus/vectors.npy'),
        'new_query_vectors_sha256': sha(args.new_cache / 'vectors.npy'),
        'query_encoding': encoding, 'results': results,
        'ndcg_at_10_difference': {'difference': float(differences.mean()), 'paired_query_bootstrap_ci95': np.quantile(samples, [.025, .975]).tolist(), 'seed': 20261112, 'resamples': 2000},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v['metrics'] for k, v in results.items()}, indent=2))
    print(json.dumps(report['ndcg_at_10_difference']))


if __name__ == '__main__':
    main()
