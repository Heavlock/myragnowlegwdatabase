#!/usr/bin/env python3
"""Exercise the same public UI, HTTP and MCP contracts on either backend."""
import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',required=True)
    parser.add_argument('--mcp-url',required=True)
    parser.add_argument('--backend',choices=['postgres','qdrant'],required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--verify-persistence',action='store_true')
    args=parser.parse_args()
    checks=[]
    def request(url,body=None,form=None,status=200):
        headers={};data=None
        if body is not None:data=json.dumps(body,ensure_ascii=False).encode();headers['Content-Type']='application/json'
        if form is not None:data=urllib.parse.urlencode(form).encode();headers['Content-Type']='application/x-www-form-urlencoded'
        try:
            with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=headers),timeout=90) as response:
                code,raw=response.status,response.read().decode()
        except urllib.error.HTTPError as error:code,raw=error.code,error.read().decode()
        assert code==status,(url,code,raw[:1500])
        return raw
    def post(path,body):return json.loads(request(args.base_url+path,body))
    def rpc(name,arguments):
        response=json.loads(request(args.mcp_url,{'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':name,'arguments':arguments}}))
        assert 'error' not in response,response
        return response['result']['structuredContent']
    def record(name):checks.append({'name':name,'passed':True});print(args.backend+': '+name,flush=True)
    if args.verify_persistence:
        state=json.loads(args.report.read_text())
        for item in state['documents']:
            actual=rpc('get_document',{'document_id':item['document_id']})
            assert actual['title']==item['title'] and actual['content']==item['content'],actual
            assert actual['metadata']==item['metadata'],actual
        state['checks'].append({'name':'Document content, IDs and metadata survive database and app restart','passed':True})
        state['passed']=True
        args.report.write_text(json.dumps(state,indent=2,ensure_ascii=False)+'\n')
        print(args.backend+': persistence after database and application restart passed',flush=True)
        return
    html=request(args.base_url+'/')
    assert 'Semantic search' in html and '<html lang="en">' in html and '</html>' in html
    assert 'name="language" value="en"' in html
    record('UI serves a complete page')
    invalid_forms=[
        ({'form_kind':'insert','metadata':'invalid'},'metadata must be a valid JSON object'),
        ({'form_kind':'insert','metadata':'{}','document_id':'bad'},'document_id must be an integer'),
        ({'form_kind':'search','limit':'bad'},'limit must be an integer'),
        ({'form_kind':'reindex','reindex_mode':'single','document_ids':''},'Enter a document ID'),
        ({'form_kind':'reindex','reindex_mode':'single','document_ids':'-1'},'document_ids must contain positive integers'),
        ({'form_kind':'reindex','reindex_mode':'single','document_ids':'1,2'},'Single mode requires exactly one document ID'),
        ({'form_kind':'reindex','reindex_mode':'invalid'},'Unknown reindex mode'),
        ({'form_kind':'invalid'},'Unknown form type'),
    ]
    for form,message in invalid_forms:
        raw=request(args.base_url+'/',form=form,status=400)
        assert message in raw,(form,raw[-1500:])
    record('UI validation messages and default document language are English')
    initialized=json.loads(request(args.mcp_url,{'jsonrpc':'2.0','id':1,'method':'initialize','params':{}}))
    assert initialized['result']['serverInfo']['name']=='myrag-mcp'
    record('MCP initializes')
    empty=post('/api/search',{'query':'empty repository','limit':3})
    assert not empty['results'],empty
    record('Fresh database supports empty search')
    data=[
      {'title':'Platform administrator','content':'Alice Morgan is the platform administrator. She manages employee access, user roles, and system permissions. Contact Alice for account authorization questions.'},
      {'title':'Database recovery policy','content':'Database backups run every night at 03:00 and are retained for fourteen days. A restore must be tested in an isolated environment before recovered records are applied to production.'},
      {'title':'Garden care','content':'Tomatoes grow in the greenhouse. Gardeners water the plants regularly and harvest ripe fruit during summer. Greenhouse ventilation prevents excess moisture.'},
      {'title':'Meeting room equipment','content':'The workplace desk supplies room displays and audio equipment. Report the room name and failed connection to request help during a meeting.'},
    ]
    for i,item in enumerate(data):
        item.update(source_uri=f'smoke:{args.backend}:{i}',source_type='manual',language='en',metadata={'test_backend':args.backend,'nested':{'n':7},'tags':['english','β']})
        if i==2:
            response=rpc('insert_document',item)
        elif i==3:
            raw=request(args.base_url+'/',form={'form_kind':'insert',**item,'metadata':json.dumps(item['metadata'])})
            assert 'Document saved' in raw
            # The UI prints the assigned document ID in its result block.
            import re
            match=re.search(r'<strong>document_id:</strong>\s*(\d+)',raw)
            assert match,raw[-1500:]
            response={'document_id':int(match.group(1)),'status':'created','chunks_created':1}
        else:response=post('/api/documents/upsert',item)
        assert response['status']=='created' and response['chunks_created']>0,response
        assert 0<response['document_id']<=2**53-1,response
        item['document_id']=response['document_id']
    record('Insertion works through HTTP, MCP and UI with exact JSON-safe numeric IDs')
    for query,index in [('Who manages user permissions?',0),('How long do we keep backup copies?',1),('How should tomatoes be watered?',2)]:
        result=post('/api/search',{'query':query,'limit':3})
        assert result['results'] and any(row['document_id']==data[index]['document_id'] for row in result['results']),result
        assert all(result['results'][i]['score']>=result['results'][i+1]['score'] for i in range(len(result['results'])-1)),result
    record('Real Qwen semantic search includes relevant documents in top three with sorted scores')
    found=rpc('get_document',{'document_id':data[0]['document_id']})
    assert found['content']==data[0]['content'] and found['metadata']==data[0]['metadata'],found
    hits=rpc('search_chunks',{'query':'Who manages user permissions?','limit':3})
    assert any(row['document_id']==data[0]['document_id'] for row in hits['results']),hits
    record('MCP reads full documents and searches the same stored data')
    old_text=data[0]['content']
    data[0].update(title='Office bicycle storage',content='Employees park bicycles in the secure courtyard rack. The workplace desk issues rack access and checks the bicycle registration sticker.',metadata={'revision':2,'tags':['changed']})
    updated=post('/api/documents/upsert',data[0])
    assert updated['status']=='reindexed' and updated['document_id']==data[0]['document_id'],updated
    all_hits=post('/api/search',{'query':'company policies','limit':20})['results']
    assert all(old_text not in h['chunk_text'] and h['title']!='Platform administrator' for h in all_hits),all_hits
    assert any(h['document_id']==data[0]['document_id'] and h['title']==data[0]['title'] for h in all_hits),all_hits
    record('Document replacement preserves its ID and removes previous chunks and metadata')
    single=post('/api/documents/reindex',{'document_ids':[data[0]['document_id']]})
    assert single['documents_reindexed']==1,single
    batch=post('/api/documents/reindex',{'document_ids':[data[0]['document_id'],data[1]['document_id'],data[1]['document_id']]})
    assert batch['documents_reindexed']==2,batch
    all_result=post('/api/documents/reindex',{'all':True})
    assert all_result['documents_reindexed']==4 and set(all_result['document_ids'])=={d['document_id'] for d in data},all_result
    record('Single, deduplicated batch and full reindex work')
    for item in data:
        actual=rpc('get_document',{'document_id':item['document_id']})
        assert actual['content']==item['content'] and actual['metadata']==item['metadata'],actual
    record('Full reindex preserves document bodies and metadata across HTTP and MCP')
    raw=request(args.base_url+'/',form={'form_kind':'search','query':'How long do we keep backup copies?','limit':2})
    assert 'Database recovery policy' in raw and 'class="error"' not in raw
    record('UI renders live semantic search results')
    for invalid in [{'query':''},{'query':'test','limit':21},{'query':'test','limit':-1}]:request(args.base_url+'/api/search',invalid,status=400)
    missing=json.loads(request(args.mcp_url,{'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'get_document','arguments':{'document_id':999999}}}))
    assert missing['error']['code']==-32000,missing
    record('Invalid requests and missing documents retain the public error contracts')
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps({'backend':args.backend,'passed':True,'checks':checks,'documents':data},indent=2,ensure_ascii=False)+'\n')


if __name__=='__main__':main()
