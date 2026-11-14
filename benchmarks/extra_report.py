"""Save a standalone EXTRA benchmark report and a browsable labeled dataset."""
import argparse
import collections
import csv
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from report import esc, pct, table

STYLE='''body{font:16px/1.6 system-ui,sans-serif;color:#192638;background:#f3f5f9;margin:0}main{max-width:1200px;margin:32px auto;padding:32px;background:white;border-radius:12px}h1{font-size:32px;line-height:1.2}h2{margin-top:34px}.muted{color:#59677b}.notice{background:#edf4ff;border-left:5px solid #2868b7;padding:14px 20px}.table{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px;border-bottom:1px solid #dce2eb;text-align:left;vertical-align:top}th{background:#edf1f7}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf1f7;padding:16px;font:13px/1.5 ui-monospace,monospace}code{font:13px ui-monospace,monospace}a{color:#19579f}details{margin:14px 0;padding:12px;border:1px solid #dce2eb;border-radius:6px}summary{font-weight:600;cursor:pointer}.pill{background:#edf1f7;border-radius:4px;padding:2px 6px;font-size:12px}input{font:inherit;width:95%;padding:10px;border:1px solid #aeb9ca;border-radius:6px}blockquote{margin:8px 0;padding:8px 16px;border-left:3px solid #b7c9de;background:#f6f8fb}li{margin:7px 0}'''


def page(title,body):
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+'</title><style>'+STYLE+'</style><main>'+body+'</main></html>'


def paired(a,b,seed=20261112):
    assert [x['query_id'] for x in a['per_query']]==[x['query_id'] for x in b['per_query']]
    delta=np.asarray([x['document_metrics']['ndcg_at_10'] for x in a['per_query']])-np.asarray([x['document_metrics']['ndcg_at_10'] for x in b['per_query']])
    rng=np.random.default_rng(seed)
    means=delta[rng.integers(0,len(delta),size=(2000,len(delta)))].mean(axis=1)
    return {'difference':float(delta.mean()),'ci95':[float(x) for x in np.quantile(means,[.025,.975])]}


