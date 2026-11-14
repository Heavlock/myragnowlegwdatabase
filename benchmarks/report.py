"""Generate a standalone HTML report and summary CSV from measured results."""
import argparse
import csv
import html
import hashlib
import json
import statistics
from pathlib import Path

import numpy as np


def esc(value):
    return html.escape(str(value))


def pct(value):
    return f'{100*value:.2f}%'


def table(headers, rows):
    return '<div class="table"><table><thead><tr>'+''.join('<th>'+esc(v)+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('results',type=Path)
    args=parser.parse_args()
    report=json.loads(args.results.read_text())
    assert len(report['runs'])==6 and len(report['models'])==3, 'Report requires all models and both query formats'
    out=args.results.parent
    names={m['id']:m['name'] for m in report['models']}
    lookup={(r['model_id'],r['mode']):r for r in report['runs']}
    rows=[]
    for mode in ['project','recommended']:
        for run in sorted((r for r in report['runs'] if r['mode']==mode),key=lambda r:-r['document_metrics']['ndcg_at_10']):
            m=run['document_metrics']
            rows.append([names[run['model_id']],mode,*[m[key] for key in ['hit_at_1','recall_at_5','recall_at_10','recall_at_20','mrr_at_10','ndcg_at_10']],run['raw_chunk_metrics']['ndcg_at_10'],run['ann_chunk_recall_at_20'],np.median(run['query_embedding']['batch_seconds'])*1000,run['ann_search_p50_ms']])
    headers=['Model','Query format','Hit@1','Recall@5','Recall@10','Recall@20','MRR@10','nDCG@10','App chunk nDCG@10','ANN chunk Recall@20','Query embed p50 ms','ANN SQL p50 ms']
    with (out/'summary.csv').open('w',newline='') as handle:
        writer=csv.writer(handle); writer.writerow(headers); writer.writerows(rows)
    winner=max((r for r in report['runs'] if r['mode']=='recommended'),key=lambda r:r['document_metrics']['ndcg_at_10'])
    current=lookup[('qwen-q8','project')]
    rng=np.random.default_rng(20261112)
    a=np.asarray([q['document_metrics']['ndcg_at_10'] for q in winner['per_query']])
    b=np.asarray([q['document_metrics']['ndcg_at_10'] for q in current['per_query']])
    paired=(a-b)[rng.integers(0,len(a),size=(2000,len(a)))].mean(axis=1)
    interval=np.quantile(paired,[.025,.975])
    parts=['''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>English retrieval benchmark — SciFact</title>
<style>body{font:16px/1.6 system-ui,sans-serif;color:#182333;background:#f4f6fa;margin:0}main{max-width:1200px;margin:36px auto;padding:36px;background:white;border-radius:12px}h1{font-size:34px;line-height:1.2}h2{margin-top:38px}p{max-width:1050px}.muted{color:#566275}.callout{border-left:5px solid #236ac3;padding:12px 20px;background:#eef5ff}.table{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:11px;border-bottom:1px solid #dae0e8;white-space:nowrap}th{background:#edf1f7}td:first-child{font-weight:600}code,pre{font:13px/1.5 ui-monospace,monospace;background:#edf1f7}pre{padding:16px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere}a{color:#1756a9}details{margin:14px 0}li{margin:8px 0}</style><main>''']
    parts+=['<h1>English retrieval accuracy: SciFact</h1>',f'<p class="muted">Measured locally · {esc(report["created_utc"])} · 3 embedding models · no reranker</p>']
    parts+=[f'<div class="callout"><strong>Best observed recommended-format nDCG@10: {esc(names[winner["model_id"]])}, {pct(winner["document_metrics"]["ndcg_at_10"])}.</strong> Current Qwen deployment format: {pct(current["document_metrics"]["ndcg_at_10"])}. The paired difference is {(a.mean()-b.mean())*100:+.2f} percentage points (95% bootstrap CI {interval[0]*100:+.2f} to {interval[1]*100:+.2f}). This comparison includes the query-format change.</div>']
    qwen_recommended=lookup[('qwen-q8','recommended')]
    bge_recommended=lookup[('bge-small-q8','recommended')]
    def paired_comparison(left,right):
        delta=np.asarray([q['document_metrics']['ndcg_at_10'] for q in left['per_query']])-np.asarray([q['document_metrics']['ndcg_at_10'] for q in right['per_query']])
        generator=np.random.default_rng(20261112)
        sampled=delta[generator.integers(0,len(delta),size=(2000,len(delta)))].mean(axis=1)
        return {'difference':float(delta.mean()),'ci95':[float(x) for x in np.quantile(sampled,[.025,.975])]}
    comparisons={'bge_recommended_minus_qwen_recommended':paired_comparison(bge_recommended,qwen_recommended),'qwen_recommended_minus_project':paired_comparison(qwen_recommended,current)}
    (out/'paired-comparisons.json').write_text(json.dumps(comparisons,indent=2)+'\n')
    comparison=comparisons['bge_recommended_minus_qwen_recommended']
    qcomparison=comparisons['qwen_recommended_minus_project']
    model_by_id={m['id']:m for m in report['models']}
    speedup=model_by_id['qwen-q8']['corpus_encoding']['total_seconds']/model_by_id['bge-small-q8']['corpus_encoding']['total_seconds']
    parts+=['<h2>Interpretation</h2>',f'<p>BGE is a strong candidate for an English-only, CPU-hosted deployment: it indexed this corpus {speedup:.2f} times faster than Qwen, with similar recommended-format document ranking quality. BGE minus Qwen recommended-format nDCG@10 was {comparison["difference"]*100:+.2f} percentage points (paired 95% CI {comparison["ci95"][0]*100:+.2f} to {comparison["ci95"][1]*100:+.2f}); this does not establish an accuracy advantage when the interval includes zero.</p>',f'<p>Updating only the Qwen query instruction improved nDCG@10 by {qcomparison["difference"]*100:.2f} percentage points (paired 95% CI {qcomparison["ci95"][0]*100:+.2f} to {qcomparison["ci95"][1]*100:+.2f}). MiniLM indexed fastest and used the smallest artifact, but had lower observed ranking quality. For a production choice, test your own documents before changing the existing model.</p>']
    parts+=['<h2>Dataset and test scope</h2>',f'<p><a href="https://github.com/beir-cellar/beir/wiki/Datasets-available">BEIR SciFact</a> is an English scientific-claim retrieval benchmark derived from <a href="https://github.com/allenai/scifact">AllenAI SciFact</a>. This run uses all {report["dataset"]["queries"]:,} judged test queries, the full {report["dataset"]["documents"]:,}-document corpus and {report["dataset"]["qrels"]:,} positive relevance judgments. No corpus or query sampling, training or fine-tuning was performed.</p>',f'<p>The real Go chunker produced {report["dataset"]["chunks"]:,} chunks (1,200 Unicode characters, 200-character overlap, existing boundary rules). Every model receives the same document payload: <code>title: &lt;title&gt; | text: &lt;chunk&gt;</code>. We test Q8_0 GGUF artifacts with the same CPU llama.cpp image and L2-normalize all vectors.</p>']
    for mode,title in [('project','Current project query format'),('recommended','Model-recommended query formats')]:
        selected=sorted([r for r in report['runs'] if r['mode']==mode],key=lambda r:-r['document_metrics']['ndcg_at_10'])
        parts+=['<h2>'+title+'</h2>']
        if mode=='project': parts+=['<p>All three models use the exact current application query prefix, <code>task: search result | query: </code>. This is the controlled comparison of embedding replacements with the existing formatter.</p>']
        else: parts+=['<p>Only the query prefix changes. Corpus vectors and document formatting remain identical to the project-format run. These are model-specific documented query conventions, with a fixed scientific-retrieval instruction for Qwen; the instruction was selected before seeing test scores. This is an ablation, not a pure model-only comparison or an official MTEB score.</p>']
        display=[]
        for run in selected:
            m=run['document_metrics']; ci=run['ndcg_at_10_ci95']
            display.append([names[run['model_id']],pct(m['hit_at_1']),pct(m['recall_at_5']),pct(m['recall_at_10']),pct(m['recall_at_20']),f'{m["mrr_at_10"]:.4f}',f'{m["ndcg_at_10"]:.4f}',f'{ci[0]:.4f}–{ci[1]:.4f}'])
        parts+=[table(['Model','Hit@1','Recall@5','Recall@10','Recall@20','MRR@10','nDCG@10','nDCG 95% CI'],display)]
    parts+=['<h2>Effect of query format</h2>']
    display=[]
    for model in report['models']:
        project=lookup[(model['id'],'project')]['document_metrics']['ndcg_at_10']
        recommended=lookup[(model['id'],'recommended')]['document_metrics']['ndcg_at_10']
        display.append([model['name'],f'{project:.4f}',f'{recommended:.4f}',f'{(recommended-project)*100:+.2f} pp',repr(model['query_prefix'])])
    parts+=[table(['Model','Current nDCG@10','Recommended nDCG@10','Difference','Recommended query prefix'],display)]
    parts+=['<h2>Application-style chunk results and approximate search</h2>','<p>The main tables rank unique documents by their best chunk similarity, using exact pgvector cosine search. The application itself returns chunks and can repeat the same document. The table below therefore also evaluates raw top-20 chunks from a pgvector HNSW index with the project’s default settings: m=16, ef_construction=64, ef_search=40. Repeated documents consume result slots; repeated gains are counted only once. ANN chunk Recall@20 measures overlap with exact top-20 chunk IDs, independently of relevance judgments.</p>']
    display=[]
    for run in report['runs']:
        raw=run['raw_chunk_metrics']
        display.append([names[run['model_id']],run['mode'],pct(raw['hit_at_1']),pct(raw['recall_at_10']),f'{raw["ndcg_at_10"]:.4f}',f'{run["exact_raw_chunk_metrics"]["ndcg_at_10"]:.4f}',pct(run['ann_chunk_recall_at_20'])])
    parts+=[table(['Model','Query format','App Hit@1','App Recall@10','App nDCG@10','Exact chunk nDCG@10','ANN chunk Recall@20'],display)]
    parts+=['<h2>Speed and resource observations</h2>','<p>CPU and runtime details are recorded in results.json for this run. Indexing batches contain 32 chunks. Query-embedding timings are individual HTTP requests (batch size 1), excluding tokenization, download and cold model startup. SQL latency excludes query embedding. Timings are observations on a shared desktop, not controlled hardware performance claims. The corpus tokenization and upload timings differ from application upsert latency. Peak service memory is the cgroup peak since service start; Qwen was already running before the benchmark.</p>']
    display=[]
    for model in report['models']:
        run=lookup[(model['id'],'recommended')]
        lat=np.asarray(run['query_embedding']['batch_seconds'])*1000
        seconds=model['corpus_encoding']['total_seconds']
        display.append([model['name'],model['dim'],f'{model["file_bytes"]/1e6:.1f}',f'{model.get("service_peak_memory_bytes",0)/2**20:.0f}',f'{seconds:.1f}',f'{report["dataset"]["chunks"]/seconds:.1f}',f'{np.median(lat):.2f}',f'{np.percentile(lat,95):.2f}',f'{run["ann_search_p50_ms"]:.2f}',f'{run["ann_search_p95_ms"]:.2f}'])
    parts+=[table(['Model','Dimensions','GGUF MB','Peak service MiB','Encode corpus s','Chunks/s','Query p50 ms','Query p95 ms','ANN SQL p50 ms','ANN SQL p95 ms'],display)]
    parts+=['<h2>Truncation and artifacts</h2>','<p>Qwen uses the deployed context and pooling configuration. BGE uses CLS pooling and a 512-token input limit; MiniLM uses mean pooling and its documented 256-token limit. Overlength BERT payloads are truncated on the right while retaining the final SEP token. Token-array input was checked against string input and produced identical embeddings before truncation. These are deployment-artifact results: they should not be presented as scores for full-precision upstream models.</p>']
    parts+=[table(['Model','Truncated chunks','Total chunks','Maximum original tokens','SHA-256'],[[m['name'],m['truncation']['truncated'],m['truncation']['total'],m['truncation'].get('max_input_tokens','not truncated'),m['file_sha256']] for m in report['models']])]
    parts+=['<h2>Metric definitions and uncertainty</h2>','<ul><li><strong>Hit@1</strong>: fraction of queries whose first result is judged relevant. This is the clearest interpretation of search accuracy.</li><li><strong>Recall@k</strong>: fraction of judged relevant documents found in the first k results, averaged equally across queries.</li><li><strong>MRR@10</strong>: reciprocal rank of the first relevant result within the first ten; zero when absent.</li><li><strong>nDCG@10</strong>: discounted relevance gain, normalized against the ideal ranking for each query. Higher is better. SciFact judgments are binary.</li><li>Intervals are query-level percentile bootstrap intervals from 2,000 resamples with seed 20261112. They quantify variation across these queries, not reproducibility across hardware, seeds or datasets.</li></ul>']
    parts+=['<h2>Limits and practical interpretation</h2>','<ul><li>This is one scientific English dataset. It does not establish a universally best model or measure coding or your own knowledge-base queries.</li><li>Document chunking and document formatting intentionally follow this project; therefore the numbers are not directly comparable to published full-document BEIR/MTEB leaderboards.</li><li>Public benchmark exposure during model training cannot be ruled out. Unjudged documents are treated as non-relevant under the standard judged-retrieval convention.</li><li>The project database remains unchanged. Benchmark vectors live in the separate <code>myrag_benchmark_scifact</code> database. No production model or query formatter was switched.</li><li>BGE and MiniLM output 384 dimensions; the current application schema enforces Qwen’s 1,024 dimensions and model ID. Switching production models requires a schema/configuration change and reindexing, not merely replacing the model file.</li></ul>']
    failures=[q for q in current['per_query'] if q['document_metrics']['hit_at_1']==0][:8]
    parts+=['<h2>Examples where the current Qwen setup missed rank 1</h2>']
    parts+=[table(['Query ID','Claim','Top retrieved title','Judged relevant IDs'],[[q['query_id'],q['query'],q['top20'][0]['title'],', '.join(q['relevant_documents'])] for q in failures])]
    parts+=['<h2>Reproduce and inspect</h2>','<p>Run from the repository root. Setup verifies dataset/model hashes, reuses the local Qwen artifact and starts temporary BGE/MiniLM services on the existing project network. Encoding caches are resumable; delete a model’s cache to measure a fresh inference run. Reusing caches preserves the original recorded timings.</p>', '<pre>'+esc('uv venv --python 3.11 ~/.cache/myrag-benchmark/venv\nuv pip install --python ~/.cache/myrag-benchmark/venv/bin/python -r benchmarks/requirements.txt\n~/.cache/myrag-benchmark/venv/bin/python benchmarks/setup.py --config benchmarks/scifact.json\nOPENBLAS_NUM_THREADS=1 ~/.cache/myrag-benchmark/venv/bin/python benchmarks/retrieval.py --config benchmarks/scifact.json\n~/.cache/myrag-benchmark/venv/bin/python benchmarks/validate.py reports/scifact/results.json\n~/.cache/myrag-benchmark/venv/bin/python benchmarks/report.py reports/scifact/results.json')+'</pre>', '<p><a href="results.json">Full results, per-query ranks and metadata</a> · <a href="summary.csv">Summary CSV</a> · <a href="config.json">Run configuration</a> · <a href="environment-packages.txt">Python package versions</a> · <a href="metric-validation.json">Independent trec_eval verification</a> · <a href="source-sha256.json">Source hashes</a> · <a href="paired-comparisons.json">Paired comparisons</a>. Six <code>.trec</code> files contain top-20 document runs for independent evaluation.</p>']
    parts+=['<details><summary>Dataset checksum and runtime environment</summary><pre>'+esc(json.dumps({'dataset':report['dataset'],'environment':report['environment'],'runtime':[{m['id']:m['command']} for m in report['models']]},indent=2))+'</pre></details>']
    parts+=['<h2>Sources</h2><ul><li><a href="https://github.com/beir-cellar/beir/wiki/Datasets-available">BEIR dataset release and checksum</a></li><li><a href="https://github.com/allenai/scifact">AllenAI SciFact dataset and paper</a></li>']
    for model in report['models']:
        parts+=['<li><a href="'+esc(model['source'])+'">'+esc(model['name'])+' upstream model card</a>']
        if model.get('conversion_source'): parts+=[' · <a href="'+esc(model['conversion_source'])+'">Pinned GGUF conversion</a>']
        parts+=['</li>']
    parts+=['</ul></main></html>']
    (out/'report.html').write_text('\n'.join(parts))
    manifest_path=out/'source-sha256.json'
    manifest=json.loads(manifest_path.read_text())
    manifest['benchmarks/report.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    print(out/'report.html')


if __name__=='__main__':
    main()
