"""Create and freeze the authored EXTRA-English-KB100 dataset before scoring."""
import collections
import hashlib
import json
import re
from pathlib import Path

from custom_records import MULTI, RECORDS


def tokens(text):
    return set(re.findall(r'[a-z]{3,}', text.lower()))


def write_jsonl(path, rows):
    path.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows))


def main():
    root=Path('benchmarks/data/extra-english-kb100-v1')
    root.mkdir(parents=True,exist_ok=True)
    if (root/'manifest.json').exists():
        raise SystemExit('Dataset is frozen. Create another version for any content change.')
    assert len(RECORDS)==100 and len(MULTI)==20
    assert len({record['title'] for record in RECORDS})==100
    counts=collections.Counter(record['cluster'] for record in RECORDS)
    assert len(counts)==10 and set(counts.values())=={10}
    corpus=[]; queries=[]; judgments=[]; relevance=[]
    for index,record in enumerate(RECORDS,1):
        document_id=f'extra_{index:03d}'
        assert all(isinstance(p,str) and p.strip() for p in record['paragraphs'])
        text='\n\n'.join(record['paragraphs'])
        assert 85 <= len(text.split()) <= 220, (index,len(text.split()))
        corpus.append({'_id':document_id,'title':record['title'],'text':text,'metadata':{'cluster':record['cluster'],'source':'original synthetic fixture','fictional_organization':'Aster Works'}})
        for paragraph,question,kind in zip(record['paragraphs'],record['queries'],['direct','paraphrase','scenario']):
            qid=str(len(queries)+1)
            assert question.strip().endswith('?'),question
            queries.append({'_id':qid,'text':question,'title':'','kind':kind,'cluster':record['cluster']})
            judgments.append({'query_id':qid,'kind':kind,'cluster':record['cluster'],'relevant_documents':[document_id],'evidence':[{'document_id':document_id,'passage':paragraph}]})
            relevance.append((qid,document_id,1))
    for question,numbers in MULTI:
        qid=str(len(queries)+1)
        assert len(set(numbers))==2
        document_ids=[f'extra_{i:03d}' for i in numbers]
        queries.append({'_id':qid,'text':question,'title':'','kind':'multi_article','cluster':'cross_workflow'})
        judgments.append({'query_id':qid,'kind':'multi_article','cluster':'cross_workflow','relevant_documents':document_ids,'evidence':[{'document_id':f'extra_{i:03d}','passage':'\n\n'.join(RECORDS[i-1]['paragraphs'])} for i in numbers]})
        relevance.extend((qid,doc,1) for doc in document_ids)
    assert len(queries)==320 and len({q['text'] for q in queries})==320
    doc_by_id={doc['_id']:doc for doc in corpus}
    for judgment,query in zip(judgments,queries):
        for evidence in judgment['evidence']:
            assert evidence['passage'] in doc_by_id[evidence['document_id']]['text']
        qt=tokens(query['text'])
        candidates=[]
        for doc in corpus:
            if doc['_id'] in judgment['relevant_documents']: continue
            dt=tokens(doc['title']+' '+doc['text'])
            candidates.append((len(qt&dt)/max(1,len(qt|dt)),doc['_id']))
        judgment['related_distractor_candidates']=[doc for _,doc in sorted(candidates,reverse=True)[:3]]
    write_jsonl(root/'corpus.jsonl',corpus)
    write_jsonl(root/'queries.jsonl',queries)
    write_jsonl(root/'judgments.jsonl',judgments)
    (root/'qrels').mkdir(exist_ok=True)
    (root/'qrels/test.tsv').write_text('query-id\tcorpus-id\tscore\n'+''.join(f'{qid}\t{doc}\t{grade}\n' for qid,doc,grade in relevance))
    manifest={'name':'EXTRA-English-KB100 v1','language':'en','synthetic':True,'documents':100,'queries':320,'positive_judgments':340,'query_types':dict(collections.Counter(q['kind'] for q in queries)),'article_clusters':dict(collections.Counter(r['cluster'] for r in RECORDS)),'source':'Original authored fictional company knowledge base; no Wikipedia text','labeling':'Same assistant authored corpus, questions and targets; no independent human annotation','freeze_policy':'No model results were observed before these corpus and qrels hashes were fixed. Dataset changes require a new version.','source_records_sha256':hashlib.sha256(Path('benchmarks/custom_records.py').read_bytes()).hexdigest(),'files':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'corpus.jsonl',root/'queries.jsonl',root/'judgments.jsonl',root/'qrels/test.tsv',root/'NOTICE.txt']}}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    main()
