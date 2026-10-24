"""依赖安装器：自动选择可用的 PyPI 镜像源，安装 requirements.txt。

用法：
    python install.py                          # 自动探测可用镜像
    python install.py --mirror tsinghua        # 指定镜像
    python install.py --mirror aliyun --venv   # 在 .venv 中安装
    python install.py --index-url https://mirror.example.com/pypi/simple
    python install.py --dev --check            # 额外装测试依赖并自检
    python install.py --mirror aliyun --build  # 安装后直接打包 exe

也支持环境变量 PIP_INDEX_URL（--mirror auto 时优先生效）。
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS = os.path.join(ROOT, "requirements.txt")
VENV_DIR = os.path.join(ROOT, ".venv")
DEV_PACKAGES = ["pytest", "httpx"]

# 名称 -> (显示名, simple index URL)
MIRRORS = {
    "aliyun": ("阿里云", "https://mirrors.aliyun.com/pypi/simple"),
    "tsinghua": ("清华 TUNA", "https://pypi.tuna.tsinghua.edu.cn/simple"),
    "ustc": ("中科大", "https://mirrors.ustc.edu.cn/pypi/simple"),
    "tencent": ("腾讯云", "https://mirrors.cloud.tencent.com/pypi/simple"),
    "huawei": ("华为云", "https://repo.huaweicloud.com/repository/pypi/simple"),
    "pypi": ("官方 PyPI", "https://pypi.org/simple"),
}
ORDER = ["aliyun", "tsinghua", "ustc", "tencent", "huawei", "pypi"]
UA = "game-manager-installer/1.0"


# ---------------------------------------------------------------- 镜像选择
def probe(url: str, timeout: float = 4.0) -> bool:
    """探测镜像是否可用：先 HEAD，不行再用 Range GET 读 1KB。"""
    target = url.rstrip("/") + "/pip/"
    for method in ("HEAD", "GET"):
        try:
            headers = {"User-Agent": UA}
            if method == "GET":
                headers["Range"] = "bytes=0-1023"
            req = urllib.request.Request(target, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if method == "GET":
                    resp.read(1024)
                if 200 <= resp.status < 400:
                    return True
        except Exception:
            continue
    return False


def choose_mirror(mirror: str = "auto", index_url: str | None = None,
                  probe_func=probe):
    """返回 (显示名, index URL)。

    index_url 优先；其次指定 mirror；auto 时按 ORDER 依次探测，全挂则回退官方 PyPI。
    """
    if index_url:
        return "自定义镜像", index_url.rstrip("/")
    if mirror and mirror != "auto":
        if mirror not in MIRRORS:
            raise ValueError(f"未知镜像：{mirror}")
        return MIRRORS[mirror]
    for key in ORDER:
        name, url = MIRRORS[key]
        if probe_func(url):
            return name, url
    return MIRRORS["pypi"]


# ---------------------------------------------------------------- 环境 / 命令
def venv_python(path: str) -> str:
    if os.name == "nt":
        return os.path.join(path, "Scripts", "python.exe")
    return os.path.join(path, "bin", "python")


def ensure_venv(path: str) -> str:
    exe = venv_python(path)
    if not os.path.isfile(exe):
        print(f"==> 创建虚拟环境：{path}")
        _run([sys.executable, "-m", "venv", path], check=True)
    return exe


def pip_command(python_exe: str, requirements: str, index: str,
                trusted_host: str | None = None,
                timeout: int = 60) -> list[str]:
    cmd = [python_exe, "-m", "pip", "install",
           "--disable-pip-version-check", "--prefer-binary",
           "--timeout", str(timeout), "--retries", "3",
           "-r", requirements, "-i", index]
    if trusted_host:
        cmd += ["--trusted-host", trusted_host]
    return cmd


def format_cmd(cmd: list[str]) -> str:
    return subprocess.list2cmdline(cmd) if os.name == "nt" else shlex.join(cmd)


def _run(cmd: list[str], **kwargs):
    """执行子进程前先刷新自己的输出，避免日志顺序错乱。"""
    sys.stdout.flush()
    return subprocess.run(cmd, **kwargs)


def save_pip_config(python_exe: str, index: str,
                    trusted_host: str | None = None) -> bool:
    cmds = [[python_exe, "-m", "pip", "config", "set",
             "global.index-url", index]]
    if trusted_host:
        cmds.append([python_exe, "-m", "pip", "config", "set",
                     "global.trusted-host", trusted_host])
    ok = True
    for cmd in cmds:
        print("   " + format_cmd(cmd))
        ok = _run(cmd, cwd=ROOT).returncode == 0 and ok
    if ok:
        print("✅ 已写入当前用户的 pip 配置（其他 Python 项目也会使用）")
    else:
        print("⚠ 写入 pip 配置失败，可稍后手动执行上面的命令")
    return ok


def check_imports(python_exe: str) -> bool:
    core = ("import fastapi, uvicorn, openpyxl, PIL, itsdangerous, "
            "pypinyin; print('核心依赖导入 OK')")
    rc = _run([python_exe, "-c", core], cwd=ROOT).returncode
    if rc != 0:
        return False
    webview = _run(
        [python_exe, "-c", "import webview; print('pywebview 导入 OK')"],
        cwd=ROOT).returncode
    if webview != 0:
        print("⚠ pywebview 导入失败：网页模式仍可用，桌面窗口需要它")
    return True


# ---------------------------------------------------------------- 主流程
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="游戏库管理器 · 依赖安装器（自动选择 PyPI 镜像）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python install.py\n"
            "  python install.py --mirror tsinghua\n"
            "  python install.py --mirror aliyun --venv --dev --check\n"
            "  python install.py --index-url https://mirror.example.com/pypi/simple\n"
            "\n可用镜像：auto、aliyun、tsinghua、ustc、tencent、huawei、pypi"))
    p.add_argument("--mirror", default="auto",
                   choices=["auto"] + list(MIRRORS),
                   help="镜像源，默认 auto（依次探测国内镜像）")
    p.add_argument("--index-url", default=None,
                   help="自定义 simple index URL，优先级最高")
    p.add_argument("--venv", action="store_true",
                   help="在项目下的 .venv 中创建/复用虚拟环境")
    p.add_argument("--dev", action="store_true",
                   help="额外安装 pytest、httpx")
    p.add_argument("--check", action="store_true",
                   help="安装后做依赖导入自检")
    p.add_argument("--build", action="store_true",
                   help="安装完成后执行 build.py 打包 exe")
    p.add_argument("--save-config", action="store_true",
                   help="把镜像写入当前用户的 pip 配置（影响其他项目）")
    p.add_argument("--trusted-host", default=None,
                   help="镜像 HTTPS 证书有问题时传给 pip 的 trusted-host")
    p.add_argument("--timeout", type=int, default=60,
                   help="pip 网络超时秒数，默认 60")
    p.add_argument("--dry-run", action="store_true",
                   help="只打印将执行的命令，不真正安装")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not os.path.isfile(REQUIREMENTS):
        print(f"找不到 {REQUIREMENTS}")
        return 1

    print("=" * 64)
    print("游戏库管理器 · 依赖安装")
    print("=" * 64)

    python_exe = sys.executable
    if args.venv:
        if args.dry_run:
            python_exe = venv_python(VENV_DIR)
            print(f"虚拟环境（dry-run 不创建）：{VENV_DIR}")
        else:
            try:
                python_exe = ensure_venv(VENV_DIR)
            except subprocess.CalledProcessError as e:
                print(f"创建虚拟环境失败：{e}")
                return 1
            print(f"虚拟环境：{VENV_DIR}")

    index_url = args.index_url
    if not index_url and args.mirror == "auto" and os.environ.get("PIP_INDEX_URL"):
        index_url = os.environ["PIP_INDEX_URL"]
        print("使用环境变量 PIP_INDEX_URL")

    try:
        name, index = choose_mirror(args.mirror, index_url)
    except ValueError as e:
        print(e)
        return 1

    trusted = args.trusted_host
    if index.startswith("http://") and not trusted:
        trusted = urllib.parse.urlsplit(index).hostname
        print("⚠ 使用 HTTP 镜像，已自动添加 --trusted-host")

    # 指定镜像但探测失败时给个提醒，仍尊重用户选择
    if args.mirror != "auto" and not index_url and not args.dry_run:
        if not probe(index):
            print(f"⚠ 镜像「{name}」当前探测不可达，仍按指定源安装；"
                  f"可改用 --mirror auto")

    print(f"Python ：{python_exe}")
    print(f"镜像  ：{name}")
    print(f"地址  ：{index}")
    print(f"依赖  ：{REQUIREMENTS}")
    if args.dry_run:
        print("模式  ：dry-run（只打印，不执行）")

    cmd = pip_command(python_exe, REQUIREMENTS, index, trusted, args.timeout)
    print("\n==> 安装依赖")
    print("   " + format_cmd(cmd))
    if args.dry_run:
        print("\n（dry-run）已跳过实际安装。")
        return 0

    rc = _run(cmd, cwd=ROOT).returncode
    if rc != 0:
        print("\n❌ 依赖安装失败。可尝试：")
        print("   python install.py --venv --mirror aliyun   # 改用独立虚拟环境")
        print("   python install.py --mirror pypi             # 换官方源")
        print(f"   python install.py --trusted-host "
              f"{urllib.parse.urlsplit(index).hostname}")
        print("   python install.py --index-url https://你的镜像/simple")
        return rc

    if args.save_config:
        save_pip_config(python_exe, index, trusted)

    if args.dev:
        dev_cmd = [python_exe, "-m", "pip", "install",
                   "--disable-pip-version-check", "--prefer-binary",
                   "--timeout", str(args.timeout), "-i", index]
        if trusted:
            dev_cmd += ["--trusted-host", trusted]
        dev_cmd += DEV_PACKAGES
        print("\n==> 安装开发依赖")
        print("   " + format_cmd(dev_cmd))
        if _run(dev_cmd, cwd=ROOT).returncode != 0:
            print("❌ 开发依赖安装失败")
            return 1

    if args.check:
        print("\n==> 导入自检")
        if not check_imports(python_exe):
            print("❌ 核心依赖导入失败")
            return 1

    if args.build:
        print("\n==> 打包 exe")
        if _run([python_exe, os.path.join(ROOT, "build.py")],
                cwd=ROOT).returncode != 0:
            print("❌ 打包失败")
            return 1
        print("产物：dist/游戏库管理器/")

    print("\n✅ 依赖安装完成")
    if args.venv:
        if os.name == "nt":
            print("   激活虚拟环境：.venv\\Scripts\\activate")
        else:
            print("   激活虚拟环境：source .venv/bin/activate")
    print("   桌面窗口：python desktop.py")
    print("   网页模式：python app.py   # http://127.0.0.1:8000")
    if not args.dev:
        print("   运行测试：python install.py --dev 后执行 python -m pytest -q")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
