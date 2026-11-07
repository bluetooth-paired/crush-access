#!/usr/bin/env bash
# 打包交付源码包：dist/crush-access-agent-backend.zip
# 不包含 .env、虚拟环境、git 历史、缓存与本地临时文件。
set -euo pipefail

cd "$(dirname "$0")/.."
python scripts/build_zip.py
