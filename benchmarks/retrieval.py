"""Evaluate local GGUF embedders with project chunks and exact pgvector search.

Prerequisites: prepared BEIR corpus, running embedding containers and PostgreSQL.
Install benchmarks/requirements.txt in an isolated Python environment.
Run: python benchmarks/retrieval.py --config benchmarks/scifact.json
"""
import argparse
import csv
import hashlib
import json
import math
import os
import platform
import re
import statistics
import subprocess
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from encode import encode, embed


def metric_values(ranking, relevant):
    relevant = {doc: int(grade) for doc, grade in relevant.items() if int(grade) > 0}
    seen = set()
    gains = []
    for doc in ranking:
        gains.append(relevant.get(doc, 0) if doc not in seen else 0)
        seen.add(doc)
    answer = {'hit_at_1': float(bool(gains and gains[0] > 0))}
    for k in (5, 10, 20):
        answer[f'recall_at_{k}'] = len(set(ranking[:k]) & set(relevant)) / len(relevant)
    answer['mrr_at_10'] = next((1/(i+1) for i, gain in enumerate(gains[:10]) if gain > 0), 0.)
    dcg = sum((2**gain-1)/math.log2(i+2) for i, gain in enumerate(gains[:10]))
    ideal = sorted(relevant.values(), reverse=True)[:10]
    idcg = sum((2**gain-1)/math.log2(i+2) for i, gain in enumerate(ideal))
    answer['ndcg_at_10'] = dcg/idcg if idcg else 0.
    return answer


def normalize_text(text):
    return re.sub(r'\n{3,}', '\n\n', text.replace('\r\n', '\n').replace('\r', '\n').replace('\t', ' ').strip())


def tokenize_and_limit(url, texts, maximum, destination):
    destination = Path(destination)
    signature = hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode()).hexdigest()
    if destination.exists():
        data = json.loads(destination.read_text())
        if data['input_sha256'] != signature or data['max_tokens'] != maximum:
            raise ValueError('Stale tokenization cache: '+str(destination))
        return data['inputs'], data['stats']
    def one(text):
        req = urllib.request.Request(url+'/tokenize', data=json.dumps({'content':text, 'add_special':True}).encode(), headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req, timeout=30) as response:
            tokens = json.load(response)['tokens']
        # Both BERT models use [CLS] and [SEP]; retain final [SEP] on truncation.
        return (tokens if len(tokens) <= maximum else tokens[:maximum-1]+tokens[-1:]), len(tokens)
    with ThreadPoolExecutor(max_workers=8) as pool:
        items = list(pool.map(one, texts))
    inputs = [tokens for tokens, _ in items]
    stats = {'max_tokens':maximum, 'truncated':sum(length > maximum for _,length in items), 'total':len(texts), 'max_input_tokens':max(length for _,length in items)}
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps({'input_sha256':signature,'max_tokens':maximum,'inputs':inputs,'stats':stats}))
    return inputs, stats


def command(*args):
    return subprocess.check_output(args,text=True).strip()


def model_url(container):
    info=json.loads(command('docker','inspect',container))[0]
    networks=info['NetworkSettings']['Networks']
    return 'http://'+next(iter(networks.values()))['IPAddress']+':8080', info


def ensure_database(dsn):
    params=conninfo_to_dict(dsn)
    name=params['dbname']
    assert name.startswith('myrag_benchmark_'), 'Only a dedicated benchmark database is permitted'
    params['dbname']='postgres'
    with psycopg.connect(**params,autocommit=True) as connection:
        exists=connection.execute('SELECT 1 FROM pg_database WHERE datname=%s',(name,)).fetchone()
        if not exists:
            connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    connection=psycopg.connect(dsn,autocommit=True)
    connection.execute('CREATE EXTENSION IF NOT EXISTS vector')
    return connection


