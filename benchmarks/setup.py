"""Fetch and verify SciFact/models and start isolated benchmark model services."""
import argparse
import hashlib
import json
import os
import subprocess
import urllib.request
import zipfile
from pathlib import Path


def checked_download(path, url, algorithm, expected):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        temporary=path.with_suffix(path.suffix+'.download')
        print('Downloading '+url,flush=True)
        with urllib.request.urlopen(url,timeout=60) as source,temporary.open('wb') as target:
            while block:=source.read(1024*1024):
                target.write(block)
        temporary.replace(path)
    actual=hashlib.new(algorithm,path.read_bytes()).hexdigest()
    if actual!=expected:
        raise ValueError(f'Checksum mismatch for {path}: {actual}')
    print('Verified '+str(path),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    args=parser.parse_args()
    cfg=json.loads(args.config.read_text())
    cache=Path(cfg['cache'])
    archive=cache/'datasets/scifact.zip'
    checked_download(archive,cfg['dataset_url'],'md5',cfg['dataset_md5'])
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            path=Path(member.filename)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError('Unsafe ZIP path')
        zipped.extractall(archive.parent)
    for model in cfg['models']:
        path=Path(model['model_file'])
        if not path.exists() and not model.get('download_url'):
            raise FileNotFoundError(f'Provide the existing Qwen model at {path}')
        checked_download(path,model.get('download_url',''),'sha256',model['sha256'])
    env = os.environ.copy()
    qwen = next(model for model in cfg['models'] if model['id'] == 'qwen-q8')
    env['EMBEDDING_MODEL_FILE'] = str(Path(qwen['model_file']).resolve())
    subprocess.run(['docker','compose','--profile','postgres','up','-d','--wait','postgres','embeddings'],env=env,check=True)
    container = json.loads(subprocess.check_output(['docker', 'inspect', qwen['container']], text=True))[0]
    network = cfg.get('network') or next(iter(container['NetworkSettings']['Networks']))
    for model in cfg['models']:
        if model['id']=='qwen-q8': continue
        found=subprocess.run(['docker','inspect',model['container']],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
        if found:
            subprocess.run(['docker','start',model['container']],check=True,stdout=subprocess.DEVNULL)
        else:
            subprocess.run(['docker','run','-d','--name',model['container'],'--network',network,'-v',str(Path(model['model_file']).resolve())+':/models/model.gguf:ro',cfg['runtime_image'],'-m','/models/model.gguf','--embedding','--host','0.0.0.0','--port','8080','--pooling',model['pooling'],'--ctx-size','2048','--parallel','4','--threads','16','--ubatch-size','2048','--batch-size','2048'],check=True)
    with (cache/'datasets/scifact/chunks.jsonl').open('w') as target:
        subprocess.run(['go','run','./cmd/prepare-benchmark','--corpus',str(cache/'datasets/scifact/corpus.jsonl')],stdout=target,check=True)


if __name__=='__main__':
    main()
