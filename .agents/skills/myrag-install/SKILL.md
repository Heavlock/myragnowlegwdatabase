---
name: myrag-install
description: Prepare, start, or verify this repository's local RAG application; inspect machine hardware, advise on compatible CPU/GPU backends, and configure its embedding model and database profile.
---

# Set up the local RAG application

Use the [installation guide](../../../docs/installation.md#install-the-required-tools) for prerequisites and the [README](../../../README.md) for model preparation, profile ports, and troubleshooting. Keep installation changes scoped to this repository.

## Inspect the machine and choose CPU or GPU

Before preparing inference, run `make hardware`. Inspect OS/architecture, CPU, available RAM, **all detected GPU vendors and exact models**, loaded drivers, available GPU memory, render-device access, and container/runtime support. The report includes PCI/sysfs discovery without requiring NVIDIA tools, macOS display discovery, and conditional backend candidates. Integrated GPUs may share system RAM; do not treat reported memory as dedicated/free VRAM. Missing inspection tools or a failed vendor query are unknown GPU readiness, not proof that the machine has no GPU. The supplied application container build targets Linux amd64; plan any architecture or native-host changes before pulling images.

Read [GPU backend selection](../../../docs/gpu-backends.md). Check current official compatibility documentation for the **exact GPU, OS, driver and runtime versions**, rather than deciding from the vendor alone. Evaluate NVIDIA CUDA, AMD ROCm or Vulkan, Intel SYCL or Vulkan, native Apple Metal, or another officially supported backend as applicable. CPU remains an option. Do not install NVIDIA software for a different vendor. Reuse compatible prerequisites and distinguish upstream capability, an available repository preset, and execution actually verified on this machine.

Give a concrete recommendation with reasons: model and buffer memory fit, dedicated versus shared memory, setup/maintenance effort, support maturity, and expected usefulness for the workload. For several GPUs, recommend a specific device and explain alternatives. A small integrated GPU can make CPU the more practical choice; do not assume every GPU is faster. Do not transfer timings from this desktop to another machine. If feasibility depends on the embedding model, finish the model choice before recommending a device.

Present the feasible named choices and your recommendation, then ask unless the user already chose, for example:

> This machine has [GPU model] and [available RAM/VRAM]. I recommend [CPU or named GPU/backend] because [reasons]. Which feasible option should I configure: [options]?

Wait for the answer before selecting acceleration or installing its extra dependencies. Present an option with missing prerequisites as requiring setup/validation, not ready to run. If only CPU is viable, explain the detected limitation and ask whether to proceed. Honor the user's choice and existing authorization; never silently switch device/backend after a failure.

Follow [CPU or GPU inference](../../../docs/installation.md#cpu-or-gpu-inference). The supplied `docker-compose.gpu.yml` is a **CUDA preset**, not a vendor-neutral implementation. Only use it for a suitable NVIDIA GPU: check CDI device discovery and CDI-enabled Docker, then run `make compute MODE=gpu`. CPU uses `make compute MODE=cpu`. For another chosen backend, prepare a matching repository-local override or native embedding-service setup using its official instructions; adjust the selector/tests if needed so future sessions retain the choice. Preserve the same model, pooling, dimensions and query prefix, existing custom overrides and unrelated `.env` fields. Confirm host/container device access and the actual selected adapter. Keep runtime-specific changes local except authorized host prerequisites. Both database profiles share the embedding service.

Persist the chosen Compose files or native endpoint in repository-local configuration and clear conflicting shell overrides. Inspect the effective selected profile's image, backend, offload setting, device access and application/MCP embedding endpoint before pulling/building. A vendor name, image tag, runtime registration, or upstream image availability alone does not prove compatibility. For installation-only work, prepare the selected components without starting services.

## Choose the installation database

If the user has not already selected a database for this installation, ask:

> Which database should I install: PostgreSQL only, Qdrant only, or both?

Wait for the answer before installing backend components or pulling database images. Do not silently use the Makefile's PostgreSQL default as the installation choice. Honor a choice already stated in the request or current task without asking again. Install only the selected backend components; selecting both uses separate document stores and the shared embedding service.

For an installation-only request, prepare the selected dependencies, model, and images without starting services. Perform the startup and live verification steps below only when startup is also requested.

## Choose the embedding model

Unless already selected, ask before downloading/configuring a model:

> Which embedding model should I install: Qwen3, BGE-small, MiniLM, or another?

Explain the model options using the [documented dimensions, pooling and query formats](../../../docs/embedding-models.md#model-specific-query-prefixes). Use the [benchmark tools](../../../benchmarks/README.md) for workload-specific comparisons; do not assume timings from another machine. Wait for the choice; do not repeat an already answered question.

## Configure the selected model's query prefix

Explicitly set `EMBEDDING_QUERY_PREFIX` for the chosen model, replacing any inherited value. The application does not select a prefix from the model ID.

| Selected model | Query-prefix value |
| --- | --- |
| Qwen3-Embedding-0.6B | `Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: ` |
| BGE-small-en-v1.5 | `Represent this sentence for searching relevant passages: ` |
| all-MiniLM-L6-v2 | Empty string, explicitly set |

Use the [model-specific commands and official references](../../../docs/embedding-models.md#model-specific-query-prefixes). Qwen needs an actual newline; Qwen/BGE values retain their trailing space. MiniLM must have an empty value, not an unset variable, which would fall back to Qwen. These are query instructions; do not prepend them to documents.

Persist the selected prefix with the GGUF path, model ID, dimensions, and pooling in the ignored repository-local `.env`, preserving unrelated settings. Follow the embedding-model guide's Compose quoting rules and remove conflicting shell overrides. Configure compatible storage before indexing; a fresh non-default PostgreSQL model also needs the documented schema conversion. For another model, consult its own official instructions instead of copying a Qwen/BGE prefix.

Before building/installing the selected services, inspect `docker compose --profile <selected-profile> config --format json` and verify the exact effective prefix for both its application and MCP service. Check actual newline/trailing-space characters and an explicit empty MiniLM value. When startup is requested, also verify the created containers receive that value. Keep the configured model choice across subsequent commands and terminal sessions.

## Prepare and verify

- Inspect Docker/Compose availability, the selected profile, existing services, model path, and current configuration first. Reuse a compatible working installation.
- Follow the README to prepare the GGUF model. `make model-download` downloads/verifies the pinned default Qwen artifact; it does not install arbitrary models. Keep `EMBEDDING_MODEL_FILE` explicit when using another location.
- Start the selected profile with `make up PROFILE=postgres` or `PROFILE=qdrant`. Check status/logs, the English UI, MCP initialization, and the read-only search operation. A zero-result search is normal for a fresh store.
- For GPU startup, verify the chosen backend/device is accessible, logs report real offloading or backend execution on that adapter, and an embedding/search request succeeds. Check for software-renderer/CPU fallback, correct finite vector dimensions, and retrieval behavior. Use the backend's monitoring tools when available. The supplied CUDA override enables placement logs; other backends need their own equivalent verification. `make compute-test` currently tests CPU/CUDA with disposable PostgreSQL volumes; adapt an isolated check for another chosen backend rather than claiming the CUDA test covers it. Record local timings only if measured. Never put test fixtures in the working store or switch its database backend just to test inference.
- Use [model switching](../../../docs/embedding-models.md#switching-the-embedding-model) for an existing store whose model/dimension must change. Changing a weight-file path alone is insufficient.
- Keep persistent volumes and original documents. Starting services is not a reason to reset a database or import test fixtures into the user's working store. Use the repository's isolated smoke tests when verification needs writes.
- Install missing host dependencies only as needed for the requested setup, following the user's existing authorization and environment permissions. Report an unavailable prerequisite accurately; do not repeatedly ask to approve work already requested.

The [knowledge contracts](../../../docs/knowledge-contracts.md) explain the local client and profile selection. After startup, search without modifying the store:

```bash
python3 scripts/myrag_client.py --profile postgres search --query 'installation check' --limit 1
```

Report the selected database, model and compute mode, running UI/MCP addresses when started, and checks performed. State unavailable prerequisites or untested GPU execution explicitly. Never report installation or indexing as successful based only on a proposed command.
