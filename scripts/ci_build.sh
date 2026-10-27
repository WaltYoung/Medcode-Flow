#!/usr/bin/env bash
# GitLab 打包入口。对应原来的 GitHub Actions：
#   BUILDER=Nuitka|PyInstaller
#   PYTHON_VERSION=3.11
#   ENTRY_POINT=run.py
#   CONSOLE=yes|no          只影响 Windows
# Linux 必须是 Ubuntu 22.04。Nuitka 走 scripts/build_nuitka_linux.sh，打成目录包。

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BUILDER="${BUILDER:-Nuitka}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
CONSOLE="${CONSOLE:-yes}"
ARTIFACT_NAME="${ARTIFACT_NAME:-medcode-flow-linux}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
export PIP_INDEX_URL

if [[ -z "${ENTRY_POINT:-}" || ! -f "$ENTRY_POINT" ]]; then
  ENTRY_POINT=""
  for candidate in run.py main.py app.py cli.py start.py __main__.py; do
    if [[ -f "$candidate" ]]; then
      ENTRY_POINT="$candidate"
      break
    fi
  done
fi
if [[ -z "$ENTRY_POINT" ]]; then
  echo "找不到入口脚本" >&2
  exit 1
fi
export ENTRY_POINT
echo "==> builder=$BUILDER python=$PYTHON_VERSION entry=$ENTRY_POINT console=$CONSOLE"

OS="$(uname -s)"

rm -rf dist build .venv-build

require_ubuntu_2204() {
  if [[ ! -f /etc/os-release ]]; then
    echo "Linux 包只能在 Ubuntu 22.04 上编译" >&2
    exit 1
  fi
  # shellcheck disable=SC1091
  source /etc/os-release
  if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "22.04" ]]; then
    echo "当前系统是 ${PRETTY_NAME:-unknown}。工作流发版要求 Ubuntu 22.04。" >&2
    exit 1
  fi
}

pick_python() {
  if command -v "python${PYTHON_VERSION}" >/dev/null 2>&1; then
    PY="python${PYTHON_VERSION}"
  elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
  elif command -v python >/dev/null 2>&1; then
    PY="python"
  else
    echo "找不到 Python ${PYTHON_VERSION}" >&2
    exit 1
  fi
}

prepare_venv() {
  local extra=("$@")
  pick_python
  if [[ ! -d .venv-build ]]; then
    "$PY" -m venv .venv-build
  fi
  # shellcheck disable=SC1091
  if [[ -f .venv-build/bin/activate ]]; then
    source .venv-build/bin/activate
  else
    # Windows 上的 venv
    source .venv-build/Scripts/activate
  fi
  python -m pip install --upgrade pip
  if [[ -f requirements.txt ]]; then
    pip install -r requirements.txt
  fi
  if [[ ${#extra[@]} -gt 0 ]]; then
    pip install "${extra[@]}"
  fi
}

data_sep() {
  case "$OS" in
    MINGW*|MSYS*|CYGWIN*) echo ";" ;;
    *) echo ":" ;;
  esac
}

build_pyinstaller() {
  local sep name
  sep="$(data_sep)"
  name="$ARTIFACT_NAME"
  prepare_venv pyinstaller
  local add_data=()
  [[ -d app ]] && add_data+=(--add-data "app${sep}app")
  [[ -d docs ]] && add_data+=(--add-data "docs${sep}docs")
  [[ -f .env.example ]] && add_data+=(--add-data ".env.example${sep}.")
  local console_flag=(--console)
  case "$OS" in
    MINGW*|MSYS*|CYGWIN*)
      if [[ "$CONSOLE" == "no" ]]; then
        console_flag=(--noconsole)
      fi
      ;;
  esac
  pyinstaller --onefile \
    --name "$name" \
    --paths . \
    "${add_data[@]}" \
    --collect-all fastapi \
    --collect-all uvicorn \
    --collect-all starlette \
    --collect-all pydantic \
    --collect-all langchain \
    --collect-all langchain_core \
    --collect-all langchain_openai \
    --collect-all langchain_community \
    --collect-all langgraph \
    --collect-all httpx \
    --collect-all jinja2 \
    --collect-all PyYAML \
    --collect-all redis \
    --hidden-import uvicorn.logging \
    --hidden-import uvicorn.loops \
    --hidden-import uvicorn.loops.auto \
    --hidden-import uvicorn.protocols \
    --hidden-import uvicorn.protocols.http \
    --hidden-import uvicorn.protocols.http.auto \
    --hidden-import uvicorn.protocols.websockets \
    --hidden-import uvicorn.protocols.websockets.auto \
    --hidden-import uvicorn.lifespan \
    --hidden-import uvicorn.lifespan.on \
    --hidden-import app \
    --hidden-import app.main \
    --hidden-import app.api \
    --hidden-import app.api.v1 \
    --hidden-import app.api.v1.workflows \
    --hidden-import app.api.v1.health \
    --hidden-import app.core \
    --hidden-import app.runtime \
    --hidden-import app.shared \
    --hidden-import app.workflows \
    --hidden-import app.workflows.medical_record_extract \
    --hidden-import app.workflows.other_diagnosis \
    --hidden-import app.workflows.secondary_diagnosis \
    --exclude-module pytest \
    "${console_flag[@]}" \
    "$ENTRY_POINT"
}

