"""数据层：SQLite 建表 / 连接 / 密码哈希 / 初始管理员。

数据目录由环境变量 GAME_DATA_DIR 控制（桌面模式由 desktop.py 指向 exe 同级），
默认是脚本同级的 data/，整个目录拷贝即可迁移。
"""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime

# 数据目录：桌面模式由 desktop.py 注入环境变量；Web 模式默认脚本同级 data/
BASE = os.environ.get("GAME_DATA_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(BASE, "games.db")
IMG_DIR = os.path.join(BASE, "images")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS games(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  name_norm TEXT NOT NULL,
  name_pinyin TEXT DEFAULT '',
  name_initials TEXT DEFAULT '',
  type TEXT DEFAULT '',
  code TEXT,
  cover TEXT DEFAULT '',
  saved_at TEXT,
  download_url TEXT DEFAULT '',
  how_to TEXT DEFAULT '',
  rating REAL DEFAULT 0,
  local_status TEXT DEFAULT '未下载',
  year INTEGER,
  location TEXT DEFAULT '',
  dup_note TEXT DEFAULT ''
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_games_code
  ON games(code) WHERE code IS NOT NULL AND code <> '';
CREATE INDEX IF NOT EXISTS ix_games_norm ON games(name_norm);
"""


def _migrate(con: sqlite3.Connection) -> None:
    """轻量迁移：老版本数据库补上新增列。"""
    cols = {r["name"] for r in con.execute("PRAGMA table_info(games)")}
    if "name_initials" not in cols:
        con.execute("ALTER TABLE games ADD COLUMN name_initials TEXT DEFAULT ''")
        con.commit()


def connect() -> sqlite3.Connection:
    """打开数据库连接（自动建库建表）。每次调用返回新连接，用完即弃。"""
    os.makedirs(IMG_DIR, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)
    _migrate(con)
    return con


def hash_pw(pw: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt,
                        n=2 ** 14, r=8, p=1, dklen=32)
    return "scrypt$" + salt.hex() + "$" + dk.hex()


def verify_pw(pw: str, stored: str) -> bool:
    try:
        _, salt_hex, dk_hex = stored.split("$")
        dk = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt_hex),
                            n=2 ** 14, r=8, p=1, dklen=32)
        return secrets.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def ensure_admin(username="admin", password=None):
    """首次运行创建管理员。密码为 None 时自动生成随机密码。

    自动生成时会打印到控制台，并额外写入 data/初始密码.txt
    （打包成无控制台的 exe 后，用户只能从该文件拿到初始密码）。
    返回 (username, password)；管理员已存在时返回 None。
    """
    con = connect()
    try:
        if con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            return None
        generated = password is None
        if generated:
            password = secrets.token_urlsafe(9)
        con.execute(
            "INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)",
            (username, hash_pw(password),
             datetime.now().isoformat(timespec="seconds")))
        con.commit()
    finally:
        con.close()

    print(f"[init] 管理员账号：{username} / {password}（请登录后立即修改）")
    if generated:
        try:
            os.makedirs(BASE, exist_ok=True)
            note = os.path.join(BASE, "初始密码.txt")
            with open(note, "w", encoding="utf-8") as f:
                f.write(
                    "游戏库管理器 · 初始管理员账号\n"
                    "==============================\n"
                    f"用户名：{username}\n"
                    f"密　码：{password}\n\n"
                    "登录后请尽快修改密码（或用程序重置），并删除本文件。\n")
        except Exception as e:  # 数据目录只读等情况不应阻断启动
            print(f"[warn] 无法写入初始密码文件：{e}")
    return username, password


def now_str() -> str:
    """统一的时间字符串格式（与前端 datetime-local 相容）。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def set_password(username: str, new_password: str) -> bool:
    """修改密码；用户不存在返回 False。"""
    con = connect()
    try:
        cur = con.execute("UPDATE users SET password_hash=? WHERE username=?",
                          (hash_pw(new_password), username))
        con.commit()
        return cur.rowcount > 0
    finally:
        con.close()


if __name__ == "__main__":
    ensure_admin()
    print(DB_PATH)
