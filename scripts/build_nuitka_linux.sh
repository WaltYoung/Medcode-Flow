#!/usr/bin/env bash
# 在 Ubuntu 22.04 上用 Nuitka 把工作流编成 Linux 可执行文件。
# 产物依赖这台机器的 glibc，换发行版或更高版本系统编出来的文件不能直接拿到 22.04 上跑。
#
#   cd /path/to/medcode-flow
#   bash scripts/build_nuitka_linux.sh
#
# 可选：
#   PYTHON_BIN=python3.11
#   VENV_DIR=.venv-build
#   SKIP_PIP_INSTALL=1
#   ENABLE_LTO=1          默认开启，即编译优化

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f /etc/os-release ]]; then
  echo "只能在 Linux 上打包" >&2
  exit 1
fi
# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "22.04" ]]; then
  echo "当前系统是 ${PRETTY_NAME:-unknown}。工作流发版要求 Ubuntu 22.04。" >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
VENV_DIR="${VENV_DIR:-.venv-build}"
ENABLE_LTO="${ENABLE_LTO:-1}"
SKIP_PIP_INSTALL="${SKIP_PIP_INSTALL:-0}"
JOBS="${JOBS:-$(nproc)}"
ENTRY="run.py"
DIST_NAME="medcode-flow"
OUT_DIR="$ROOT/build/nuitka"

run_root() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "==> 安装 Python 3.11 和编译工具"
  export DEBIAN_FRONTEND=noninteractive
  run_root apt-get update
  run_root apt-get install -y python3.11 python3.11-venv python3.11-dev \
    build-essential ccache patchelf ca-certificates
fi

echo "==> $($PYTHON_BIN --version) on ${PRETTY_NAME}"

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if [[ "$SKIP_PIP_INSTALL" != "1" ]]; then
  python -m pip install --upgrade pip
  pip install -r requirements.txt nuitka
fi

LTO_ARGS=()
if [[ "$ENABLE_LTO" == "1" ]]; then
  LTO_ARGS+=(--lto=yes)
fi

rm -rf "$OUT_DIR" "$ROOT/dist/${DIST_NAME}" "$ROOT/dist/${DIST_NAME}-linux.zip"
mkdir -p "$ROOT/dist"

echo "==> Nuitka standalone"
python -m nuitka \
  --standalone \
  --assume-yes-for-downloads \
  --output-dir="$OUT_DIR" \
  --output-filename="$DIST_NAME" \
  --remove-output \
  --jobs="$JOBS" \
  "${LTO_ARGS[@]}" \
  --include-package=app \
  --include-package=uvicorn \
  --include-package=fastapi \
  --include-package=starlette \
  --include-package=pydantic \
  --include-package=pydantic_settings \
  --include-package=langgraph \
  --include-package=langchain \
  --include-package=langchain_core \
  --include-package=langchain_openai \
  --include-package=langchain_community \
  --include-package=openai \
  --include-package=dashscope \
  --include-package=httpx \
  --include-package=jinja2 \
  --include-package=anyio \
  --include-package=redis \
  --include-package=tzdata \
  --include-module=uvicorn.logging \
  --include-module=uvicorn.loops \
  --include-module=uvicorn.loops.auto \
  --include-module=uvicorn.protocols.http.auto \
  --include-module=uvicorn.protocols.websockets.auto \
  --include-module=uvicorn.lifespan.on \
  --include-data-dir=app/workflows/medical_record_extract/prompts=app/workflows/medical_record_extract/prompts \
  --include-data-dir=app/workflows/secondary_diagnosis/prompts=app/workflows/secondary_diagnosis/prompts \
  --include-data-dir=app/workflows/other_diagnosis/prompts=app/workflows/other_diagnosis/prompts \
  --nofollow-import-to=pytest \
  --nofollow-import-to=tests \
  "$ENTRY"

BUILT="$OUT_DIR/run.dist"
if [[ ! -d "$BUILT" ]]; then
  echo "未找到 Nuitka 产物: $BUILT" >&2
  exit 1
fi

cp "$ROOT/.env.example" "$BUILT/.env.example"
ARCHIVE="$(python - <<'PY'
import shutil
from pathlib import Path
root = Path(".").resolve()
built = root / "build" / "nuitka" / "run.dist"
archive = shutil.make_archive(str(root / "dist" / "medcode-flow-linux"), "zip", root_dir=built.parent, base_dir=built.name)
print(archive)
PY
)"

echo "==> done: $ARCHIVE"
echo "部署时解压整个 run.dist，在该目录放置 .env 后执行 ./medcode-flow"
echo "只替换可执行文件不够，旁边的库和提示词要一起换。"
