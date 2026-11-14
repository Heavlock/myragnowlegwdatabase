#!/usr/bin/env python3
"""Check persisted CPU/GPU selection without starting services or touching .env."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import configure_compute
import machine_info

ROOT = Path(__file__).resolve().parent.parent


class ComputeConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='myrag-compute-config-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in ['docker-compose.yml', 'docker-compose.gpu.yml']:
            shutil.copyfile(ROOT / name, self.root / name)
        self.original = ('# Keep local settings\nPOSTGRES_APP_PORT=18765\n'
                         'EMBEDDING_MODEL_FILE=/tmp/myrag-config-test-model.gguf\n'
                         'EMBEDDING_QUERY_PREFIX="Instruct: Given a question, retrieve relevant passages that answer the question\\nQuery: "\n'
                         'UNRELATED_SETTING="keep this value"\n')
        self.envfile = self.root / '.env'
        self.envfile.write_text(self.original)
        clean = {k: v for k, v in os.environ.items() if not k.startswith(('COMPOSE_', 'POSTGRES_', 'QDRANT_', 'EMBEDDING_', 'CHUNK_'))}
        self.environ = patch.dict(os.environ, clean, clear=True)
        self.environ.start()
        self.addCleanup(self.environ.stop)

    def select(self, mode, ready=True):
        with patch.object(configure_compute, 'ROOT', self.root), \
             patch.object(configure_compute, 'inspect_machine', return_value={'cuda_container_ready': ready}), \
             patch('sys.argv', ['configure_compute.py', '--mode', mode]), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            configure_compute.main()

    def config(self, profile):
        return json.loads(subprocess.check_output(['docker', 'compose', '--profile', profile,
                                                  'config', '--format', 'json'], cwd=self.root))

    def test_switching_preserves_model_prefix_ports_and_unrelated_settings(self):
        for mode in ['gpu', 'cpu', 'gpu', 'cpu']:
            self.select(mode)
            self.assertTrue(self.envfile.read_text().startswith(self.original))
            self.assertEqual(self.envfile.read_text().count('COMPOSE_FILE='), 1)
            for profile, app, mcp in [('postgres', 'app', 'mcp'), ('qdrant', 'app-qdrant', 'mcp-qdrant')]:
                config = self.config(profile)
                embedding = config['services']['embeddings']
                self.assertEqual(embedding['environment']['LLAMA_ARG_N_GPU_LAYERS'], '99' if mode == 'gpu' else '0')
                devices = embedding.get('devices', [])
                self.assertEqual(bool(devices), mode == 'gpu')
                self.assertEqual(embedding['image'].endswith(':server-cuda'), mode == 'gpu')
                for service in [app, mcp]:
                    self.assertEqual(config['services'][service]['environment']['EMBEDDING_QUERY_PREFIX'],
                                     'Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: ')
            self.assertEqual(self.config('postgres')['services']['app']['ports'][0]['published'], '18765')

    def test_gpu_without_runtime_does_not_change_configuration(self):
        with self.assertRaises(SystemExit):
            self.select('gpu', ready=False)
        self.assertEqual(self.envfile.read_text(), self.original)
        self.select('cpu', ready=False)
        self.assertIn('COMPOSE_FILE=docker-compose.yml\n', self.envfile.read_text())

    def test_non_nvidia_gpu_gets_backend_specific_advice_without_file_changes(self):
        info = {'cuda_container_ready': False, 'nvidia_hardware_detected': False,
                'inference_candidates': [{'backend': 'cpu'}, {'backend': 'rocm'}, {'backend': 'vulkan'}]}
        error = io.StringIO()
        with patch.object(configure_compute, 'ROOT', self.root), \
             patch.object(configure_compute, 'inspect_machine', return_value=info), \
             patch('sys.argv', ['configure_compute.py', '--mode', 'gpu']), \
             contextlib.redirect_stderr(error), self.assertRaises(SystemExit):
            configure_compute.main()
        self.assertIn('rocm, vulkan', error.getvalue())
        self.assertEqual(self.envfile.read_text(), self.original)

    def test_shell_override_is_rejected_without_mutating_file(self):
        with patch.dict(os.environ, {'COMPOSE_FILE': 'docker-compose.yml'}):
            with self.assertRaises(SystemExit):
                self.select('cpu')
        self.assertEqual(self.envfile.read_text(), self.original)

    def test_custom_compose_files_are_preserved(self):
        (self.root / 'custom.yml').write_text('services:\n  embeddings:\n    environment:\n      CUSTOM_SETTING: keep\n')
        custom = self.original + 'COMPOSE_FILE=docker-compose.yml:custom.yml\n'
        self.envfile.write_text(custom)
        with self.assertRaises(SystemExit):
            self.select('gpu')
        self.assertEqual(self.envfile.read_text(), custom)


class HardwareDiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='myrag-gpu-inventory-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'pci'
        self.root.mkdir()
        self.pci = patch.object(machine_info, 'PCI_ROOT', self.root)
        self.pci.start()
        self.addCleanup(self.pci.stop)

    def test_cdi_readiness_does_not_require_legacy_runtime_registration(self):
        def command(*args):
            if args[0] == 'nvidia-smi':
                return '0, NVIDIA GeForce RTX 3060, 12288, 10000, 595.99.02, 00000000:01:00.0'
            if args[0] == 'nvidia-ctk':
                return 'nvidia.com/gpu=0\nnvidia.com/gpu=all'
            if args[-1] == '{{json .Runtimes}}':
                return '{"runc": {}}'
            if args[-1] == '{{json .CDISpecDirs}}':
                return '["/var/run/cdi"]'
            return None
        with patch.object(machine_info, 'command', side_effect=command), \
             patch.object(machine_info.shutil, 'which', return_value='/usr/bin/nvidia-ctk'):
            info = machine_info.inspect_machine()
        self.assertTrue(info['cuda_container_ready'])
        self.assertNotIn('nvidia', info['docker_runtimes'])

    def test_nvidia_without_driver_remains_a_setup_option(self):
        def command(*args):
            if args[0] == 'lspci':
                return '0000:01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GeForce RTX 3060 [10de:2487]'
            if args[-1] == '{{json .Runtimes}}':
                return '{"runc": {}}'
            return None
        with patch.object(machine_info, 'command', side_effect=command), \
             patch.object(machine_info.shutil, 'which', return_value=None):
            info = machine_info.inspect_machine()
        self.assertEqual(info['compute_options'], ['cpu', 'gpu'])
        self.assertTrue(info['gpu_setup_required'])
        self.assertFalse(info['nvidia_driver_ready'])
        self.assertFalse(info['cuda_container_ready'])

    def test_missing_inspection_tools_reports_unknown_detection(self):
        with patch.object(machine_info, 'command', return_value=None), \
             patch.object(machine_info, 'gpu_inventory', return_value=([], False)), \
             patch.object(machine_info.shutil, 'which', return_value=None):
            info = machine_info.inspect_machine()
        self.assertFalse(info['gpu_detection_complete'])
        self.assertFalse(info['cuda_container_ready'])
        self.assertFalse(info['docker_available'])

    def test_amd_detection_without_nvidia_tools_and_shared_memory_advice(self):
        device = self.root / '0000:0d:00.0'
        device.mkdir()
        for name, value in {'class': '0x030000', 'vendor': '0x1002', 'device': '0x13c0',
                            'mem_info_vram_total': str(2 * 1024**3), 'mem_info_vram_used': str(16 * 1024**2)}.items():
            (device / name).write_text(value)
        driver = Path(self.temporary.name) / 'amdgpu'
        driver.mkdir()
        (device / 'driver').symlink_to(driver)
        (device / 'drm' / 'renderD128').mkdir(parents=True)
        with patch.object(machine_info, 'command', return_value=None), \
             patch.object(machine_info.shutil, 'which', return_value=None):
            info = machine_info.inspect_machine()
        gpu = info['gpus'][0]
        self.assertEqual(gpu['vendor'], 'AMD')
        self.assertEqual(gpu['driver'], 'amdgpu')
        self.assertEqual(gpu['render_nodes'], ['/dev/dri/renderD128'])
        self.assertEqual(gpu['vram_total_mib'], 2048)
        self.assertEqual(gpu['vram_free_mib'], 2032)
        self.assertIn('shared', gpu['memory_source'])
        self.assertFalse(info['nvidia_hardware_detected'])
        self.assertEqual(info['compute_options'], ['cpu', 'gpu'])
        self.assertEqual({c['backend'] for c in info['inference_candidates']}, {'cpu', 'rocm', 'vulkan'})
        self.assertTrue(all(not c['preset_available'] for c in info['inference_candidates'] if c['backend'] != 'cpu'))

    def test_intel_pci_identity_and_backend_candidates(self):
        line = '0000:03:00.0 Display controller [0380]: Intel Corporation Arc GPU [8086:56a0]'
        inventory, complete = machine_info.gpu_inventory(line)
        self.assertTrue(complete)
        self.assertEqual(inventory[0]['vendor'], 'Intel')
        self.assertEqual(inventory[0]['device_id'], '0x56a0')
        self.assertEqual({c['backend'] for c in machine_info.inference_advice(inventory, False)}, {'cpu', 'sycl', 'vulkan'})

    def test_native_apple_gpu_discovery(self):
        def command(*args):
            if args[0] == 'system_profiler':
                return json.dumps({'SPDisplaysDataType': [{'sppci_model': 'Apple M3 Pro'}]})
            return None
        with patch.object(machine_info.platform, 'system', return_value='Darwin'), \
             patch.object(machine_info, 'command', side_effect=command), \
             patch.object(machine_info.shutil, 'which', return_value=None):
            info = machine_info.inspect_machine()
        self.assertEqual(info['gpus'][0]['vendor'], 'Apple')
        self.assertEqual({c['backend'] for c in info['inference_candidates']}, {'cpu', 'metal'})


if __name__ == '__main__':
    unittest.main()
