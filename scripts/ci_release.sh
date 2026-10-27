#!/usr/bin/env bash
# 标签流水线把 dist 上传到 Package Registry，并建一条 GitLab Release。
# 上传失败时退出非 0。调用方把这个任务标成允许失败，编译产物仍留在流水线里。

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -z "${CI_COMMIT_TAG:-}" ]]; then
  echo "只有标签流水线才发布" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    if [[ "$(id -u)" -eq 0 ]]; then
      apt-get update
      apt-get install -y curl ca-certificates
    else
      sudo apt-get update
      sudo apt-get install -y curl ca-certificates
    fi
  else
    echo "没有 curl，无法上传" >&2
    exit 1
  fi
fi

shopt -s nullglob
files=(dist/*)
if [[ ${#files[@]} -eq 0 ]]; then
  echo "dist 里没有产物" >&2
  exit 1
fi

uploaded=0
for f in "${files[@]}"; do
  [[ -f "$f" ]] || continue
  name="$(basename "$f")"
  echo "==> 上传 $name"
  curl --fail --header "JOB-TOKEN: ${CI_JOB_TOKEN}" \
    --upload-file "$f" \
    "${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/packages/generic/medcode-flow/${CI_COMMIT_TAG}/${name}"
  uploaded=1
done

if [[ "$uploaded" -ne 1 ]]; then
  echo "没有可上传的文件" >&2
  exit 1
fi

curl --fail --header "JOB-TOKEN: ${CI_JOB_TOKEN}" \
  --header "Content-Type: application/json" \
  --data "{\"name\":\"medcode-flow ${CI_COMMIT_TAG}\",\"tag_name\":\"${CI_COMMIT_TAG}\",\"description\":\"安装包在 Package Registry，流水线页面也可以下载。\",\"assets\":{\"links\":[{\"name\":\"Package Registry\",\"url\":\"${CI_PROJECT_URL}/-/packages\"}]}}" \
  "${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/releases"

echo "==> Release ${CI_COMMIT_TAG} 已创建"
