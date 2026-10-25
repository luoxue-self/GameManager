"""安全清理本地构建缓存。

默认只删除：
  - build/、dist/
  - .pytest_cache/
  - 递归的 __pycache__/、*.pyc、*.pyo
  - release/ 下的整合包 staging 目录（保留 *.zip）

永远不会动：
  - data/（你的游戏数据、数据库、初始密码）
  - release/*.zip（最终整合包）
  - .git/、源码、虚拟环境

用法：
    python tools/clean.py --dry-run
    python tools/clean.py --yes
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOP_NAMES = ("build", "dist", ".pytest_cache")
SKIP_DIRS = {".git", "data", ".venv", "venv", "release"}


def _size(path: Path) -> int:
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for name in filenames:
            try:
                total += (Path(dirpath) / name).stat().st_size
            except OSError:
                pass
    return total


def collect_targets(root: Path) -> list[Path]:
    """返回要删除的绝对路径列表；不包含 data/ 与 release/*.zip。"""
    root = Path(root)
    targets: list[Path] = []

    for name in TOP_NAMES:
        p = root / name
        if p.is_dir():
            targets.append(p)

    release = root / "release"
    if release.is_dir():
        for p in release.iterdir():
            if p.is_dir() and p.name.startswith("游戏库管理器-v"):
                targets.append(p)

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if "__pycache__" in dirnames:
            targets.append(Path(dirpath) / "__pycache__")
            dirnames.remove("__pycache__")
        for name in filenames:
            if name.endswith((".pyc", ".pyo")):
                targets.append(Path(dirpath) / name)

    # 去掉重复项和“已被父目录覆盖”的子项
    ordered = sorted(set(targets), key=lambda p: len(p.parts))
    result: list[Path] = []
    for path in ordered:
        if any(path == parent or parent in path.parents for parent in result):
            continue
        result.append(path)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="安全清理游戏库管理器的构建缓存")
    parser.add_argument("--dry-run", action="store_true", help="只列出，不删除")
    parser.add_argument("--yes", action="store_true", help="不询问，直接删除")
    args = parser.parse_args(argv)

    targets = collect_targets(ROOT)
    if not targets:
        print("没有需要清理的构建缓存。")
        print("data/ 与 release/*.zip 永远不会被删除。")
        return 0

    total = 0
    print("将清理以下内容：")
    for path in targets:
        size = _size(path)
        total += size
        try:
            rel = path.relative_to(ROOT)
        except ValueError:
            rel = path
        print(f"  {rel}  ({size / 1024 / 1024:.2f} MB)")

    print(f"\n合计约 {total / 1024 / 1024:.2f} MB")
    print("保留：data/、release/*.zip、源码、.git/")
    if args.dry_run:
        print("dry-run：未删除任何内容。")
        return 0
    if not args.yes:
        answer = input("确认删除以上内容？[y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("已取消。")
            return 0

    failed = 0
    for path in targets:
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as exc:
            failed += 1
            print(f"  [跳过] {path}: {exc}")

    print(f"\n清理完成，释放约 {total / 1024 / 1024:.2f} MB。")
    if failed:
        print(f"有 {failed} 项未能删除（可能被占用），可关闭程序后重试。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
