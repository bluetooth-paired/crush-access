"""打包交付源码包（不依赖系统 zip 命令）。

用法：python scripts/build_zip.py
输出：dist/crush-access-agent-backend.zip
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

NAME = "crush-access-agent-backend"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / f"{NAME}.zip"

INCLUDE = ["README.md", "pyproject.toml", "uv.lock", ".env.example", "config", "docs", "scripts", "src", "tests"]
SKIP_DIRS = {"__pycache__", ".venv", ".git", "dist", "node_modules", ".pytest_cache", ".idea", ".ruff_cache"}
SKIP_SUFFIX = {".pyc", ".pyo", ".log", ".env"}


def iter_files(base: Path):
    for path in sorted(base.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_dir():
            continue
        if path.suffix in SKIP_SUFFIX or path.name == ".env":
            continue
        yield path


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in INCLUDE:
            target = ROOT / item
            if not target.exists():
                print(f"skip missing: {item}")
                continue
            if target.is_file():
                zf.write(target, f"{NAME}/{item}")
                count += 1
                continue
            for file in iter_files(target):
                zf.write(file, f"{NAME}/{file.relative_to(ROOT).as_posix()}")
                count += 1
    size_mb = OUT.stat().st_size / 1024 / 1024
    print(f"已生成 {OUT}（{count} 个文件，{size_mb:.2f} MB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
