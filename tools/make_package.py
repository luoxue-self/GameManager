"""构建「游戏库管理器」整合包：exe + 文档 + 源码，打包成可分发 zip。

用法：
    python tools/build_guide.py       # 先生成 使用指南.html（需要 markdown）
    python tools/make_package.py      # 产物在 release/
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import zipfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist", "游戏库管理器")
RELEASE = os.path.join(ROOT, "release")

SOURCE_FILES = [
    "app.py", "db.py", "dedup.py", "excel_io.py", "desktop.py",
    "build.py", "install.py", "install.bat", "重置密码.bat",
    "requirements.txt", "pyinstaller.spec", ".gitignore", ".gitattributes",
    "LICENSE", "README.md", "IMPLEMENTATION.md", "使用指南.md",
    "使用指南.html", "Game Manager.md",
]
SOURCE_DIRS = ["templates", "assets", "tests", "tools", "docs", ".github"]
PACKAGE_DOCS = [
    "docs/screenshot.png", "docs/screenshot-detail.png",
    "docs/screenshot-edit.png", "docs/screenshot-import.png",
    "docs/screenshot-login.png", "docs/screenshot-settings.png",
    "docs/architecture.png", "docs/完整性检查报告.md",
]
PACKAGE_ROOT_FILES = [
    "使用指南.md", "使用指南.html", "README.md", "LICENSE",
    "重置密码.bat", "docs/完整性检查报告.md",
]

FIRST_RUN = """游戏库管理器 v{version} · 首次启动必读
============================================

1. 双击「游戏库管理器.exe」。
2. 首次启动后，打开 data\\初始密码.txt，用户名是 admin，
   密码就是文件里那一串。
3. 登录后，点右上角 ⚙ → 修改密码。
4. 忘记密码时，双击「重置密码.bat」，按弹窗显示的新密码登录。

详细图文教程：双击「使用指南.html」
数据都在 data 文件夹；备份 / 换电脑时复制整个文件夹即可。

运行环境：Windows 10 1803+ / Windows 11（64 位），需要 WebView2 Runtime。
"""

DATA_NOTE = """这个文件夹保存你的全部游戏数据：
- games.db          游戏库数据库
- images\\           封面图片
- 初始密码.txt       首次启动 / 重置密码时生成
- 启动日志.txt       出问题时的排查日志

备份或换电脑：先关闭程序，复制整个 data 文件夹。
"""


def read_version() -> str:
    with open(os.path.join(ROOT, "app.py"), encoding="utf-8") as f:
        text = f.read()
    m = re.search(r'version="([\d.]+)"', text)
    if not m:
        raise SystemExit("无法从 app.py 读取版本号")
    return m.group(1)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def copy_file(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def copy_tree(src: str, dst: str, ignore_names=("__pycache__", ".pytest_cache")) -> None:
    def ignore(directory, names):
        return [n for n in names if n in ignore_names]

    shutil.copytree(src, dst, ignore=ignore)


def main() -> int:
    version = read_version()
    exe = os.path.join(DIST, "游戏库管理器.exe")
    if not os.path.isfile(exe):
        raise SystemExit("找不到 dist/游戏库管理器/游戏库管理器.exe，请先运行 python build.py")
    if not os.path.isfile(os.path.join(ROOT, "使用指南.html")):
        raise SystemExit("缺少 使用指南.html，请先运行 python tools/build_guide.py")

    pkg_name = f"游戏库管理器-v{version}"
    staging = os.path.join(RELEASE, pkg_name)
    zip_path = os.path.join(RELEASE, pkg_name + "-整合包.zip")
    if os.path.isdir(staging):
        shutil.rmtree(staging)
    os.makedirs(staging, exist_ok=True)

    # 1. 可运行程序
    for name in os.listdir(DIST):
        src = os.path.join(DIST, name)
        dst = os.path.join(staging, name)
        if os.path.isdir(src):
            if name == "data":
                continue      # 不打包运行数据
            copy_tree(src, dst)
        else:
            copy_file(src, dst)

    # 2. 数据目录说明（首次启动自动生成游戏库）
    os.makedirs(os.path.join(staging, "data", "images"), exist_ok=True)
    with open(os.path.join(staging, "data", "说明.txt"), "w", encoding="utf-8") as f:
        f.write(DATA_NOTE)
    with open(os.path.join(staging, "data", "images", ".gitkeep"), "w", encoding="utf-8"):
        pass

    # 3. 文档 / 指南 / 报告 / 重置脚本
    for rel in PACKAGE_ROOT_FILES:
        copy_file(os.path.join(ROOT, rel), os.path.join(staging, os.path.basename(rel)))
    for rel in PACKAGE_DOCS:
        copy_file(os.path.join(ROOT, rel), os.path.join(staging, rel))
    with open(os.path.join(staging, "首次启动必读.txt"), "w", encoding="utf-8") as f:
        f.write(FIRST_RUN.format(version=version))

    # 4. 完整源码
    source_dir = os.path.join(staging, "源码")
    os.makedirs(source_dir, exist_ok=True)
    for name in SOURCE_FILES:
        copy_file(os.path.join(ROOT, name), os.path.join(source_dir, name))
    for name in SOURCE_DIRS:
        copy_tree(os.path.join(ROOT, name), os.path.join(source_dir, name))
    os.makedirs(os.path.join(source_dir, "data"), exist_ok=True)
    with open(os.path.join(source_dir, "data", ".gitkeep"), "w", encoding="utf-8"):
        pass

    # 5. 版本信息
    size = os.path.getsize(exe)
    info = f"""游戏库管理器 整合包
=====================

版本        ：v{version}
构建日期    ：{date.today().isoformat()}
运行平台    ：Windows 10 1803+ / Windows 11（64 位）
运行方式    ：双击 游戏库管理器.exe
首次密码    ：首次启动后见 data/初始密码.txt
数据位置    ：程序同级 data 文件夹（绿色便携）
重置密码    ：双击 重置密码.bat

exe 大小    ：{size:,} 字节
exe SHA256  ：{sha256(exe)}

整合包内容 ：
  游戏库管理器.exe / _internal/   可运行程序
  使用指南.html / 使用指南.md      图文使用说明
  首次启动必读.txt                 三步上手
  重置密码.bat                     忘记密码时使用
  data/                            数据目录（首次启动生成库）
  docs/                            界面截图与架构图
  完整性检查报告.md                本次完整性检查结果
  源码/                            完整源码、测试与构建脚本

源码运行    ：
  cd 源码
  python install.py --mirror auto
  python desktop.py

更多说明见 README.md。
"""
    with open(os.path.join(staging, "版本信息.txt"), "w", encoding="utf-8") as f:
        f.write(info)

    # 6. 打 zip（不包含任何运行时密码 / 数据库）
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, _, files in os.walk(staging):
            for name in files:
                full = os.path.join(folder, name)
                arc = os.path.relpath(full, RELEASE).replace("\\", "/")
                z.write(full, arc)

    forbidden = ("games.db", ".secret", "初始密码.txt", ".venv/")
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
    bad = [n for n in names if any(f in n for f in forbidden)]
    if bad:
        raise SystemExit(f"整合包疑似包含运行数据：{bad}")

    print(f"整合包：{zip_path}")
    print(f"大小  ：{os.path.getsize(zip_path)/1024/1024:.1f} MB")
    print(f"SHA256：{sha256(zip_path)}")
    print(f"文件数：{len(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
