#!/usr/bin/env python3
"""Persist CPU or the supplied CUDA preset; advise on other detected GPU backends."""
import argparse
import os
from pathlib import Path
import subprocess

from machine_info import inspect_machine

ROOT = Path(__file__).resolve().parent.parent
BASE = 'docker-compose.yml'
GPU = 'docker-compose.gpu.yml'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', required=True, choices=['cpu', 'gpu'])
    args = parser.parse_args()
    if 'COMPOSE_FILE' in os.environ or 'COMPOSE_PATH_SEPARATOR' in os.environ:
        parser.error('Unset shell COMPOSE_FILE and COMPOSE_PATH_SEPARATOR before persisting a mode in .env.')
    if args.mode == 'gpu':
        info = inspect_machine()
        if not info['cuda_container_ready']:
            alternatives = ', '.join(c['backend'] for c in info.get('inference_candidates', []) if c['backend'] not in ['cpu', 'cuda'])
            if alternatives and not info.get('nvidia_hardware_detected'):
                parser.error('The supplied GPU preset is CUDA-specific. Detected hardware has candidate routes: ' + alternatives +
                             '. Inspect make hardware and docs/gpu-backends.md, verify compatibility, and prepare a matching local override before selecting GPU. Configuration was not changed.')
            parser.error('The CUDA preset needs a working NVIDIA driver, NVIDIA Container Toolkit CDI devices, and CDI-enabled Docker. Run make hardware; use docs/gpu-backends.md to evaluate other GPU backends.')
    env = subprocess.check_output(['docker', 'compose', 'config', '--environment'], cwd=ROOT, text=True)
    settings = dict(line.split('=', 1) for line in env.splitlines() if '=' in line)
    previous = settings.get('COMPOSE_FILE', BASE)
    if settings.get('COMPOSE_PATH_SEPARATOR', ':') != ':':
        parser.error('Custom COMPOSE_PATH_SEPARATOR is unsupported; configure Compose files manually.')
    if previous not in (BASE, BASE + ':' + GPU):
        parser.error('Custom COMPOSE_FILE is configured; preserve its overrides and choose acceleration manually.')
    value = BASE + (':' + GPU if args.mode == 'gpu' else '')
    path = ROOT / '.env'
    lines = path.read_text().splitlines(keepends=True) if path.exists() else []
    updated = []
    for line in lines:
        if line.split('=', 1)[0].strip() != 'COMPOSE_FILE':
            updated.append(line)
    if updated and not updated[-1].endswith('\n'):
        updated[-1] += '\n'
    updated.append('COMPOSE_FILE=' + value + '\n')
    # Validate the selected files before writing; no service is started here.
    command = ['docker', 'compose', '-f', BASE]
    if args.mode == 'gpu':
        command += ['-f', GPU]
    subprocess.run(command + ['config', '--quiet'], cwd=ROOT, check=True)
    path.write_text(''.join(updated))
    print(f'Saved {args.mode} mode in {path}. Apply it with make up PROFILE=postgres (or qdrant).')


if __name__ == '__main__':
    main()
