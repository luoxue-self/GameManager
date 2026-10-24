"""本地一键打包：python build.py → dist/游戏库管理器/"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)
    for d in ("build", "dist"):
        shutil.rmtree(d, ignore_errors=True)

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("缺少 PyInstaller，请先执行：pip install -r requirements.txt")
        return 1

    print("==> 正在打包（首次约 1~3 分钟）…")
    subprocess.run([sys.executable, "-m", "PyInstaller",
                    "pyinstaller.spec", "--noconfirm", "--clean"], check=True)

    out_data = os.path.join("dist", "游戏库管理器", "data", "images")
    os.makedirs(out_data, exist_ok=True)
    print("\n✅ 打包完成：dist/游戏库管理器/")
    print("   整个文件夹拷给用户，双击 exe 即用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
