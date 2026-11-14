# Choosing an inference backend for this machine

Run `make hardware` before recommending CPU or GPU. Its `gpus` inventory reports vendor/model, PCI identity, kernel driver, render nodes, and memory where available. `inference_candidates` lists routes to investigate, **not a compatibility guarantee or automatic selection**. NVIDIA CUDA readiness has a dedicated prerequisite probe; other candidates require their own checks. If discovery is incomplete, inspect the host with its native tools instead of reporting that no GPU exists.

| Detected hardware | Candidate route | Check before recommending |
| --- | --- | --- |
| Any supported host CPU | CPU | Application build architecture, available RAM, model fit and measured workload speed. |
| NVIDIA GPU | CUDA | Exact architecture/driver support, free VRAM, CUDA image compatibility and container CDI access. The repository supplies this preset. |
| AMD GPU | ROCm/HIP or Vulkan | Exact GPU and OS support in AMD's current matrix; Vulkan features and render-node access. Do not assume every Radeon or integrated GPU supports ROCm. |
| Intel GPU | SYCL/oneAPI or Vulkan | Exact GPU, driver/runtime and OS support; GPU enumeration and permissions inside the selected runtime. |
| Apple GPU on macOS | Native Metal | Native llama.cpp support, unified memory and the host embedding endpoint. The supplied Linux container cannot provide native Metal access; adapt the application build/deployment too. |
| Other GPU | An officially supported backend, possibly Vulkan | Exact device support and physical GPU enumeration; a software renderer such as llvmpipe does not establish GPU acceleration. |

Read current primary sources for the relevant route:

- [llama.cpp build backends](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) and [available GPU container images](https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md).
- [AMD ROCm compatibility](https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html); follow its links for the specific GPU family and operating system.
- [llama.cpp Intel SYCL support](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/SYCL.md).
- [NVIDIA CDI support](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html).

Recommend a named device/backend and explain its value for the selected model: memory headroom including context/batch buffers and other applications, setup effort, support status, and expected workload benefit. Small integrated GPUs use shared/reserved RAM and may offer little benefit over a capable CPU. Present CPU and any credible GPU routes, marking missing prerequisites and unverified compatibility. Ask the user to select unless they already chose. Never install another vendor's toolkit just because the command is named `MODE=gpu`.

The current execution presets are CPU and NVIDIA CUDA. `make compute MODE=gpu` selects the CUDA override only after its prerequisites pass. On a different vendor, prepare a backend-specific repository-local Compose override or native service **after the choice**, using the relevant official device/driver/runtime requirements. Preserve custom Compose files, persist the chosen files or endpoint in local configuration, and keep application and MCP clients on the same model service. Additional backends have not been validated by this repository's CPU/CUDA comparison; upstream image availability is not repository support.

For a requested startup, verify real execution on the selected physical GPU and a real embeddings response with the expected dimension and finite values, then check retrieval. Use disposable stores for write-based tests and compare with CPU when requested. Preserve existing documents and vectors when changing only the compute device; changing the embedding model requires the separate migration workflow. Report the backend, device, checks, and any remaining limits without claiming an untested route works.
