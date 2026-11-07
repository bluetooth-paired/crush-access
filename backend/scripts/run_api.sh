#!/usr/bin/env bash
# 启动独立后端服务（本地 / 服务器 / Docker 均可）
# 用法：bash scripts/run_api.sh
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"

# 端口/进程数可从 shell 环境或项目 .env 读取（Python 进程内的 .env 加载在启动之后，故此处单独读）
read_env_value() {
  local key="$1"
  [ -f .env ] || return 0
  grep -E "^[[:space:]]*(export[[:space:]]+)?${key}=" .env | tail -n 1 | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^["'\'']//' -e 's/["'\'']$//'
}

if [ -z "${API_PORT:-}" ]; then
  env_port="$(read_env_value API_PORT || true)"
  API_PORT="${env_port:-8000}"
fi
if [ -z "${API_WORKERS:-}" ]; then
  env_workers="$(read_env_value API_WORKERS || true)"
  API_WORKERS="${env_workers:-1}"
fi

echo "[run_api] starting on 0.0.0.0:${API_PORT} (workers=${API_WORKERS})"

# 优先使用项目虚拟环境，避免「uv sync 后未激活虚拟环境」导致依赖缺失
if [ -z "${PYTHON_BIN:-}" ]; then
  if [ -x ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
  else
    PYTHON_BIN="python"
  fi
fi

exec "${PYTHON_BIN}" -m uvicorn api.app:app --host 0.0.0.0 --port "${API_PORT}" --workers "${API_WORKERS}"