def browser(data,out,corpus,queries,judgments):
    docs={doc['_id']:doc for doc in corpus}
    question_by_id={q['_id']:q for q in queries}
    body='<h1>EXTRA-English-KB100 v1: articles and questions</h1><p><a href="report.html">Back to test report</a></p><div class="notice">Original fictional company procedures. These are synthetic test fixtures, not real operating policies. Targets were authored by the same assistant as the questions and have not received independent human relevance review.</div>'
    body+='<p>100 articles in 10 clusters; 300 single-article questions plus 20 questions requiring two sources. Expand an article to read it and its three questions. Supporting paragraphs and preselected related distractors are included.</p><input id="filter" type="search" placeholder="Filter articles and their questions" aria-label="Filter articles and questions"><p id="count">100 articles</p>'
    for doc in corpus:
        rows=[j for j in judgments if j['relevant_documents']==[doc['_id']]]
        body+='<details class="article" id="'+esc(doc['_id'])+'"><summary>'+esc(doc['_id']+' — '+doc['title'])+' <span class="pill">'+esc(doc['metadata']['cluster'])+'</span></summary>'
        body+=''.join('<p>'+esc(paragraph)+'</p>' for paragraph in doc['text'].split('\n\n'))
        body+='<h3>Questions and supporting passages</h3>'
        for judgment in rows:
            q=question_by_id[judgment['query_id']]
            body+='<p><strong>Q'+q['_id']+' · '+esc(judgment['kind'])+':</strong> '+esc(q['text'])+'</p><blockquote>'+esc(judgment['evidence'][0]['passage'])+'</blockquote>'
            links=['<a href="#'+esc(i)+'">'+esc(docs[i]['title'])+'</a>' for i in judgment['related_distractor_candidates']]
            body+='<p class="muted">Related distractor candidates: '+', '.join(links)+'. These candidates are lexical neighbors, not independently judged negatives.</p>'
        body+='</details>'
    body+='<h2>Twenty multi-article questions</h2>'
    for j in judgments:
        if j['kind']!='multi_article':continue
        body+='<details><summary>Q'+j['query_id']+': '+esc(question_by_id[j['query_id']]['text'])+'</summary><p>Relevant articles: '+', '.join('<a href="#'+doc+'">'+esc(docs[doc]['title'])+'</a>' for doc in j['relevant_documents'])+'</p></details>'
    body+='''<script>const f=document.getElementById('filter');f.addEventListener('input',()=>{let n=0;for(const e of document.querySelectorAll('.article')){const ok=e.textContent.toLowerCase().includes(f.value.toLowerCase());e.hidden=!ok;if(ok)n++}document.getElementById('count').textContent=n+' articles'});document.addEventListener('click',e=>{const a=e.target.closest('a[href^="#extra_"]');if(a){const t=document.getElementById(a.getAttribute('href').slice(1));if(t){t.hidden=false;t.open=true}}});</script>'''
    (out/'dataset.html').write_text(page('EXTRA article and query browser',body))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path)
    args=parser.parse_args()
    out=args.results.parent
    results=json.loads(args.results.read_text())
    config=json.loads((out/'config.json').read_text())
    data=Path(config['data_directory'])
    manifest=json.loads((data/'manifest.json').read_text())
    assert len(results['runs'])==6 and results['dataset']['documents']==100 and results['dataset']['queries']==320
    assert json.loads((out/'metric-validation.json').read_text())['passed']
    for name,digest in manifest['files'].items():assert hashlib.sha256((data/name).read_bytes()).hexdigest()==digest
    corpus=[json.loads(line) for line in (data/'corpus.jsonl').read_text().splitlines()]
    queries=[json.loads(line) for line in (data/'queries.jsonl').read_text().splitlines()]
    judgments=[json.loads(line) for line in (data/'judgments.jsonl').read_text().splitlines()]
    models={m['id']:m for m in results['models']}
    runs={(r['model_id'],r['mode']):r for r in results['runs']}
    recommended=sorted([r for r in results['runs'] if r['mode']=='recommended'],key=lambda r:-r['document_metrics']['ndcg_at_10'])
    winner=recommended[0]
    comparisons={'qwen_recommended_minus_bge_recommended':paired(runs['qwen-q8','recommended'],runs['bge-small-q8','recommended']),'qwen_recommended_minus_project':paired(runs['qwen-q8','recommended'],runs['qwen-q8','project'])}
    (out/'paired-comparisons.json').write_text(json.dumps(comparisons,indent=2)+'\n')
    headers=['Model','Query format','Hit@1','Recall@5','Recall@10','Recall@20','MRR@10','nDCG@10','App chunk nDCG@10','Corpus embedding seconds','Query embedding p50 ms']
    with (out/'summary.csv').open('w',newline='') as handle:
        writer=csv.writer(handle);writer.writerow(headers)
        for run in results['runs']:
            m=run['document_metrics'];model=models[run['model_id']]
            writer.writerow([model['name'],run['mode'],*[m[key] for key in ['hit_at_1','recall_at_5','recall_at_10','recall_at_20','mrr_at_10','ndcg_at_10']],run['raw_chunk_metrics']['ndcg_at_10'],model['corpus_encoding']['total_seconds'],float(np.median(run['query_embedding']['batch_seconds'])*1000)])
    groups=[]
    for run in results['runs']:
        for kind in ['direct','paraphrase','scenario','multi_article']:
            selected=[q for q in run['per_query'] if q['kind']==kind]
            aggregate={k:float(np.mean([q['document_metrics'][k] for q in selected])) for k in selected[0]['document_metrics']}
            groups.append({'model_id':run['model_id'],'mode':run['mode'],'query_kind':kind,'count':len(selected),'metrics':aggregate})
    (out/'query-type-results.json').write_text(json.dumps(groups,indent=2)+'\n')
    body='<h1>Custom English retrieval test — EXTRA KB100</h1><p class="muted">'+esc(results['created_utc'])+' · 100 authored articles · 320 queries · 3 local GGUF models · no reranker</p>'
    body+='<div class="notice"><strong>Best observed recommended-format nDCG@10: '+esc(models[winner['model_id']]['name'])+' ('+f'{winner["document_metrics"]["ndcg_at_10"]:.4f}'+').</strong> This is a controlled synthetic test, not a new public benchmark or an independently annotated accuracy claim.</div>'
    body+='<h2>Dataset and freeze</h2><p>The corpus is an original fictional Aster Works knowledge base, not Wikipedia text. It contains 100 articles, 10 each on access, recovery, network delivery, incidents, knowledge management, billing, logistics, analytics, workplace operations, and engineering. Each article has three authored questions: direct, paraphrased/follow-up, and constrained scenario. Twenty extra questions request information from two articles, yielding 320 queries and 340 positive judgments.</p>'
    body+='<p>All '+str(results['dataset']['chunks'])+' chunks were produced by the real Go chunker using the current 1,200-character size and 200-character overlap. Documents contain 12,686 words total, with 117–139 words per article. Each label includes an exact supporting passage. Complete questions do not appear verbatim in the article text. Corpus, queries, judgments and qrels were hashed before the first model result; no questions or labels were changed after evaluation.</p>'
    body+='<p><a href="dataset.html">Browse every article, question and supporting passage</a> · <a href="dataset/manifest.json">Frozen manifest</a> · <a href="dataset/audit.json">Dataset checks</a> · <a href="dataset/qrels/test.tsv">Relevance judgments</a></p>'
    body+='<p>The same assistant authored the articles and labels; there was no independent human semantic annotation. The single-source labels identify the intended answer article, but another article might also supply part of an answer. Unjudged sources count as non-relevant. Related distractor candidates were selected by word overlap before evaluation, not mined from model failures.</p>'
    for mode,title in [('recommended','Model-recommended query formats'),('project','Unchanged project query format')]:
        body+='<h2>'+title+'</h2>'
        body+='<p>'+('Each model uses its documented query convention. Qwen receives a fixed workplace-knowledge retrieval instruction chosen before this run. Document formatting is unchanged across modes.' if mode=='recommended' else 'All models receive the existing prefix <code>task: search result | query: </code>. This controls the query formatter while comparing model replacements.')+'</p>'
        selected=sorted([r for r in results['runs'] if r['mode']==mode],key=lambda r:-r['document_metrics']['ndcg_at_10'])
        rows=[]
        for r in selected:
            m=r['document_metrics'];ci=r['ndcg_at_10_ci95']
            rows.append([models[r['model_id']]['name'],pct(m['hit_at_1']),pct(m['recall_at_5']),pct(m['recall_at_10']),pct(m['recall_at_20']),f'{m["mrr_at_10"]:.4f}',f'{m["ndcg_at_10"]:.4f}',f'{ci[0]:.4f}–{ci[1]:.4f}'])
        body+=table(['Model','Hit@1','Recall@5','Recall@10','Recall@20','MRR@10','nDCG@10','nDCG 95% CI'],rows)
    body+='<h2>Interpretation and uncertainty</h2>'
    c=comparisons['qwen_recommended_minus_bge_recommended'];qc=comparisons['qwen_recommended_minus_project']
    body+=f'<p>Recommended-format Qwen minus BGE nDCG@10: {100*c["difference"]:+.2f} percentage points, paired 95% bootstrap CI {100*c["ci95"][0]:+.2f} to {100*c["ci95"][1]:+.2f}. Qwen recommended instruction minus its unchanged project prefix: {100*qc["difference"]:+.2f} points, CI {100*qc["ci95"][0]:+.2f} to {100*qc["ci95"][1]:+.2f}. Intervals use 2,000 query resamples and seed 20261112. Because three questions share each article, query-level intervals may be optimistic; article-level dependence is not modeled.</p>'
    body+='<p>On the earlier SciFact benchmark, recommended-format BGE and Qwen were nearly tied. This controlled workplace corpus tests a different distribution and is much smaller. Higher scores here do not establish general improvement, and differences between these datasets should not be attributed solely to models. Treat these tests as complementary evidence rather than combine their percentages.</p>'
    body+='<h2>Question-type breakdown, recommended formats</h2>'
    body+=table(['Model','Question type','Queries','Hit@1','Recall@10','nDCG@10'],[[models[g['model_id']]['name'],g['query_kind'],g['count'],pct(g['metrics']['hit_at_1']),pct(g['metrics']['recall_at_10']),f'{g["metrics"]["ndcg_at_10"]:.4f}'] for g in groups if g['mode']=='recommended'])
    body+='<h2>Actual chunk-return behavior and approximate indexing</h2><p>The main tables use exact cosine similarity and rank each document by its best chunk. The application returns raw chunks and can repeat a document. Below are metrics for its top-20 chunk SQL with a HNSW index available (m=16, ef_construction=64, ef_search=40). PostgreSQL chooses the query plan; per-model EXPLAIN output is saved in results.json. Duplicate documents consume result positions, and each relevant document gains credit only once.</p>'
    body+=table(['Model','Format','Chunk Hit@1','Chunk Recall@10','Chunk nDCG@10','Overlap with exact top-20 chunks'],[[models[r['model_id']]['name'],r['mode'],pct(r['raw_chunk_metrics']['hit_at_1']),pct(r['raw_chunk_metrics']['recall_at_10']),f'{r["raw_chunk_metrics"]["ndcg_at_10"]:.4f}',pct(r['ann_chunk_recall_at_20'])] for r in results['runs']])
    body+='<h2>CPU timing and model artifacts</h2><p>The configured llama.cpp runtime and model artifacts are recorded in results.json. Models were evaluated sequentially with warm services; corpus batches contain 32 chunks and query batches contain one query. Times exclude downloads and corpus tokenization. This small warm-cache test is not a controlled load or capacity benchmark. Service memory peaks can include earlier activity and are retained in the raw metadata.</p>'
    rows=[]
    for model_id,model in models.items():
        r=runs[model_id,'recommended'];lat=np.asarray(r['query_embedding']['batch_seconds'])*1000
        rows.append([model['name'],model['dim'],f'{model["file_bytes"]/1e6:.1f}',f'{model["corpus_encoding"]["total_seconds"]:.2f}',f'{np.median(lat):.2f}',f'{np.percentile(lat,95):.2f}',model['truncation']['truncated']])
    body+=table(['Model','Dimensions','GGUF MB','Corpus embedding s','Query p50 ms','Query p95 ms','Truncated chunks'],rows)
    body+='<p>BGE uses CLS pooling with a 512-token limit; MiniLM uses mean pooling and a 256-token limit. Qwen uses the deployed last-token pooling and context configuration. Every model receives the same <code>title: &lt;title&gt; | text: &lt;chunk&gt;</code> document payload, and vectors are L2-normalized. Overlength BERT input retains its final SEP token after truncation. Artifact hashes, image IDs, runtime commands and source hashes are saved.</p>'
    body+='<h2>Examples to inspect</h2>'
    failures=[]
    for r in recommended:
        for q in r['per_query']:
            if not q['document_metrics']['hit_at_1']:
                failures.append([models[r['model_id']]['name'],q['query_id'],q['kind'],q['query'],q['top20'][0]['title'],', '.join(q['relevant_documents'])])
                if sum(row[0]==models[r['model_id']]['name'] for row in failures)>=5:break
    body+=table(['Model','Query','Type','Question','First returned article','Expected article IDs'],failures)
    body+='<h2>What the metrics mean</h2><ul><li>Hit@1 is the fraction of queries whose first document is among the authored relevant targets.</li><li>Recall@10 is the fraction of a query relevant targets retrieved in the first ten, averaged over all queries. It is also tested on questions requiring two articles.</li><li>nDCG@10 rewards relevant documents near the top and normalizes by an ideal ranking. The ideal score is 1.</li><li>MRR@10 is the reciprocal rank of the first relevant document within ten results; missing targets score zero.</li></ul>'
    body+='<h2>Saved evidence and reproduction</h2><p><a href="results.json">Full per-query results</a> · <a href="summary.csv">Summary CSV</a> · <a href="query-type-results.json">Question-type results</a> · <a href="paired-comparisons.json">Paired comparisons</a> · <a href="metric-validation.json">Independent trec_eval verification</a> · <a href="config.json">Run configuration</a> · <a href="source-sha256.json">Source hashes</a> · <a href="environment-packages.txt">Package versions</a>.</p>'
    body+='<p>The dataset directory contains corpus, questions, passage-level judgments, qrels, notice and freeze manifest. A source snapshot preserves the evaluated harness. Six TREC run files preserve the top twenty document rankings. The working application and its model were not switched; vectors are stored only in <code>myrag_benchmark_extra</code>.</p>'
    body+='<pre>'+esc('docker start myrag-benchmark-bge myrag-benchmark-minilm\nOPENBLAS_NUM_THREADS=1 ~/.cache/myrag-benchmark/venv/bin/python benchmarks/retrieval.py --config benchmarks/extra-english-kb100.json\n~/.cache/myrag-benchmark/venv/bin/python benchmarks/validate.py reports/extra-english-kb100/results.json\n~/.cache/myrag-benchmark/venv/bin/python benchmarks/extra_report.py reports/extra-english-kb100/results.json')+'</pre>'
    body+='<p>The existing Go preparation command recreates chunks from the frozen corpus. New content or labels require another dataset version; do not edit v1 in response to a model mistake. The benchmark database is isolated from the app database. Changing production to a 384-dimensional model would require schema/configuration changes and reindexing.</p>'
    body+='<h2>Upstream model references</h2><ul>'+''.join('<li><a href="'+esc(m['source'])+'">'+esc(m['name'])+'</a></li>' for m in models.values())+'</ul>'
    (out/'report.html').write_text(page('EXTRA English KB100 retrieval benchmark',body))
    for p in data.rglob('*'):
        if p.is_file():
            target=out/'dataset'/p.relative_to(data);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    browser(data,out,corpus,queries,judgments)
    hashes=json.loads((out/'source-sha256.json').read_text())
    hashes['benchmarks/extra_report.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out/'source-sha256.json').write_text(json.dumps(hashes,indent=2)+'\n')
    for name,digest in hashes.items():
        path=Path(name)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name
        target=out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    print(out/'report.html')
    print(out/'dataset.html')


if __name__=='__main__':
    main()