def populate(connection, name, chunks, vectors):
    table=sql.Identifier(name)
    connection.execute(sql.SQL('DROP TABLE IF EXISTS {}').format(table))
    connection.execute(sql.SQL('CREATE TABLE {} (chunk_index integer PRIMARY KEY, document_id text NOT NULL, embedding vector({}))').format(table,sql.Literal(vectors.shape[1])))
    tick=time.monotonic()
    with connection.cursor().copy(sql.SQL('COPY {} (chunk_index,document_id,embedding) FROM STDIN').format(table)) as copy:
        for chunk,vector in zip(chunks,vectors):
            copy.write_row((chunk['index'],chunk['document_id'], '['+','.join(format(float(x),'.8g') for x in vector)+']'))
    connection.execute(sql.SQL('ANALYZE {}').format(table))
    connection.execute(sql.SQL('CREATE INDEX {} ON {} USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)').format(sql.Identifier(name+'_hnsw'),table))
    return time.monotonic()-tick


def retrieval(connection, table_name, vector):
    value='['+','.join(format(float(x),'.8g') for x in vector)+']'
    tick=time.monotonic()
    # Exact scan: no ANN index, no reranker. Same cosine operator as the app.
    connection.execute('SET enable_indexscan=off')
    rows=connection.execute(sql.SQL('SELECT chunk_index,document_id,1-(embedding <=> %s::vector) AS score FROM {} ORDER BY embedding <=> %s::vector,chunk_index').format(sql.Identifier(table_name)),(value,value)).fetchall()
    elapsed=time.monotonic()-tick
    chunks=[doc for _,doc,_ in rows[:20]]
    unique=[]
    seen=set()
    for index,doc,score in rows:
        if doc not in seen:
            unique.append((doc,float(score),index))
            seen.add(doc)
            if len(unique)==20: break
    connection.execute('SET enable_indexscan=on')
    connection.execute('SET hnsw.ef_search=40')
    tick=time.monotonic()
    approximate=connection.execute(sql.SQL('SELECT chunk_index,document_id FROM {} ORDER BY embedding <=> %s::vector LIMIT 20').format(sql.Identifier(table_name)),(value,)).fetchall()
    ann_elapsed=time.monotonic()-tick
    exact_indexes={index for index,_,_ in rows[:20]}
    ann_recall=len(exact_indexes & {index for index,_ in approximate})/20
    return unique,chunks,elapsed,[doc for _,doc in approximate],ann_elapsed,ann_recall


def aggregate(per_query, key):
    return {metric:statistics.fmean(row[key][metric] for row in per_query) for metric in per_query[0][key]}


