"""Resumable embedding of prepared project chunks through llama.cpp's HTTP API."""
import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np


def embed(base_url, texts):
    request = urllib.request.Request(
        base_url.rstrip('/') + '/v1/embeddings',
        data=json.dumps({'input': texts, 'encoding_format': 'float'}).encode(),
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = json.load(response)
    items = sorted(payload['data'], key=lambda item: item['index'])
    if len(items) != len(texts):
        raise ValueError(f'Expected {len(texts)} vectors, got {len(items)}')
    vectors = np.asarray([item['embedding'] for item in items], dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if not np.isfinite(vectors).all() or (norms == 0).any():
        raise ValueError('Non-finite or zero embedding')
    return vectors / norms, payload.get('usage', {})


def encode(base_url, texts, destination, batch_size=32):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    signature = hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode()).hexdigest()
    manifest = destination / 'manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text())['input_sha256'] != signature:
            raise ValueError(f'Cached inputs changed: {destination}')
    else:
        manifest.write_text(json.dumps({'input_sha256': signature, 'count': len(texts)}))
    batches, records = [], []
    started = time.monotonic()
    for first in range(0, len(texts), batch_size):
        data_path = destination / f'{first:06d}.npy'
        metadata_path = data_path.with_suffix('.json')
        if data_path.exists() and metadata_path.exists():
            vectors = np.load(data_path)
            metadata = json.loads(metadata_path.read_text())
        else:
            tick = time.monotonic()
            vectors, usage = embed(base_url, texts[first:first+batch_size])
            metadata = {'seconds': time.monotonic()-tick, 'count': len(vectors), 'usage': usage}
            temporary = data_path.with_suffix('.tmp.npy')
            np.save(temporary, vectors)
            temporary.replace(data_path)
            metadata_path.write_text(json.dumps(metadata))
        batches.append(vectors)
        records.append(metadata)
        if first % (batch_size*10) == 0 or first+batch_size >= len(texts):
            print(json.dumps({'cache': str(destination), 'completed': min(first+batch_size,len(texts)), 'total':len(texts), 'wall_seconds':round(time.monotonic()-started,1)}), flush=True)
    vectors = np.concatenate(batches)
    np.save(destination / 'vectors.npy', vectors)
    totals = {'count':len(texts), 'dim':vectors.shape[1], 'total_seconds':sum(r['seconds'] for r in records), 'batch_size':batch_size, 'batch_seconds':[r['seconds'] for r in records], 'input_sha256':signature}
    (destination/'summary.json').write_text(json.dumps(totals,indent=2))
    return vectors, totals


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--chunks', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--batch-size', type=int, default=32)
    args = parser.parse_args()
    texts = [json.loads(line)['payload'] for line in args.chunks.open()]
    encode(args.url, texts, args.output, args.batch_size)
