#!/usr/bin/env python3
"""Execute documented model-switch blocks against isolated stacks, or check one phase."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
REPORT=ROOT/'reports/model-switch'


def request(url,body=None):
    data=None if body is None else json.dumps(body).encode()
    with urllib.request.urlopen(urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'}),timeout=120) as response:
        return json.load(response)


def compose(*args,**kwargs):
    return subprocess.run(['docker','compose','--profile',os.environ['PROFILE'],*args],check=True,**kwargs)


def output(*args,extra=None):
    env=os.environ.copy();env.update(extra or {})
    return subprocess.check_output(['docker','compose','--profile',env['PROFILE'],*args],env=env,text=True)


def wait_ready(base):
    for _ in range(90):
        try:
            with urllib.request.urlopen(base+'/',timeout=3) as response:
                assert '<html lang="en">' in response.read().decode()
                return
        except (OSError,AssertionError):time.sleep(1)
    raise RuntimeError('Application not ready: '+base)


def phase_check(phase):
    profile=os.environ['PROFILE'];base='http://127.0.0.1:'+os.environ['POSTGRES_APP_PORT' if profile=='postgres' else 'QDRANT_APP_PORT']
    mcp='http://127.0.0.1:'+os.environ['POSTGRES_MCP_PORT' if profile=='postgres' else 'QDRANT_MCP_PORT']+'/mcp'
    service='app' if profile=='postgres' else 'app-qdrant'
    mcp_service='mcp' if profile=='postgres' else 'mcp-qdrant'
    state_path=REPORT/(profile+'-state.json')
    wait_ready(base)
    def rpc(name,arguments):
        result=request(mcp,{'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':name,'arguments':arguments}})
        assert 'error' not in result,result
        return result['result']['structuredContent']
    if phase=='initial':
        documents=[
          {'title':'Vector search','content':'pgvector adds vector storage and similarity search to PostgreSQL. Qdrant is a vector database that supports semantic search.'},
          {'title':'Employee account access','content':'Alice Morgan manages employee account permissions. Ask Alice to approve new user access and changes to authorization roles.'},
          {'title':'Greenhouse tomatoes','content':'Tomato plants need regular watering and good greenhouse ventilation. Harvest ripe tomatoes during summer.'},
          {'title':'Incident review procedure','content':('After an incident, write a review of the root cause and recovery actions. Record the timeline, impact, and follow-up owners. '*20)},
        ]
        for i,doc in enumerate(documents):
            doc['content']=doc['content'].strip()
            doc.update(source_uri=f'model-switch:{i}',source_type='manual',language='en',metadata={'nested':{'version':7},'tags':['english','β']})
            result=request(base+'/api/documents/upsert',doc)
            assert result['status']=='created' and result['chunks_created']>0,result
            doc['document_id']=result['document_id']
        state={'profile':profile,'documents':documents,'checks':[]}
        state_path.write_text(json.dumps(state,indent=2)+'\n')
        # A rejected dimension must roll back the SQL transaction without touching data/vectors.
        if profile=='postgres':
            with (ROOT/'deployments/postgres/switch_embedding_model.sql').open('rb') as sql:
                p=subprocess.run(['docker','compose','--profile','postgres','exec','-T','postgres','psql','-U','rag','-d','rag','-v','ON_ERROR_STOP=1','-v','model_id=invalid','-v','embedding_dim=3000'],stdin=sql,capture_output=True)
            assert p.returncode!=0 and b'division by zero' in p.stderr
    else:
        state=json.loads(state_path.read_text())
    records=[json.loads(line) for line in output('run','--rm','-T','--no-deps',service,'export').splitlines()]
    expected={d['source_uri']:d for d in state['documents']}
    assert len(records)==len(expected)==4
    dimension=384 if phase=='bge' else 1024
    model='BAAI/bge-small-en-v1.5:Q8_0' if phase=='bge' else 'Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0'
    for actual in records:
        old=expected[actual['source_uri']]
        for field in ['title','content','source_uri','source_type','language','metadata']:assert actual[field]==old[field],(field,actual,old)
        if profile=='postgres' or phase!='bge':assert actual['document_id']==old['document_id']
        else:assert actual['document_id']!=old['document_id']
        assert rpc('get_document',{'document_id':actual['document_id']})==actual
    for query,title in [('How can PostgreSQL search similar vectors?','Vector search'),('Who approves employee account permissions?','Employee account access')]:
        result=request(base+'/api/search',{'query':query,'limit':4})
        assert any(row['title']==title for row in result['results']),result
        assert all(math.isfinite(row['score']) for row in result['results']),result
        assert all(result['results'][i]['score']>=result['results'][i+1]['score'] for i in range(len(result['results'])-1))
        hits=rpc('search_chunks',{'query':query,'limit':4})
        assert hits['results'] and any(row['title']==title for row in hits['results']),hits
    if profile=='postgres':
        sql="SELECT model_name || '|' || embedding_dim || '|' || vector_dims(embedding) || '|' || count(*) FROM chunk_embeddings_v1 GROUP BY model_name,embedding_dim,vector_dims(embedding)"
        values=output('exec','-T','postgres','psql','-U','rag','-d','rag','-At','-c',sql).strip().splitlines()
        assert len(values)==1 and values[0].startswith(f'{model}|{dimension}|{dimension}|'),values
        assert int(values[0].split('|')[-1])>4 # includes multi-chunk documents
    else:
        collection=os.environ.get('QDRANT_COLLECTION','myrag_documents')
        qbase='http://127.0.0.1:'+os.environ['QDRANT_PORT']
        info=request(qbase+'/collections/'+collection)['result']
        assert info['config']['params']['vectors']['size']==dimension and info['config']['metadata']['model_name']==model,info
        points=request(qbase+'/collections/'+collection+'/points/scroll',{'limit':100,'with_vector':True,'with_payload':False})['result']['points']
        assert len(points)==4
        assert all(len(vector)==dimension for point in points for vector in point['vector'])
    if phase=='bge':
        if profile=='qdrant':
            # An old collection must reject the new model even though it still contains documents.
            bad=os.environ.copy();bad['QDRANT_COLLECTION']=os.environ['PREVIOUS_QDRANT_COLLECTION']
            p=subprocess.run(['docker','compose','--profile','qdrant','run','--rm','-T','--no-deps',service,'export'],env=bad,capture_output=True)
            assert p.returncode!=0 and b'incompatible' in p.stderr
            with open(os.environ['SWITCH_BACKUP_DIR']+'/documents.jsonl','rb') as dump:
                p=subprocess.run(['docker','compose','--profile','qdrant','run','--rm','-T','--no-deps',service,'import'],stdin=dump,capture_output=True)
            assert p.returncode!=0 and b'empty target' in p.stderr
        else:
            # Prove the pre-switch dump is usable without touching the live test DB.
            compose('exec','-T','postgres','createdb','-U','rag','model_switch_restore')
            with open(os.environ['SWITCH_BACKUP_DIR']+'/postgres.dump','rb') as dump:
                compose('exec','-T','postgres','pg_restore','-U','rag','-d','model_switch_restore',stdin=dump)
            restored=output('exec','-T','postgres','psql','-U','rag','-d','model_switch_restore','-At','-c','SELECT count(*) FROM documents; SELECT DISTINCT vector_dims(embedding) FROM chunk_embeddings_v1;').strip()
            assert restored=='4\n1024',restored
            compose('exec','-T','postgres','dropdb','-U','rag','model_switch_restore')
        compose('restart',profile)
        compose('up','-d','--wait',profile)
        compose('restart',service,mcp_service)
        wait_ready(base)
        after=[json.loads(line) for line in output('run','--rm','-T','--no-deps',service,'export').splitlines()]
        assert after==records,'Documents changed after restart'
        assert request(base+'/api/search',{'query':'vector search','limit':3})['results']
        assert rpc('get_document',{'document_id':records[0]['document_id']})==records[0]
    state['checks'].append({'phase':phase,'passed':True,'documents':len(records),'dimension':dimension,'model':model})
    state_path.write_text(json.dumps(state,indent=2)+'\n')
    print(profile,phase,'passed',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['postgres','qdrant','all'],default='all')
    parser.add_argument('--check',choices=['initial','bge','rollback'])
    args=parser.parse_args()
    if args.check:phase_check(args.check);return
    REPORT.mkdir(parents=True,exist_ok=True)
    readme=(ROOT/'docs/embedding-models.md').read_text()
    blocks={name:re.search(r'<!-- model-switch:'+name+r' -->\s*```bash\n(.*?)```',readme,re.S).group(1) for name in ['backup','download','configure','rebuild','rollback']}
    summaries=[]
    for profile in (['postgres','qdrant'] if args.profile=='all' else [args.profile]):
        env=os.environ.copy()
        for key in ['EMBEDDING_MODEL_ID','EMBEDDING_DIM','EMBEDDING_POOLING','EMBEDDING_QUERY_PREFIX','CHUNK_SIZE_RUNES','CHUNK_OVERLAP_RUNES','QDRANT_API_KEY','QDRANT_COLLECTION','COMPOSE_FILE']:
            env.pop(key,None)
        env['EMBEDDING_MODEL_FILE']=env.get('EMBEDDING_MODEL_FILE',str(ROOT / 'models/Qwen3-Embedding-0.6B-Q8_0.gguf'))
        env['PROFILE']=profile;env['COMPOSE_PROJECT_NAME']=f'myrag-switch-{profile}-{os.getpid()}'
        sockets=[]
        for key in ['POSTGRES_PORT','POSTGRES_APP_PORT','POSTGRES_MCP_PORT','QDRANT_PORT','QDRANT_APP_PORT','QDRANT_MCP_PORT']:
            s=socket.socket();s.bind(('127.0.0.1',0));sockets.append(s);env[key]=str(s.getsockname()[1])
        for s in sockets:s.close()
        check='python3 scripts/model_switch_smoke.py --check '
        script='set -euo pipefail\nmake up PROFILE="$PROFILE"\n'+check+'initial\n'
        script+='\n'.join(blocks[name] for name in ['backup','download','configure','rebuild'])
        script+='\nexport SWITCH_BACKUP_DIR PREVIOUS_QDRANT_COLLECTION\n'+check+'bge\n'+blocks['rollback']+'\n'+check+'rollback\n'
        (REPORT/(profile+'-readme-flow.sh')).write_text(script)
        try:
            with (REPORT/(profile+'.log')).open('w') as log:
                subprocess.run(['bash','-x',str(REPORT/(profile+'-readme-flow.sh'))],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
            summaries.append(json.loads((REPORT/(profile+'-state.json')).read_text()))
            (REPORT/(profile+'-failure.log')).unlink(missing_ok=True)
        except BaseException:
            with (REPORT/(profile+'-failure.log')).open('w') as log:
                subprocess.run(['docker','compose','--profile',profile,'logs','--tail','80'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            raise
        finally:
            subprocess.run(['docker','compose','--profile','postgres','--profile','qdrant','down','--volumes','--remove-orphans'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
        print(profile,'documented model-switch flow passed',flush=True)
    (REPORT/'results.json').write_text(json.dumps({'passed':True,'readme_sha256':hashlib.sha256(readme.encode()).hexdigest(),'profiles':summaries},indent=2)+'\n')


if __name__=='__main__':main()
