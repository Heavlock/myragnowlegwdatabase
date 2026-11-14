#!/usr/bin/env python3
"""Read local hardware and Docker acceleration prerequisites without changing them."""
import csv
import io
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

PCI_ROOT = Path('/sys/bus/pci/devices')
VENDORS = {'0x10de': 'NVIDIA', '0x1002': 'AMD', '0x8086': 'Intel', '0x106b': 'Apple'}


def command(*args):
    try:
        result = subprocess.run(args, text=True, capture_output=True, timeout=20)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def memory_mib(value):
    try:
        return int(value)
    except ValueError:
        return None


def gpu_inventory(display_lines, pci_root=None):
    """Inventory display-class PCI devices even when vendor tools are missing."""
    pci_root = PCI_ROOT if pci_root is None else pci_root
    records = {}
    for line in (display_lines or '').splitlines():
        if not any(kind in line for kind in ['VGA compatible controller', '3D controller', 'Display controller']):
            continue
        match = re.match(r'(\S+)\s+.*?:\s+(.+?)\s+\[([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\]', line)
        if match:
            address, name, vendor, device = match.groups()
            address = address if address.count(':') == 2 else '0000:' + address
            records[address] = {'pci_address': address, 'name': name, 'vendor': VENDORS.get('0x' + vendor.lower(), 'Other'),
                                'vendor_id': '0x' + vendor.lower(), 'device_id': '0x' + device.lower()}
    for device in pci_root.glob('*'):
        try:
            if int((device / 'class').read_text().strip(), 16) >> 16 != 3:
                continue
            vendor = (device / 'vendor').read_text().strip().lower()
            device_id = (device / 'device').read_text().strip().lower()
            record = records.setdefault(device.name, {'pci_address': device.name, 'name': f'{VENDORS.get(vendor, "Other")} PCI device {device_id}',
                                                       'vendor': VENDORS.get(vendor, 'Other'), 'vendor_id': vendor, 'device_id': device_id})
            record['driver'] = (device / 'driver').resolve().name if (device / 'driver').exists() else None
            record['render_nodes'] = ['/dev/dri/' + p.name for p in (device / 'drm').glob('renderD*')]
            total = device / 'mem_info_vram_total'
            used = device / 'mem_info_vram_used'
            if total.exists():
                record['vram_total_mib'] = int(total.read_text().strip()) // 1024**2
                record['memory_source'] = 'kernel driver; may include shared/reserved RAM on integrated GPUs'
                if used.exists():
                    record['vram_free_mib'] = max(0, record['vram_total_mib'] - int(used.read_text().strip()) // 1024**2)
        except (OSError, ValueError):
            continue
    return list(records.values()), display_lines is not None or pci_root.is_dir()


def inference_advice(gpus, cuda_ready):
    """Candidate routes for an installer to verify, not automatic GPU selection."""
    advice = [{'backend': 'cpu', 'preset_available': True, 'status': 'available',
               'advice': 'Use as a baseline or when GPU support, memory, or measured benefit is insufficient.'}]
    vendors = {gpu['vendor'] for gpu in gpus}
    if 'NVIDIA' in vendors:
        advice.append({'backend': 'cuda', 'preset_available': True,
                       'status': 'ready_for_validation' if cuda_ready else 'requires_setup_and_validation',
                       'advice': 'Check exact GPU/driver compatibility, free VRAM and NVIDIA CDI access; validate the CUDA preset.'})
    for vendor, backend, reason in [
        ('AMD', 'rocm', 'Verify the exact GPU, OS and ROCm support matrix before installing ROCm.'),
        ('Intel', 'sycl', 'Verify the exact GPU, OS, Intel driver and oneAPI/SYCL support.'),
        ('Apple', 'metal', 'Use native macOS llama.cpp with Metal; adapt the application architecture and host embedding endpoint.'),
    ]:
        if vendor in vendors:
            advice.append({'backend': backend, 'preset_available': False, 'status': 'requires_configuration_and_validation', 'advice': reason})
    if vendors & {'AMD', 'Intel', 'NVIDIA', 'Other'}:
        advice.append({'backend': 'vulkan', 'preset_available': False, 'status': 'requires_configuration_and_validation',
                       'advice': 'Check Vulkan compute features, the actual physical GPU and container render-node access; do not mistake a software Vulkan device for GPU support.'})
    return advice


def inspect_machine():
    cpu = platform.processor()
    mem_kib = {}
    if Path('/proc/cpuinfo').exists():
        cpu = next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                    if line.startswith('model name')), cpu)
    if Path('/proc/meminfo').exists():
        mem_kib = {line.split(':')[0]: int(line.split()[1])
                   for line in Path('/proc/meminfo').read_text().splitlines()}
    raw = command('nvidia-smi', '--query-gpu=index,name,memory.total,memory.free,driver_version,pci.bus_id',
                  '--format=csv,noheader,nounits')
    display_lines = command('lspci', '-Dnn')
    displays = '\n'.join(line for line in (display_lines or '').splitlines()
                         if any(kind in line for kind in ['VGA compatible controller', '3D controller', 'Display controller']))
    inventory, detection_complete = gpu_inventory(display_lines)
    if platform.system() == 'Darwin':
        apple = command('system_profiler', 'SPDisplaysDataType', '-json')
        if apple:
            for item in json.loads(apple).get('SPDisplaysDataType', []):
                name = item.get('sppci_model') or item.get('_name', 'Unknown macOS GPU')
                vendor = 'Apple' if 'Apple' in name else next((v for v in ['AMD', 'Intel', 'NVIDIA'] if v in name), 'Other')
                inventory.append({'name': name, 'vendor': vendor, 'driver': 'macOS',
                                  'reported_memory': item.get('spdisplays_vram') or item.get('spdisplays_vram_shared')})
            detection_complete = True
    nvidia_detected = bool(raw or any(gpu['vendor'] == 'NVIDIA' for gpu in inventory))
    gpus = []
    for row in csv.reader(io.StringIO(raw or '')):
        if len(row) != 6:
            continue
        index, name, total, free, driver, address = (field.strip() for field in row)
        total, free = memory_mib(total), memory_mib(free)
        gpus.append({'index': index, 'name': name, 'memory_total_mib': total,
                     'memory_free_mib': free, 'driver': driver, 'pci_address': address[-12:].lower()})
        match = next((gpu for gpu in inventory if gpu.get('pci_address') == address[-12:].lower()), None)
        if match is None:
            match = {'name': name, 'vendor': 'NVIDIA', 'pci_address': address[-12:].lower()}
            inventory.append(match)
        match.update(vram_total_mib=total, vram_free_mib=free, memory_source='nvidia-smi')
    raw_runtimes = command('docker', 'info', '--format', '{{json .Runtimes}}')
    runtimes = sorted(json.loads(raw_runtimes)) if raw_runtimes else []
    toolkit = shutil.which('nvidia-ctk')
    raw_cdi = command('nvidia-ctk', 'cdi', 'list') if toolkit else None
    cdi_devices = [line for line in (raw_cdi or '').splitlines() if line.startswith('nvidia.com/gpu=')]
    raw_cdi_dirs = command('docker', 'info', '--format', '{{json .CDISpecDirs}}')
    cdi_dirs = json.loads(raw_cdi_dirs) if raw_cdi_dirs else []
    cuda_ready = bool(gpus and toolkit and cdi_devices and cdi_dirs)
    return {
        'system': platform.system(), 'architecture': platform.machine(), 'cpu': cpu,
        'logical_cpus': os.cpu_count(), 'memory_total_mib': mem_kib.get('MemTotal', 0) // 1024,
        'memory_available_mib': mem_kib.get('MemAvailable', 0) // 1024,
        'display_devices': displays or None,
        'gpus': inventory,
        'nvidia_hardware_detected': nvidia_detected,
        'nvidia_driver_ready': bool(gpus),
        'gpu_detection_complete': bool(raw) or detection_complete,
        'nvidia_gpus': gpus, 'docker_available': raw_runtimes is not None,
        'docker_runtimes': runtimes, 'nvidia_container_toolkit': toolkit,
        'nvidia_cdi_devices': cdi_devices, 'docker_cdi_spec_dirs': cdi_dirs,
        'cuda_container_ready': cuda_ready,
        'compute_options': ['cpu', 'gpu'] if inventory else ['cpu'],
        'gpu_setup_required': bool(inventory and not cuda_ready),
        'inference_candidates': inference_advice(inventory, cuda_ready),
    }


if __name__ == '__main__':
    print(json.dumps(inspect_machine(), indent=2))