nuitka_common=(
  --include-package=app
  --include-package=uvicorn
  --include-package=fastapi
  --include-package=starlette
  --include-package=pydantic
  --include-package=pydantic_settings
  --include-package=langgraph
  --include-package=langchain
  --include-package=langchain_core
  --include-package=langchain_openai
  --include-package=langchain_community
  --include-package=openai
  --include-package=dashscope
  --include-package=httpx
  --include-package=jinja2
  --include-package=anyio
  --include-package=redis
  --include-package=tzdata
  --include-module=uvicorn.logging
  --include-module=uvicorn.loops
  --include-module=uvicorn.loops.auto
  --include-module=uvicorn.protocols.http.auto
  --include-module=uvicorn.protocols.websockets.auto
  --include-module=uvicorn.lifespan.on
  --include-data-dir=app/workflows/medical_record_extract/prompts=app/workflows/medical_record_extract/prompts
  --include-data-dir=app/workflows/secondary_diagnosis/prompts=app/workflows/secondary_diagnosis/prompts
  --include-data-dir=app/workflows/other_diagnosis/prompts=app/workflows/other_diagnosis/prompts
  --nofollow-import-to=pytest
  --nofollow-import-to=tests
)

build_nuitka_other() {
  prepare_venv nuitka ordered-set zstandard
  mkdir -p dist
  local jobs="${JOBS:-2}"
  if [[ "$OS" == Darwin ]]; then
    python -m nuitka --standalone --macos-create-app-bundle \
      --assume-yes-for-downloads \
      --jobs="$jobs" \
      "${nuitka_common[@]}" \
      "$ENTRY_POINT"
    local base
    base="$(basename "$ENTRY_POINT" .py)"
    rm -rf "dist/${ARTIFACT_NAME}"
    mv "${base}.app" "dist/${ARTIFACT_NAME}"
    return
  fi
  local extra=()
  if [[ "$CONSOLE" == "no" ]]; then
    extra+=(--windows-console-mode=disable)
  fi
  python -m nuitka --standalone --onefile \
    --assume-yes-for-downloads \
    --output-dir=dist \
    --output-filename="$ARTIFACT_NAME" \
    --jobs="$jobs" \
    "${extra[@]}" \
    "${nuitka_common[@]}" \
    "$ENTRY_POINT"
}

ensure_linux_python() {
  local bin="python${PYTHON_VERSION}"
  if command -v "$bin" >/dev/null 2>&1; then
    return
  fi
  export DEBIAN_FRONTEND=noninteractive
  if [[ "$(id -u)" -eq 0 ]]; then
    apt-get update
    if [[ "$PYTHON_VERSION" != "3.11" ]]; then
      apt-get install -y software-properties-common ca-certificates gnupg
      add-apt-repository -y ppa:deadsnakes/ppa
      apt-get update
    fi
    apt-get install -y "$bin" "${bin}-venv" "${bin}-dev" \
      build-essential ccache patchelf ca-certificates
  else
    sudo apt-get update
    if [[ "$PYTHON_VERSION" != "3.11" ]]; then
      sudo apt-get install -y software-properties-common ca-certificates gnupg
      sudo add-apt-repository -y ppa:deadsnakes/ppa
      sudo apt-get update
    fi
    sudo apt-get install -y "$bin" "${bin}-venv" "${bin}-dev" \
      build-essential ccache patchelf ca-certificates
  fi
}

case "$OS" in
  Linux)
    require_ubuntu_2204
    ensure_linux_python
    if [[ "$BUILDER" == "Nuitka" ]]; then
      export PYTHON_VERSION
      bash scripts/build_nuitka_linux.sh
    elif [[ "$BUILDER" == "PyInstaller" ]]; then
      build_pyinstaller
    else
      echo "未知打包工具: $BUILDER" >&2
      exit 1
    fi
    ;;
  Darwin|MINGW*|MSYS*|CYGWIN*)
    if [[ "$BUILDER" == "Nuitka" ]]; then
      build_nuitka_other
    elif [[ "$BUILDER" == "PyInstaller" ]]; then
      build_pyinstaller
    else
      echo "未知打包工具: $BUILDER" >&2
      exit 1
    fi
    ;;
  *)
    echo "不支持的系统: $OS" >&2
    exit 1
    ;;
esac

echo "==> dist:"
ls -la dist || true
