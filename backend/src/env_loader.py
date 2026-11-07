"""项目根目录 `.env` 加载器。

设计目的：让 README 里「cp .env.example .env 后直接启动」在全新虚拟环境中真实可用。

约束：
- 只补充「当前进程尚未设置」的变量（override=False），不覆盖显式传入的环境变量；
- 找不到 `.env` 时静默跳过，绝不因为缺少 `.env` 而启动失败；
- 不打印、不记录任何变量值，避免密钥泄漏；
- 优先使用 python-dotenv（项目依赖），缺失时退化为内置解析，保证独立部署可用。
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_LOADED = False


def _candidate_files() -> list[Path]:
    roots: list[Path] = []
    workspace = os.getenv("COZE_WORKSPACE_PATH")
    if workspace:
        roots.append(Path(workspace))
    here = Path(__file__).resolve()
    roots.extend([here.parent.parent, Path.cwd(), Path.cwd().parent])

    seen: set[Path] = set()
    files: list[Path] = []
    for root in roots:
        candidate = (root / ".env").resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            files.append(candidate)
    return files


def _fallback_load(path: Path) -> None:
    """极简 .env 解析：支持 KEY=VALUE、# 注释、引号包裹。不覆盖已有环境变量。"""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def load_project_env() -> None:
    """幂等地加载项目 `.env`（只在首次调用时真正读取）。"""
    global _LOADED
    if _LOADED:
        return
    _LOADED = True

    path = next(iter(_candidate_files()), None)
    if path is None:
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=False)
        logger.debug("loaded env file: %s", path)
    except Exception:  # noqa: BLE001 - dotenv 缺失或解析失败时退化
        try:
            _fallback_load(path)
            logger.debug("loaded env file (fallback parser): %s", path)
        except Exception as e:  # noqa: BLE001 - .env 损坏不影响启动
            logger.warning("failed to load env file %s: %s", path, type(e).__name__)


__all__ = ["load_project_env"]