def bootstrap(per_query, key, seed):
    values=np.asarray([row['document_metrics'][key] for row in per_query])
    rng=np.random.default_rng(seed)
    samples=values[rng.integers(0,len(values),size=(2000,len(values)))].mean(axis=1)
    return [float(x) for x in np.quantile(samples,[.025,.975])]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    args=parser.parse_args()
    cfg=json.loads(args.config.read_text())
    cache=Path(cfg['cache'])
    data=Path(cfg['data_directory']) if cfg.get('data_directory') else cache/'datasets'/cfg['dataset']
    out=Path(cfg['output'])
    out.mkdir(parents=True,exist_ok=True)
    corpus={row['_id']:row for row in map(json.loads,(data/'corpus.jsonl').open())}
    query_rows={row['_id']:row for row in map(json.loads,(data/'queries.jsonl').open())}
    queries={qid:row['text'] for qid,row in query_rows.items()}
    qrels={}
    for row in csv.DictReader((data/'qrels/test.tsv').open(),delimiter='\t'):
        if int(row['score']) > 0:
            qrels.setdefault(row['query-id'],{})[row['corpus-id']]=int(row['score'])
    qids=sorted(qrels,key=lambda x:int(x))
    assert len(corpus)==cfg.get('expected_documents',5183) and len(qids)==cfg.get('expected_queries',300)
    assert {grade for relevant in qrels.values() for grade in relevant.values()}=={1}
    assert all(set(relevant)<=set(corpus) for relevant in qrels.values())
    chunks=[json.loads(line) for line in (data/'chunks.jsonl').open()]
    assert {chunk['document_id'] for chunk in chunks}==set(corpus)
    if cfg.get('dataset_manifest'):
        manifest_path=Path(cfg['dataset_manifest'])
        dataset_manifest=json.loads(manifest_path.read_text())
        assert hashlib.sha256(manifest_path.read_bytes()).hexdigest()==cfg['dataset_manifest_sha256'], 'Dataset manifest changed'
        for name,digest in dataset_manifest['files'].items():
            assert hashlib.sha256((data/name).read_bytes()).hexdigest()==digest, 'Frozen dataset changed: '+name
        assert hashlib.sha256((data/'chunks.jsonl').read_bytes()).hexdigest()==cfg['chunks_sha256']
        provenance={'manifest_sha256':cfg['dataset_manifest_sha256'],'files':dataset_manifest['files'],'synthetic':True}
    else:
        archive=cache/'datasets/scifact.zip'
        assert hashlib.md5(archive.read_bytes()).hexdigest()==cfg['dataset_md5']
        provenance={'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'archive_md5':cfg['dataset_md5']}
    connection=ensure_database(cfg['postgres_dsn'])
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'dataset':{'name':cfg.get('dataset_name','BEIR SciFact test'),'documents':len(corpus),'queries':len(qids),'qrels':sum(map(len,qrels.values())),'chunks':len(chunks),'url':cfg.get('dataset_url'),**provenance},'environment':{'cpu':command('lscpu'),'python':platform.python_version(),'numpy':np.__version__,'postgres':connection.execute('SELECT version()').fetchone()[0],'git_head':command('git','rev-parse','HEAD'),'git_diff_sha256':hashlib.sha256(command('git','diff','HEAD').encode()).hexdigest()},'models':[],'runs':[]}
    (out/'config.json').write_text(args.config.read_text())
    source_paths=[*Path('benchmarks').glob('*.py'),*Path('benchmarks').glob('*.json'),Path('benchmarks/requirements.txt'),Path('cmd/prepare-benchmark/main.go'),Path('internal/chunker/chunker.go'),Path('internal/embeddings/formatter.go'),Path('internal/storage/search.go')]
    (out/'source-sha256.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},indent=2)+'\n')
    for model in cfg['models']:
        print('MODEL '+model['name'],flush=True)
        url,container=model_url(model['container'])
        model_dir=cache/'embeddings'/model['id']
        model_dir.mkdir(parents=True,exist_ok=True)
        digest=hashlib.sha256(Path(model['model_file']).read_bytes()).hexdigest()
        assert digest==model['sha256'], 'Model checksum mismatch'
        fingerprint={'file_sha256':digest,'image':container['Image'],'command':container['Config']['Cmd']}
        fp_path=model_dir/'model-fingerprint.json'
        if fp_path.exists() and json.loads(fp_path.read_text())!=fingerprint:
            raise ValueError('Cached model runtime changed')
        fp_path.write_text(json.dumps(fingerprint,indent=2))
        texts=[chunk['payload'] for chunk in chunks]
        truncation={'truncated':0,'total':len(texts)}
        if 'max_tokens' in model:
            texts,truncation=tokenize_and_limit(url,texts,model['max_tokens'],model_dir/'corpus-tokens.json')
        vectors,encoding=encode(url,texts,model_dir/'corpus',32)
        assert vectors.shape==(len(chunks),model['dim'])
        table='chunks_'+model['id'].replace('-','_')
        load_seconds=populate(connection,table,chunks,vectors)
        meta={**model,**fingerprint,'file_bytes':Path(model['model_file']).stat().st_size,'corpus_encoding':encoding,'truncation':truncation,'database_load_seconds':load_seconds,'ann_explain':connection.execute(sql.SQL('EXPLAIN (FORMAT JSON) SELECT chunk_index,document_id FROM {} ORDER BY embedding <=> %s::vector LIMIT 20').format(sql.Identifier(table)),('['+','.join(format(float(x),'.8g') for x in vectors[0])+']',)).fetchone()[0]}
        try:
            meta['service_peak_memory_bytes']=int(command('docker','exec',model['container'],'cat','/sys/fs/cgroup/memory.peak'))
        except (subprocess.CalledProcessError,ValueError): pass
        report['models'].append(meta)
        for mode in ['project','recommended']:
            prefix='task: search result | query: ' if mode=='project' else model['query_prefix']
            query_texts=[prefix+normalize_text(queries[qid]) for qid in qids]
            query_truncation={'truncated':0,'total':len(qids)}
            if 'max_tokens' in model:
                query_texts,query_truncation=tokenize_and_limit(url,query_texts,model['max_tokens'],model_dir/(mode+'-query-tokens.json'))
            query_vectors,query_encoding=encode(url,query_texts,model_dir/(mode+'-queries'),1)
            per_query=[]
            trec=[]
            for qid,vector in zip(qids,query_vectors):
                ranking,raw_chunks,seconds,ann_chunks,ann_seconds,ann_recall=retrieval(connection,table,vector)
                docids=[doc for doc,_,_ in ranking]
                metrics=metric_values(docids,qrels[qid])
                raw_metrics=metric_values(ann_chunks,qrels[qid])
                exact_raw_metrics=metric_values(raw_chunks,qrels[qid])
                per_query.append({'query_id':qid,'query':queries[qid],'kind':query_rows[qid].get('kind','benchmark'),'cluster':query_rows[qid].get('cluster','benchmark'),'relevant_documents':qrels[qid],'top20':[{'document_id':doc,'score':score,'title':corpus[doc]['title']} for doc,score,_ in ranking],'document_metrics':metrics,'raw_chunk_metrics':raw_metrics,'exact_raw_chunk_metrics':exact_raw_metrics,'exact_search_seconds':seconds,'ann_search_seconds':ann_seconds,'ann_chunk_recall_at_20':ann_recall})
                trec.extend(f'{qid} Q0 {doc} {rank} {score:.17g} {model["id"]}-{mode}' for rank,(doc,score,_) in enumerate(ranking,1))
            run={'model_id':model['id'],'mode':mode,'query_prefix':prefix,'document_metrics':aggregate(per_query,'document_metrics'),'raw_chunk_metrics':aggregate(per_query,'raw_chunk_metrics'),'exact_raw_chunk_metrics':aggregate(per_query,'exact_raw_chunk_metrics'),'ann_chunk_recall_at_20':statistics.fmean(r['ann_chunk_recall_at_20'] for r in per_query),'ann_search_p50_ms':float(np.median([r['ann_search_seconds'] for r in per_query])*1000),'ann_search_p95_ms':float(np.percentile([r['ann_search_seconds'] for r in per_query],95)*1000),'ndcg_at_10_ci95':bootstrap(per_query,'ndcg_at_10',cfg['seed']),'hit_at_1_ci95':bootstrap(per_query,'hit_at_1',cfg['seed']),'query_embedding':query_encoding,'query_truncation':query_truncation,'exact_search_p50_ms':float(np.median([r['exact_search_seconds'] for r in per_query])*1000),'exact_search_p95_ms':float(np.percentile([r['exact_search_seconds'] for r in per_query],95)*1000),'per_query':per_query}
            report['runs'].append(run)
            (out/(model['id']+'-'+mode+'.trec')).write_text('\n'.join(trec)+'\n')
            (out/'results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
            print('RESULT '+json.dumps({k:v for k,v in run.items() if k in ['model_id','mode','document_metrics','raw_chunk_metrics']}),flush=True)
    connection.close()
    (out/'environment-packages.txt').write_text(command('uv','pip','freeze','--python',os.sys.executable)+'\n')
    print('COMPLETE '+str(out/'results.json'),flush=True)


if __name__=='__main__':
    main()
