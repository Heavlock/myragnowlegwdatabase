#!/usr/bin/env python3
"""Check local knowledge contracts against disposable PostgreSQL/Qdrant projects."""
import argparse
import copy
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'reports/skills'
CLIENT = ROOT / 'scripts/myrag_client.py'


def check_profile(profile):
    env = os.environ.copy()
    env['COMPOSE_PROJECT_NAME'] = f'myrag-skills-{profile}-{os.getpid()}'
    env['PROFILE'] = profile
    for key in ['MYRAG_MCP_URL', 'EMBEDDING_MODEL_ID', 'EMBEDDING_DIM', 'EMBEDDING_POOLING', 'EMBEDDING_QUERY_PREFIX', 'CHUNK_SIZE_RUNES', 'CHUNK_OVERLAP_RUNES', 'QDRANT_COLLECTION', 'QDRANT_API_KEY', 'COMPOSE_FILE']:
        env.pop(key, None)
    env['EMBEDDING_MODEL_FILE'] = env.get('SKILLS_TEST_MODEL_FILE', str(ROOT / 'models/Qwen3-Embedding-0.6B-Q8_0.gguf'))
    sockets = []
    for key in ['POSTGRES_PORT', 'POSTGRES_APP_PORT', 'POSTGRES_MCP_PORT', 'QDRANT_PORT', 'QDRANT_APP_PORT', 'QDRANT_MCP_PORT']:
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        sockets.append(sock)
        env[key] = str(sock.getsockname()[1])
    for sock in sockets:
        sock.close()
    checks = []
    with (OUT / (profile + '.log')).open('w') as log:
        def call(operation, *arguments, body=None, expected=0, prefix=None):
            command = [sys.executable, str(CLIENT), *(prefix or ['--profile', profile]), operation, *map(str, arguments)]
            result = subprocess.run(command, cwd=ROOT, env=env, input=None if body is None else json.dumps(body), text=True, capture_output=True)
            log.write(json.dumps({'command': command, 'exit_code': result.returncode}) + '\n')
            log.write(result.stdout + result.stderr)
            log.flush()
            assert result.returncode == expected, result.stderr
            return json.loads(result.stdout if expected == 0 else result.stderr)

        def record(name):
            checks.append({'name': name, 'passed': True})
            print(profile + ': ' + name, flush=True)

        try:
            subprocess.run(['make', 'up', 'PROFILE=' + profile], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            port = env['POSTGRES_MCP_PORT' if profile == 'postgres' else 'QDRANT_MCP_PORT']
            for _ in range(60):
                try:
                    request = urllib.request.Request(f'http://127.0.0.1:{port}/mcp', data=b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}', headers={'Content-Type':'application/json'})
                    with urllib.request.urlopen(request, timeout=3) as response:
                        assert json.load(response)['result']['serverInfo']['name'] == 'myrag-mcp'
                    break
                except (OSError, ValueError, KeyError, AssertionError):
                    time.sleep(1)
            else:
                raise RuntimeError('MCP endpoint did not become ready.')
            record('Installation path starts the selected profile and real embedding model')
            first = call('search', '--query', 'backup retention', '--limit', 5)
            assert not first['result']['results']
            record('Search on an empty store succeeds without creating documents')
            original = {'title': 'Backup retention policy', 'content': 'Database backups run every night. Backup copies are retained for fourteen days.', 'source_uri': 'contract:backup-policy', 'source_type': 'internal_doc', 'metadata': {'project': 'contract-test', 'owner': {'team': 'platform', 'location': 'remote'}, 'tags': ['operations', 'β']}}
            saved = call('save', '--input', '-', body=original)
            identifier = saved['result']['document_id']
            assert saved['verified'] and saved['result']['status'] == 'created' and 0 < identifier <= 2**53 - 1
            stored = saved['document']
            assert stored['language'] == 'en' and stored['metadata'] == original['metadata'] and stored['source_uri'] == original['source_uri']
            assert saved['profile'] == profile and saved['endpoint'].endswith('/mcp')
            record('Save creates a new document, supplies English language, and verifies full read-back')
            read = call('get', '--document-id', identifier)
            assert read['document'] == stored
            found = call('search', '--query', 'How long are backup copies retained?', '--limit', 5)
            assert any(row['document_id'] == identifier for row in found['result']['results'])
            record('Semantic search and full-source retrieval return the saved document')
            revised = original['content'].replace('fourteen', 'twenty-one')
            changed = call('update', '--document-id', identifier, '--input', '-', body={'content': revised, 'metadata': {'owner': {'contact': 'operations@example.com'}}})
            expected_metadata = copy.deepcopy(original['metadata'])
            expected_metadata['owner']['contact'] = 'operations@example.com'
            assert changed['verified'] and changed['result']['status'] == 'reindexed' and changed['result']['document_id'] == identifier
            assert changed['document']['metadata'] == expected_metadata and changed['document']['content'] == revised
            for field in ['title', 'source_uri', 'source_type', 'language']:
                assert changed['document'][field] == stored[field]
            record('Update retains identity/source fields and recursively preserves unrequested metadata')
            renamed = call('update', '--document-id', identifier, '--input', '-', body={'title': 'Current backup policy', 'metadata': {}})
            assert renamed['document']['content'] == revised and renamed['document']['metadata'] == expected_metadata
            record('A title-only edit and empty merge preserve the complete source and metadata')
            cleared = call('update', '--document-id', identifier, '--input', '-', '--replace-metadata', body={'metadata': {}})
            assert cleared['document']['metadata'] == {} and cleared['document']['content'] == revised
            record('Explicit metadata replacement can clear metadata without replacing content')
            bad_save = call('save', '--input', '-', body={'document_id': identifier, **original}, expected=1)
            assert 'use update' in bad_save['error']
            missing = call('update', '--document-id', 2**53-1, '--input', '-', body={'content': 'must not create a document'}, expected=1)
            assert 'not found' in missing['error']
            bad_patch = call('update', '--document-id', identifier, '--input', '-', body={'document_id': identifier, 'content': 'must not write'}, expected=1)
            assert 'Unknown fields' in bad_patch['error']
            empty = call('update', '--document-id', identifier, '--input', '-', body={}, expected=1)
            assert 'empty' in empty['error']
            record('Save-with-ID, missing updates, ID-bearing patches, and empty patches fail safely')
            endpoint = cleared['endpoint']
            override = call('get', '--document-id', identifier, prefix=['--url', endpoint])
            assert override['profile'] == 'custom' and override['document'] == cleared['document']
            record('Explicit endpoint override works and reports custom store identity')
            final = call('get', '--document-id', identifier)
            assert final['document'] == cleared['document']
            service = 'app' if profile == 'postgres' else 'app-qdrant'
            export = subprocess.check_output(['docker', 'compose', '--profile', profile, 'run', '--rm', '-T', '--no-deps', service, 'export'], cwd=ROOT, env=env, text=True, stderr=log)
            documents = [json.loads(line) for line in export.splitlines()]
            assert documents == [cleared['document']]
            record('Read/search/rejected operations leave exactly one correct stored document')
        finally:
            subprocess.run(['docker', 'compose', '--profile', 'postgres', '--profile', 'qdrant', 'down', '--volumes', '--remove-orphans', '--rmi', 'local'], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    return {'profile': profile, 'passed': True, 'checks': checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=['postgres', 'qdrant', 'all'], default='all')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    states = []
    (OUT / 'results.json').write_text(json.dumps({'passed': False, 'status': 'running'}, indent=2) + '\n')
    for profile in (['postgres', 'qdrant'] if args.profile == 'all' else [args.profile]):
        states.append(check_profile(profile))
    (OUT / 'results.json').write_text(json.dumps({'passed': True, 'profiles': states, 'scope': 'Actual MCP save/update/search/get calls in disposable projects; no live knowledge-base writes.'}, indent=2) + '\n')


if __name__ == '__main__':
    main()
