# Installation and maintenance

Run commands from the repository root. For the short setup path, see the [README](../README.md#quick-start).

## Install the required tools

The Dockerfile builds a Linux amd64 binary. The installation commands below target Ubuntu with Bash. Other hosts require compatible amd64 container support or an adapted build. Container execution does not require Go, Java, Python ML packages, LM Studio, or a GPU on the host. Python 3 is needed for the smoke tests, and host Go is needed for Go builds/tests.

On Ubuntu, install the command-line utilities if missing:

```bash
sudo apt-get update
sudo apt-get install -y git make bash curl ca-certificates python3 coreutils
```

For a fresh Ubuntu installation, configure Docker's repository and install Engine, Buildx, and the Compose plugin. If Docker is already installed, keep your working installation and proceed to the checks. For conflicting older packages or another operating system, follow the [official installation guide](https://docs.docker.com/engine/install/ubuntu/).

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

Give your current user access using Docker's [Linux post-installation instructions](https://docs.docker.com/engine/install/linux-postinstall/), then log out and back in. Membership in the Docker group grants root-level privileges:

```bash
sudo usermod -aG docker "$USER"
```

Verify access from the new login session before continuing:

```bash
docker info
docker compose version
make --version
python3 --version
command -v bash curl sha256sum
```

For local development, install Go 1.25 or newer using the [official Go installation instructions](https://go.dev/doc/install), add its `bin` directory to `PATH`, and verify it:

```bash
go version
```

The Docker build installs the Go toolchain and Go dependencies inside its build stage. You do not need to install PostgreSQL, pgvector, Qdrant, or llama.cpp on the host: Compose provides them. Internet access is needed for the initial model download, container image pulls, and Go dependency downloads. Keep several GB of free disk space for images, model files, and data, and allow RAM beyond the model's on-disk size for inference and databases.

## CPU or GPU inference

Inspect the local hardware and prerequisites before choosing:

```bash
make hardware
```

The report inventories GPU vendors/models, PCI devices, kernel drivers, render nodes, memory where available, and candidate inference backends. Discovery also works without NVIDIA tools. Read [GPU backend selection](gpu-backends.md) to assess NVIDIA CUDA, AMD ROCm/Vulkan, Intel SYCL/Vulkan, native Apple Metal, or CPU using the exact hardware and current official compatibility information. Account for inference buffers, shared memory and concurrent applications. Compare performance on the actual machine rather than assuming a GPU is faster.

The supplied execution presets are CPU and NVIDIA CUDA on Linux amd64. The `MODE=gpu` command below refers to that CUDA preset. Other detected vendors are candidates for a matching local override or native runtime after compatibility checks; detection is not a claim of tested acceleration. No NVIDIA toolkit is needed for a non-NVIDIA route.

Persist CPU inference (the default):

```bash
make compute MODE=cpu
make up PROFILE=postgres
```

For NVIDIA GPU inference, first confirm that `nvidia-smi` works on the host. Install a compatible driver if needed using [NVIDIA's driver instructions](https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/). With Docker and the driver already working, the optional Ubuntu/Debian installer follows [NVIDIA Container Toolkit installation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html):

```bash
sudo bash scripts/install_nvidia_toolkit.sh
make hardware
make compute MODE=gpu
docker compose --profile postgres pull embeddings
make up PROFILE=postgres
```

The installer adds NVIDIA's signed stable package repository, installs Container Toolkit, and refreshes its CDI device specifications. It needs sudo, Python 3, systemd, and CDI-enabled Docker Engine (28.3+ enables CDI by default). It does not install a driver or a host CUDA development toolkit, change Docker settings, or restart Docker. Inspect `nvidia-ctk cdi list` and `make hardware` if device discovery fails.

`make compute` changes only `COMPOSE_FILE` in the ignored repository-local `.env`. CPU selects `docker-compose.yml`, the CPU server image, and zero GPU layers. GPU adds `docker-compose.gpu.yml`, selects `ghcr.io/ggml-org/llama.cpp:server-cuda`, requests CDI device `nvidia.com/gpu=0` (override the index with `EMBEDDING_GPU_ID`), and requests offloading of all model layers. See [llama.cpp's GPU images](https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md), [NVIDIA CDI support](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html), and [Docker CDI devices](https://docs.docker.com/reference/cli/dockerd/#configure-cdi-devices). No automatic fallback hides a failed GPU setup. A custom `COMPOSE_FILE` is left for manual configuration; unset shell `COMPOSE_FILE`/`COMPOSE_PATH_SEPARATOR` when relying on `.env`.

Selection persists across terminal sessions and applies to plain Compose commands and both database profiles. Selecting a mode does not start or restart anything; `make up` applies it. For installation-only work, omit `make up`, pull `postgres embeddings` for PostgreSQL (or `qdrant embeddings` for Qdrant), and build only the selected app/MCP services. Switching CPU/GPU keeps the same model, dimensions, query prefix and storage; no reindexing is needed merely to change the compute device. Both profiles share one embedding service, so applying a mode briefly affects both clients.

After startup, inspect `docker compose logs embeddings`: GPU mode must report CUDA device discovery and nonzero offloaded layers. Check a real request too; a healthy container alone does not prove GPU execution. The following comparison runs CPU and GPU sequentially in disposable PostgreSQL projects, checks UI/HTTP/MCP and persistence, validates embeddings and retrieval consistency, and saves measurements under `reports/compute/`:

```bash
make compute-test
```

It needs a prepared default Qwen3 model, Docker GPU support, and both server images from the same llama.cpp source revision. If cached tags differ, refresh both images or use matching pinned versions before comparing timings. It preserves the working stack and its volumes. To run the existing profile smoke test in one mode, use `make smoke-test PROFILE=postgres COMPUTE_MODE=cpu` or `COMPUTE_MODE=gpu`; its default is CPU regardless of the working `.env` mode. Test fixtures are never inserted into the working store.

## PostgreSQL schema management

A fresh PostgreSQL volume is initialized from `migrations/`. Docker runs these files only on the first initialization; restarting an existing volume does not apply schema changes. Qdrant requires no PostgreSQL instance or SQL migrations.

For an existing PostgreSQL database, install the [pgCodeKeeper CLI](https://github.com/pgcodekeeper/pgcodekeeper-cli/releases) and its Java runtime. Configure the executable and JDBC connection explicitly:

```bash
export PGCODEKEEPER_CLI=/absolute/path/to/pgcodekeeper-cli.sh
export MYRAG_DB_DSN='jdbc:postgresql://localhost:6432/rag?user=rag&password=rag'
make migration-generate
```

Review `sql/migrations/myrag.sql` before applying changes:

```bash
make migrate
```

`migrate` compares `sql/project` against the target database and applies that schema diff; it does not execute the generated SQL file. Schema synchronization can drop database objects absent from the local schema, so review the generated diff first. The migration scripts default to the JDBC connection above and look for `pgcodekeeper-cli.sh` on `PATH` if `PGCODEKEEPER_CLI` is unset.

To replace the local schema project with the database's schema:

```bash
make migration-pull
```

Optional environment overrides: `SCHEMA_DIR` selects the source schema directory for generation/application and the destination for schema export; `MIGRATION_OUTPUT` selects the generated SQL file. These allow migration tests to use temporary paths without changing the checked-in schema.
