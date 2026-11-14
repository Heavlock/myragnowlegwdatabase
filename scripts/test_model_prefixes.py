#!/usr/bin/env python3
"""Exercise model-specific prefixes through real HTTP/MCP services in disposable stacks."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
SERVICES = ['app', 'mcp', 'app-qdrant', 'mcp-qdrant']
PREFIXES = {
    'qwen-q8': 'Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: ',
    'bge-small-q8': 'Represent this sentence for searching relevant passages: ',
    'minilm-q8': '',
}
MODEL_IDS = {
    'qwen-q8': 'Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0',
    'bge-small-q8': 'BAAI/bge-small-en-v1.5:Q8_0',
    'minilm-q8': 'sentence-transformers/all-MiniLM-L6-v2:Q8_0',
}
DOCUMENTS = [
    ('backup', 'Backup retention', 'Database backup copies are retained for thirty days. Restore a backup into a temporary database before recovering production records.'),
    ('access', 'Employee access approval', 'A new employee must obtain manager approval before an account is activated. People Operations also confirms the employment start date.'),
    ('security', 'Exposed API key response', 'If an API key is exposed, revoke the compromised key immediately. Generate a replacement credential and update the affected service.'),
    ('tls', 'Encrypted web connections', 'HTTPS uses the TLS protocol to encrypt web traffic between a browser and a server. Certificates authenticate the server identity.'),
    ('migrations', 'Database schema migrations', 'Database schema changes are applied through versioned SQL migrations. Review the migration and test it on a disposable database before applying it.'),
    ('office', 'Office opening hours', 'The office reception opens at nine in the morning and closes at six in the evening on weekdays. Visitors sign in at the front desk.'),
]
QUESTIONS = [
    ('backup', 'How many days are backup copies retained?'),
    ('access', 'Who must approve access for a new employee?'),
    ('security', 'What should I do if an API key is exposed?'),
    ('tls', 'Which protocol encrypts web traffic?'),
    ('migrations', 'How are database schema changes applied?'),
]
SCORE_TOLERANCE = 1e-5


def run(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def inspect(container):
    return json.loads(run('docker', 'inspect', container))[0]


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def request(url, body=None, expected=200):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    assert status == expected, (url, status, raw[:500])
    return json.loads(raw) if body is not None and status == 200 else raw


def rpc(url, name, arguments):
    result = request(url, {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                           'params': {'name': name, 'arguments': arguments}})
    assert 'error' not in result and not result['result'].get('isError'), result
    return result['result']['structuredContent']


def wait_http(url):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            request(url)
            return
        except (OSError, AssertionError):
            time.sleep(.5)
    raise RuntimeError('Service did not become ready: ' + url)


def protected_state():
    names = run('docker', 'ps', '-q', '--filter', 'label=com.docker.compose.project=myragnowlegwdatabase').split()
    state = {'containers': sorted(names)}
    for cid in names:
        container = inspect(cid)
        if container['Config']['Labels'].get('com.docker.compose.service') == 'postgres':
            sql = "select json_build_object('documents',(select count(*) from documents),'chunks',(select count(*) from chunks),'vectors',(select count(*) from chunk_embeddings_v1),'documents_digest',(select md5(coalesce(string_agg(row_to_json(d)::text,'' order by id),'')) from documents d),'vectors_digest',(select md5(coalesce(string_agg(row_to_json(v)::text,'' order by chunk_id),'')) from chunk_embeddings_v1 v));"
            state['database'] = json.loads(run('docker', 'exec', cid, 'psql', '-U', 'rag', '-d', 'rag', '-Atqc', sql))
    return state


class Recorder(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, upstream, path, dimension):
        self.upstream, self.path, self.dimension = upstream, path, dimension
        self.records, self.errors, self.lock = [], [], threading.Lock()
        super().__init__(address, RecordingHandler)


class RecordingHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        try:
            with urllib.request.urlopen(self.server.upstream + self.path, timeout=30) as response:
                raw, status = response.read(), response.status
        except Exception as error:
            raw, status = str(error).encode(), 503
        self.send_response(status)
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        try:
            raw = self.rfile.read(int(self.headers['Content-Length']))
            body = json.loads(raw)
            assert self.path == '/v1/embeddings', self.path
            req = urllib.request.Request(self.server.upstream + self.path, data=raw,
                                         headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=60) as response:
                output, status = response.read(), response.status
            parsed = json.loads(output)
            vectors = [item['embedding'] for item in parsed['data']]
            assert len(vectors) == len(body['input'])
            assert all(len(v) == self.server.dimension and all(math.isfinite(x) for x in v) for v in vectors)
            record = {'input': body['input'], 'model': body.get('model'),
                      'dimensions': [len(v) for v in vectors],
                      'vector_sha256': hashlib.sha256(json.dumps(vectors).encode()).hexdigest()}
            with self.server.lock:
                self.server.records.append(record)
                with self.server.path.open('a') as capture:
                    capture.write(json.dumps(record) + '\n')
        except Exception as error:
            with self.server.lock:
                self.server.errors.append(str(error))
            output, status = str(error).encode(), 502
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(output)


def free_ports(count):
    sockets = [socket.socket() for _ in range(count)]
    try:
        for listener in sockets:
            listener.bind(('127.0.0.1', 0))
        return [s.getsockname()[1] for s in sockets]
    finally:
        for listener in sockets:
            listener.close()


def same_results(actual, expected):
    assert [r['source_uri'] for r in actual] == [r['source_uri'] for r in expected], (actual, expected)
    delta = max(abs(a['score'] - b['score']) for a, b in zip(actual, expected))
    assert delta <= SCORE_TOLERANCE, delta
    return delta


def test_model(model, output, image, bridge, token):
    mid = model['id']
    directory = output / mid
    directory.mkdir()
    project = 'myrag-prefix-' + token + '-' + mid
    assert project.startswith('myrag-prefix-')
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('EMBEDDING_', 'POSTGRES_', 'QDRANT_', 'CHUNK_', 'COMPOSE_')):
            env.pop(key)
    ports = free_ports(6)
    settings = dict(zip(['POSTGRES_PORT', 'POSTGRES_APP_PORT', 'POSTGRES_MCP_PORT',
                         'QDRANT_PORT', 'QDRANT_APP_PORT', 'QDRANT_MCP_PORT'], map(str, ports)))
    settings.update(EMBEDDING_MODEL_FILE=model['model_file'], EMBEDDING_MODEL_ID=MODEL_IDS[mid],
                    EMBEDDING_DIM=str(model['dim']), EMBEDDING_POOLING=model.get('pooling', 'last'),
                    EMBEDDING_QUERY_PREFIX=PREFIXES[mid], CHUNK_SIZE_RUNES='500', CHUNK_OVERLAP_RUNES='0')
    envfile = directory / 'configuration.env'

    def write_env():
        envfile.write_text(''.join(k + '=' + json.dumps(v) + '\n' for k, v in settings.items()))

    write_env()
    override = directory / 'compose.override.json'
    override.write_text(json.dumps({'services': {s: {'image': image} for s in SERVICES}}, indent=2))
    command = ['docker', 'compose', '-f', str(ROOT / 'docker-compose.yml'), '-f', str(override),
               '--env-file', str(envfile), '-p', project, '--profile', 'postgres', '--profile', 'qdrant']
    log = (directory / 'compose.log').open('w')

    def compose(*args, body=None, check=True):
        return subprocess.run(command + list(args), env=env, text=True, input=body,
                              stdout=log, stderr=subprocess.STDOUT, check=check)

    def cid(service):
        return subprocess.check_output(command + ['ps', '-q', service], env=env, text=True).strip()

    recorder = None
    report = {'model': mid, 'prefix': PREFIXES[mid], 'dimension': model['dim'], 'pooling': settings['EMBEDDING_POOLING'], 'profiles': {}, 'passed': False}
    try:
        compose('up', '-d', '--no-build', '--wait', 'postgres', 'qdrant', 'embeddings')
        if mid != 'qwen-q8':
            compose('exec', '-T', 'postgres', 'psql', '-U', 'rag', '-d', 'rag',
                    '-v', 'ON_ERROR_STOP=1', '-v', 'model_id=' + MODEL_IDS[mid], '-v', 'embedding_dim=' + str(model['dim']),
                    body=(ROOT / 'deployments/postgres/switch_embedding_model.sql').read_text())
        embedding = inspect(cid('embeddings'))
        ip = next(iter(embedding['NetworkSettings']['Networks'].values()))['IPAddress']
        recorder = Recorder((bridge, 0), 'http://' + ip + ':8080', directory / 'embedding-inputs.jsonl', model['dim'])
        threading.Thread(target=recorder.serve_forever, daemon=True).start()
        proxy = 'http://' + bridge + ':' + str(recorder.server_port)
        override.write_text(json.dumps({'services': {s: {'image': image, 'environment': {'EMBEDDINGS_BASE_URL': proxy}} for s in SERVICES}}, indent=2))
        compose('up', '-d', '--no-build', '--no-deps', *SERVICES)
        targets = {'postgres': ('app', 'mcp', ports[1], ports[2]), 'qdrant': ('app-qdrant', 'mcp-qdrant', ports[4], ports[5])}
        references = {}
        for backend, (app, mcp, app_port, mcp_port) in targets.items():
            base, endpoint = f'http://127.0.0.1:{app_port}', f'http://127.0.0.1:{mcp_port}/mcp'
            wait_http(base + '/')
            for service in [app, mcp]:
                values = dict(x.split('=', 1) for x in inspect(cid(service))['Config']['Env'] if '=' in x)
                assert values['EMBEDDING_QUERY_PREFIX'] == PREFIXES[mid]
            for i, (key, title, content) in enumerate(DOCUMENTS):
                body = {'title': title, 'content': content, 'source_uri': 'prefix-test://' + key,
                        'language': 'en', 'metadata': {'test': 'model-prefix', 'model': mid}}
                first = len(recorder.records)
                result = request(base + '/api/documents/upsert', body) if i % 2 == 0 else rpc(endpoint, 'insert_document', body)
                assert result['chunks_created'] == 1
                assert [r['input'] for r in recorder.records[first:]] == [['title: ' + title + ' | text: ' + content]]
                actual = rpc(endpoint, 'get_document', {'document_id': result['document_id']})
                assert actual['content'] == content and actual['metadata'] == body['metadata']
            rows, max_delta = [], 0.0
            for key, question in QUESTIONS:
                baseline = None
                for repetition in range(4):
                    query = (' \t' + question + '\t ') if repetition >= 2 else question
                    first = len(recorder.records)
                    result = request(base + '/api/search', {'query': query, 'limit': 3}) if repetition % 2 == 0 else rpc(endpoint, 'search_chunks', {'query': query, 'limit': 3})
                    assert [r['input'] for r in recorder.records[first:]] == [[PREFIXES[mid] + question]], (mid, backend, recorder.records[first:])
                    hits = result['results']
                    assert len(hits) == 3 and hits[0]['source_uri'] == 'prefix-test://' + key, (mid, backend, key, hits)
                    assert all(math.isfinite(h['score']) for h in hits)
                    assert all(a['score'] >= b['score'] for a, b in zip(hits, hits[1:]))
                    if baseline is None:
                        baseline = hits
                    else:
                        max_delta = max(max_delta, same_results(hits, baseline))
                references[(backend, question)] = baseline
                rows.append({'query': question, 'expected_source': 'prefix-test://' + key, 'results': baseline, 'repeats': 4})
            first = len(recorder.records)
            request(base + '/api/search', {'query': ' \t ', 'limit': 3}, expected=400)
            invalid = request(endpoint, {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                                         'params': {'name': 'search_chunks', 'arguments': {'query': ' \t ', 'limit': 3}}})
            assert 'error' in invalid or invalid.get('result', {}).get('isError')
            assert len(recorder.records) == first, 'Invalid query reached the embedding model'
            report['profiles'][backend] = {'correct_first_results': len(rows), 'questions': rows, 'maximum_repeat_score_delta': max_delta, 'invalid_queries_rejected_without_embedding': True}
        cross_delta = max(same_results(references[('postgres', q)], references[('qdrant', q)]) for _, q in QUESTIONS)
        report['cross_backend_maximum_score_delta'] = cross_delta
        compose('restart', 'embeddings')
        wait_http(proxy + '/health')
        compose('restart', *SERVICES)
        restart_delta = 0.0
        for backend, (_, _, app_port, mcp_port) in targets.items():
            wait_http(f'http://127.0.0.1:{app_port}/')
            for _, question in QUESTIONS:
                result = rpc(f'http://127.0.0.1:{mcp_port}/mcp', 'search_chunks', {'query': question, 'limit': 3})
                restart_delta = max(restart_delta, same_results(result['results'], references[(backend, question)]))
        report['maximum_score_delta_after_model_and_app_restart'] = restart_delta
        if mid == 'qwen-q8':
            settings.pop('EMBEDDING_QUERY_PREFIX')
            write_env()
            compose('up', '-d', '--no-build', '--no-deps', '--force-recreate', *SERVICES)
            for backend, (app, mcp, app_port, mcp_port) in targets.items():
                wait_http(f'http://127.0.0.1:{app_port}/')
                for service in [app, mcp]:
                    assert not any(x.startswith('EMBEDDING_QUERY_PREFIX=') for x in inspect(cid(service))['Config']['Env'])
                for _, question in QUESTIONS:
                    first = len(recorder.records)
                    result = rpc(f'http://127.0.0.1:{mcp_port}/mcp', 'search_chunks', {'query': question, 'limit': 3})
                    assert recorder.records[first]['input'] == [PREFIXES[mid] + question]
                    same_results(result['results'], references[(backend, question)])
            report['unset_prefix_matches_explicit_qwen_setting'] = True
        assert not recorder.errors, recorder.errors
        allowed = {PREFIXES[mid] + q for _, q in QUESTIONS} | {'title: ' + title + ' | text: ' + body for _, title, body in DOCUMENTS}
        assert all(r['model'] == MODEL_IDS[mid] and all(value in allowed for value in r['input']) for r in recorder.records)
        report.update(passed=True, embedding_requests=len(recorder.records), model_sha256=model['sha256'], runtime_image=embedding['Image'], score_tolerance=SCORE_TOLERANCE)
    finally:
        compose('logs', '--no-color', check=False)
        compose('down', '--volumes', '--remove-orphans', check=False)
        if recorder:
            recorder.shutdown()
            recorder.server_close()
        log.close()
        report['cleanup_complete'] = not run('docker', 'ps', '-aq', '--filter', 'label=com.docker.compose.project=' + project)
        (directory / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    assert report['cleanup_complete']
    print(mid + ': both profiles passed exact-prefix, relevance, repeat, whitespace, restart and channel-parity checks.', flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    models = json.loads((ROOT / 'benchmarks/scifact.json').read_text())['models']
    for model in models:
        model['model_file'] = str((ROOT / model['model_file']).resolve())
    for model in models:
        assert digest(Path(model['model_file'])) == model['sha256'], model['id']
        # Use the published model-guide shell settings as the configurations under test.
        key = {'qwen-q8': 'qwen', 'bge-small-q8': 'bge', 'minilm-q8': 'minilm'}[model['id']]
        block = re.search(r'<!-- query-prefix:' + key + r' -->\s*```bash\n(.*?)```', (ROOT / 'docs/embedding-models.md').read_text(), re.S).group(1)
        actual = subprocess.check_output(['bash', '-c', block + '\npython3 -c \'import os,json; print(json.dumps(os.environ["EMBEDDING_QUERY_PREFIX"]))\''], text=True)
        assert json.loads(actual) == PREFIXES[model['id']]
    before = protected_state()
    token = str(os.getpid())
    image = 'myrag-prefix-test:' + token
    bridge = json.loads(run('docker', 'network', 'inspect', 'bridge'))[0]['IPAM']['Config'][0]['Gateway']
    report = {'passed': False, 'scope': 'Real application HTTP/MCP, six short synthetic documents and five questions per model/backend. This is functional/repeatability verification, not a retrieval benchmark.', 'models': []}
    try:
        with (output / 'build.log').open('w') as log:
            subprocess.run(['docker', 'build', '-t', image, str(ROOT)], stdout=log, stderr=subprocess.STDOUT, check=True)
        for model in models:
            report['models'].append(test_model(model, output, image, bridge, token))
        assert protected_state() == before, 'The working stack changed during the test'
        report.update(passed=True, working_stack_unchanged=True)
    finally:
        subprocess.run(['docker', 'image', 'rm', image], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        (output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print('All models passed; working containers and document/vector checksums are unchanged.', flush=True)


if __name__ == '__main__':
    main()
