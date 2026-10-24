"""桌面入口：后台线程跑 uvicorn → 等端口可连 → 开 pywebview 原生窗口。

数据放在 exe 同级的 data/ 目录，整个文件夹拷走即可迁移。
启动/异常信息写入 data/启动日志.txt（无控制台的 exe 也能排查）。
"""
from __future__ import annotations

import os
import secrets
import socket
import sys
import threading
import time
import traceback
from datetime import datetime

HOST = "127.0.0.1"
START_PORT = 18763


def _log(msg: str) -> None:
    path = os.path.join(DATA_DIR, "启动日志.txt")
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    except Exception:
        pass


def _fatal(msg: str) -> None:
    """打包成无控制台 exe 后，用系统弹窗把错误告诉用户。"""
    try:
        if sys.stderr:  # windowed 模式下 stderr 为 None
            print(msg, file=sys.stderr)
    except Exception:
        pass
    _log("启动失败：" + msg)
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, msg, "游戏库管理器", 0x10)
        except Exception:
            pass


def _info(msg: str) -> None:
    """成功提示：写日志 + 系统弹窗（无控制台的 exe 也能看到）。"""
    try:
        if sys.stdout:
            print(msg)
    except Exception:
        pass
    _log(msg)
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, msg, "游戏库管理器", 0x40)
        except Exception:
            pass


def app_dir() -> str:
    """exe 所在目录；源码运行时为脚本目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = app_dir()
DATA_DIR = os.path.join(BASE_DIR, "data")
try:
    os.makedirs(os.path.join(DATA_DIR, "images"), exist_ok=True)
except OSError as e:
    _fatal(f"无法写入数据目录：\n{DATA_DIR}\n\n请把程序放到桌面或 D 盘等可写位置。\n\n{e}")
    raise SystemExit(1)

# PyInstaller 的 windowed 模式会把 sys.stdout / sys.stderr 置为 None，
# 而 uvicorn 的日志格式化会调用 sys.stdout.isatty()，不兜底会直接启动失败。
if sys.stdout is None or sys.stderr is None:
    try:
        _stream = open(os.path.join(DATA_DIR, "启动日志.txt"), "a",
                       encoding="utf-8", buffering=1)
    except OSError:
        _stream = open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _stream
    if sys.stderr is None:
        sys.stderr = _stream

os.environ["GAME_DATA_DIR"] = DATA_DIR

import db            # noqa: E402
import uvicorn       # noqa: E402
from app import app  # noqa: E402


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, port)) != 0


def pick_port(start: int) -> int:
    for p in range(start, start + 20):
        if _port_free(p):
            return p
    raise RuntimeError("找不到可用端口（18763–18782 都被占用）")


def start_server(port: int):
    config = uvicorn.Config(app, host=HOST, port=port, log_level="warning")
    server = uvicorn.Server(config)

    def _run():
        try:
            server.run()
        except BaseException:
            _log("uvicorn 线程异常：\n" + traceback.format_exc())

    threading.Thread(target=_run, daemon=True, name="uvicorn").start()
    for _ in range(200):
        if not _port_free(port):
            return server
        time.sleep(0.05)
    raise RuntimeError("服务启动超时")


def _open_browser(url: str) -> None:
    import webbrowser
    try:
        webbrowser.open(url)
    except Exception:
        pass


def reset_password(argv: list[str]) -> int:
    """命令行重置管理员密码：--reset-password [新密码]。

    不传新密码时生成随机密码，写入 data/初始密码.txt 并弹窗显示。
    """
    _log("执行密码重置")
    db.ensure_admin()
    new = None
    try:
        idx = argv.index("--reset-password")
        if idx + 1 < len(argv) and not argv[idx + 1].startswith("-"):
            new = argv[idx + 1]
    except ValueError:
        pass
    if new is not None and len(new) < 6:
        _fatal("新密码至少 6 位")
        return 1
    new = new or secrets.token_urlsafe(9)
    if not db.set_password("admin", new):
        _fatal("重置失败：找不到 admin 用户")
        return 1

    note = os.path.join(DATA_DIR, "初始密码.txt")
    try:
        with open(note, "w", encoding="utf-8") as f:
            f.write("游戏库管理器 · 密码已重置\n"
                    "==============================\n"
                    "用户名：admin\n"
                    f"密　码：{new}\n\n"
                    "请登录后到右上角 ⚙ 修改密码。\n")
    except OSError as e:
        _log(f"写入初始密码文件失败：{e}")

    _info(f"管理员密码已重置：{new}\n\n"
          f"已写入 data/初始密码.txt。\n请登录后尽快修改。")
    return 0


def _main() -> int:
    _log(f"启动：frozen={getattr(sys, 'frozen', False)} "
         f"exe={sys.executable} data={DATA_DIR}")
    db.ensure_admin()

    try:
        port = pick_port(START_PORT)
        _log(f"选择端口 {port}")
        start_server(port)
        _log(f"服务已就绪：http://{HOST}:{port}")
    except Exception as e:
        _log("服务启动异常：\n" + traceback.format_exc())
        _fatal(f"服务启动失败：\n{e}")
        return 1

    url = f"http://{HOST}:{port}"
    try:
        import webview
        _log(f"pywebview 导入成功：{getattr(webview, '__file__', '?')}")
    except Exception:
        _log("pywebview 导入失败：\n" + traceback.format_exc())
        _fatal("未能加载桌面窗口组件，改用浏览器打开。\n\n"
               "详情见 data/启动日志.txt")
        _open_browser(url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return 0

    try:
        webview.create_window(
            "游戏库管理器", url=url,
            width=1360, height=860, min_size=(1100, 700),
            text_select=True, confirm_close=False,
        )
        _log("窗口已创建，进入事件循环")
        webview.start(debug=os.environ.get("DEBUG") == "1")
        _log("事件循环结束，程序退出")
    except Exception:
        _log("窗口启动失败：\n" + traceback.format_exc())
        _fatal(
            "桌面窗口启动失败。\n\n"
            "如果是 Windows 10 1803 之前的系统，或窗口为空白，请安装\n"
            "Microsoft Edge WebView2 Runtime 后重试：\n"
            "https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
            "详情见 data/启动日志.txt")
        return 1
    return 0


def main() -> int:
    try:
        if "--reset-password" in sys.argv[1:]:
            return reset_password(sys.argv[1:])
        return _main()
    except SystemExit:
        raise
    except BaseException:
        _log("未捕获异常：\n" + traceback.format_exc())
        _fatal("程序启动失败，详情见 data/启动日志.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())
