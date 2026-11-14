#!/usr/bin/env python3
"""Compare real Qwen CPU/CUDA inference using disposable PostgreSQL projects."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

from machine_info import inspect_machine
from test_model_prefixes import free_ports, inspect, request, wait_http

ROOT = Path(__file__).resolve().parent.parent
PREFIX = 'Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: '
MODEL = 'Qwen/Qwen3-Embedding-0.6B-GGUF:Q8_0'
MODEL_SHA = '06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439'
TEXTS = [
    'title: Backup retention | text: Database backups run every night and are retained for fourteen days.',
    'title: Access approval | text: Managers approve new employee accounts and changes to user permissions.',
    'title: Garden care | text: Water tomato plants regularly and ventilate the greenhouse in summer.',
]
QUERIES = ['How long are backup copies kept?', 'Who approves employee access?', 'How do I care for tomatoes?']


def output(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def working_state(project):
    containers = output('docker', 'ps', '-q', '--filter', 'label=com.docker.compose.project=' + project).split()
    state = {'containers': sorted(containers)}
    for cid in containers:
        if inspect(cid)['Config']['Labels'].get('com.docker.compose.service') == 'postgres':
            sql = "SELECT json_build_object('documents',(SELECT count(*) FROM documents),'chunks',(SELECT count(*) FROM chunks),'vectors',(SELECT count(*) FROM chunk_embeddings_v1),'document_digest',(SELECT md5(coalesce(string_agg(row_to_json(d)::text,'' ORDER BY id),'')) FROM documents d),'vector_digest',(SELECT md5(coalesce(string_agg(row_to_json(v)::text,'' ORDER BY chunk_id),'')) FROM chunk_embeddings_v1 v))"
            state['database'] = json.loads(output('docker', 'exec', cid, 'psql', '-U', 'rag', '-d', 'rag', '-Atqc', sql))
    return state


def cosine(a, b):
    return sum(x*y for x, y in zip(a, b)) / math.sqrt(sum(x*x for x in a) * sum(y*y for y in b))


def measure(url, inputs, repeats):
    def embed():
        result = request(url + '/v1/embeddings', {'model': MODEL, 'input': inputs})
        vectors = [row['embedding'] for row in sorted(result['data'], key=lambda row: row['index'])]
        assert len(vectors) == len(inputs)
        assert all(len(v) == 1024 and all(math.isfinite(x) for x in v) for v in vectors)
        assert all(sum(x*x for x in v) > 0 for v in vectors)
        return vectors, result.get('usage')
    embed()  # Warm the same request before recording elapsed HTTP time.
    seconds = []
    for _ in range(repeats):
        start = time.perf_counter()
        vectors, usage = embed()
        seconds.append(time.perf_counter() - start)
    return {'seconds': seconds, 'median_seconds': statistics.median(seconds),
            'inputs_per_request': len(inputs), 'usage': usage}, vectors


def test_mode(mode, directory, model_file):
    project = 'myrag-compute-' + mode + '-' + str(os.getpid())
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('COMPOSE_', 'POSTGRES_', 'QDRANT_', 'EMBEDDING_', 'CHUNK_')):
            env.pop(key)
    ports = free_ports(6)
    settings = dict(zip(['POSTGRES_PORT', 'POSTGRES_APP_PORT', 'POSTGRES_MCP_PORT',
                         'QDRANT_PORT', 'QDRANT_APP_PORT', 'QDRANT_MCP_PORT'], map(str, ports)))
    settings.update(EMBEDDING_MODEL_FILE=str(model_file), EMBEDDING_MODEL_ID=MODEL,
                    EMBEDDING_DIM='1024', EMBEDDING_POOLING='last', EMBEDDING_QUERY_PREFIX=PREFIX,
                    CHUNK_SIZE_RUNES='1200', CHUNK_OVERLAP_RUNES='200',
                    EMBEDDING_GPU_ID=os.environ.get('EMBEDDING_GPU_ID', '0'))
    envfile = directory / (mode + '.env')
    envfile.write_text(''.join(key + '=' + json.dumps(value) + '\n' for key, value in settings.items()))
    # Same bounded context and batch parameters in both backends.
    overrides = directory / (mode + '-test.json')
    overrides.write_text(json.dumps({'services': {'embeddings': {'environment': {
        'LLAMA_ARG_CTX_SIZE': '4096', 'LLAMA_ARG_BATCH': '2048', 'LLAMA_ARG_UBATCH': '512',
    }}}}))
    command = ['docker', 'compose', '--progress', 'plain', '-f', str(ROOT / 'docker-compose.yml')]
    if mode == 'gpu':
        command += ['-f', str(ROOT / 'docker-compose.gpu.yml')]
    command += ['-f', str(overrides), '--env-file', str(envfile), '-p', project, '--profile', 'postgres']
    log = (directory / (mode + '-compose.log')).open('w')

    def compose(*args, check=True):
        return subprocess.run(command + list(args), env=env, stdout=log, stderr=subprocess.STDOUT, check=check)

    def cid(service):
        return output(*(command + ['ps', '-q', service]), env=env)

    report = {'mode': mode, 'project': project, 'passed': False}
    try:
        print(mode + ': starting disposable PostgreSQL stack', flush=True)
        compose('up', '-d', '--build', '--wait', '--wait-timeout', '180')
        embed_id = cid('embeddings')
        container = inspect(embed_id)
        device_requests = container['HostConfig'].get('DeviceRequests') or []
        if mode == 'gpu':
            assert any(d.get('Driver') == 'cdi' and any(v.startswith('nvidia.com/gpu=') for v in d.get('DeviceIDs', [])) for d in device_requests)
        else:
            assert not device_requests, device_requests
        for service in ['app', 'mcp']:
            actual = dict(value.split('=', 1) for value in inspect(cid(service))['Config']['Env'] if '=' in value)
            assert actual['EMBEDDING_QUERY_PREFIX'] == PREFIX
            assert actual['EMBEDDING_MODEL_ID'] == MODEL and actual['EMBEDDING_DIM'] == '1024'
        base = 'http://127.0.0.1:' + str(ports[1])
        mcp = 'http://127.0.0.1:' + str(ports[2]) + '/mcp'
        wait_http(base + '/')
        smoke_report = directory / (mode + '-profile.json')
        smoke = [sys.executable, str(ROOT / 'scripts/profile_smoke.py'), '--base-url', base,
                 '--mcp-url', mcp, '--backend', 'postgres', '--report', str(smoke_report)]
        subprocess.run(smoke, check=True, stdout=log, stderr=subprocess.STDOUT)
        compose('restart', 'postgres')
        compose('up', '-d', '--wait', 'postgres')
        compose('restart', 'app', 'mcp')
        wait_http(base + '/')
        subprocess.run(smoke + ['--verify-persistence'], check=True, stdout=log, stderr=subprocess.STDOUT)
        print(mode + ': UI, HTTP, MCP, document replacement, reindex and persistence passed', flush=True)
        address = next(iter(container['NetworkSettings']['Networks'].values()))['IPAddress']
        url = 'http://' + address + ':8080'
        inputs = TEXTS + [PREFIX + query for query in QUERIES]
        reference = request(url + '/v1/embeddings', {'model': MODEL, 'input': inputs})
        vectors = [row['embedding'] for row in sorted(reference['data'], key=lambda row: row['index'])]
        assert len(vectors) == len(inputs)
        assert all(len(v) == 1024 and all(math.isfinite(x) for x in v) for v in vectors)
        query_timing, _ = measure(url, [PREFIX + QUERIES[0]], 7)
        batch_timing, _ = measure(url, TEXTS * 8, 5)
        rankings = [sorted(range(len(TEXTS)), key=lambda i: cosine(query, vectors[i]), reverse=True)
                    for query in vectors[len(TEXTS):]]
        assert [r[0] for r in rankings] == [0, 1, 2], rankings
        logs = output('docker', 'logs', embed_id, stderr=subprocess.STDOUT)
        (directory / (mode + '-embeddings.log')).write_text(logs)
        offloaded = [int(n) for n in re.findall(r'offloaded\s+(\d+)/(?:\d+)\s+layers', logs)]
        if mode == 'gpu':
            assert offloaded and max(offloaded) > 0, 'No actual layer offloading found in GPU logs'
            assert re.search(r'CUDA\d|CUDA device', logs), 'No CUDA device found in GPU logs'
        else:
            assert not offloaded or max(offloaded) == 0
        image = json.loads(output('docker', 'image', 'inspect', container['Image']))[0]
        report.update(passed=True, image=container['Config']['Image'], image_id=container['Image'],
                      image_revision=(image['Config'].get('Labels') or {}).get('org.opencontainers.image.revision'),
                      offloaded_layers=max(offloaded, default=0), device_requests=device_requests,
                      query_timing=query_timing, batch_24_timing=batch_timing, rankings=rankings,
                      vectors=vectors, profile_checks=json.loads(smoke_report.read_text())['checks'])
        if mode == 'gpu':
            # Query GPU-indexed documents after switching the same stack to CPU,
            # then switch back. No reindex or document write is involved.
            cpu_command = command.copy()
            gpu_file_index = cpu_command.index(str(ROOT / 'docker-compose.gpu.yml'))
            del cpu_command[gpu_file_index - 1:gpu_file_index + 1]
            query = {'query': 'How long do we keep backup copies?', 'limit': 3}
            original_hits = request(base + '/api/search', query)['results']
            before_switch = working_state(project)['database']
            subprocess.run(cpu_command + ['up', '-d', '--no-deps', '--wait', 'embeddings'],
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            assert not inspect(cid('embeddings'))['HostConfig'].get('DeviceRequests')
            cpu_hits = request(base + '/api/search', query)['results']
            compose('up', '-d', '--no-deps', '--wait', 'embeddings')
            gpu_hits = request(base + '/api/search', query)['results']
            assert [h['document_id'] for h in original_hits] == [h['document_id'] for h in cpu_hits] == [h['document_id'] for h in gpu_hits]
            assert any(h['title'] == 'Database recovery policy' for h in gpu_hits)
            assert working_state(project)['database'] == before_switch
            report['device_switch_preserves_index_and_retrieval'] = True
            print('gpu: GPU -> CPU -> GPU kept the same stored index and search rankings', flush=True)
        print(mode + ': query median %.4fs; batch of 24 median %.4fs; offloaded layers %d' %
              (query_timing['median_seconds'], batch_timing['median_seconds'], report['offloaded_layers']), flush=True)
        return report
    finally:
        compose('logs', '--tail', '100', check=False)
        compose('down', '--volumes', '--remove-orphans', '--rmi', 'local')
        log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modes', nargs='+', choices=['cpu', 'gpu'], default=['cpu', 'gpu'])
    args = parser.parse_args()
    config = json.loads(output('docker', 'compose', '--profile', 'postgres', 'config', '--format', 'json', cwd=ROOT))
    model = Path(config['services']['embeddings']['volumes'][0]['source'])
    with model.open('rb') as source:
        assert hashlib.file_digest(source, 'sha256').hexdigest() == MODEL_SHA, 'The compute test requires the pinned default Qwen Q8_0 artifact'
    hardware = inspect_machine()
    if 'gpu' in args.modes and not hardware['cuda_container_ready']:
        parser.error('CUDA tests require a working NVIDIA driver, NVIDIA CDI devices and CDI-enabled Docker; run make hardware.')
    directory = ROOT / 'reports/compute' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    directory.mkdir(parents=True)
    before = working_state(config['name'])
    report = {'passed': False, 'hardware': hardware, 'model_sha256': MODEL_SHA,
              'context_size': 4096, 'batch_size': 2048, 'ubatch_size': 512,
              'working_state_before': before, 'modes': {},
              'timing_scope': 'Warm repeated HTTP requests; one query or 24 short document chunks. Excludes startup, downloads and indexing. Other host workloads are not stopped.'}
    try:
        for mode in args.modes:
            report['modes'][mode] = test_mode(mode, directory, model)
        if {'cpu', 'gpu'} <= report['modes'].keys():
            cpu, gpu = report['modes']['cpu'], report['modes']['gpu']
            # A comparison should use the same runtime source revision.
            assert cpu['image_revision'] and cpu['image_revision'] == gpu['image_revision'], 'CPU/GPU llama.cpp revisions differ; refresh both images or use matching pinned versions'
            similarities = [cosine(a, b) for a, b in zip(cpu['vectors'], gpu['vectors'])]
            assert min(similarities) >= .999, similarities
            assert cpu['rankings'] == gpu['rankings']
            report['comparison'] = {
                'minimum_vector_cosine': min(similarities),
                'maximum_component_difference': max(abs(x-y) for a, b in zip(cpu['vectors'], gpu['vectors']) for x, y in zip(a, b)),
                'rankings_identical': True,
                'query_speedup': cpu['query_timing']['median_seconds'] / gpu['query_timing']['median_seconds'],
                'batch_24_speedup': cpu['batch_24_timing']['median_seconds'] / gpu['batch_24_timing']['median_seconds'],
            }
        after = working_state(config['name'])
        report['working_state_after'] = after
        assert before == after, 'Working containers or stored data changed during the isolated test'
        report['passed'] = True
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        for mode in report['modes'].values():
            mode.pop('vectors', None)
        (directory / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
        print('Report: ' + str(directory / 'results.json'), flush=True)
    print(json.dumps(report.get('comparison', {}), indent=2))


if __name__ == '__main__':
    main()
