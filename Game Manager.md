## 目录

1. 项目简介
    
2. 功能需求清单
    
3. 技术选型
    
4. 系统架构
    
5. 目录结构
    
6. 环境准备
    
7. 阶段一：项目初始化
    
8. 阶段二：数据库层（db.py）
    
9. 阶段三：去重算法（dedup.py）
    
10. 阶段四：Excel 导入导出（excel_io.py）
    
11. 阶段五：Web 后端（app.py）
    
12. 阶段六：Web 前端（templates/）
    
13. 阶段七：桌面封装（desktop.py）
    
14. 阶段八：PyInstaller 打包
    
15. 阶段九：GitHub 开源与 CI
    
16. 测试清单
    
17. 部署与使用
    
18. 常见问题 FAQ
    
19. 后续扩展路线图
    

---

## 1. 项目简介

一个本地优先的游戏资源管理工具，核心能力：

- 管理 12 个字段：游戏名、类型、编号、图片、保存时间、下载链接、使用方法、推荐指数、本地状态、游戏年份、保存位置
    
- **模糊搜索 + 相似去重**（"王国之泪"能搜到"塞尔达传说：王国之泪"）
    
- Excel 双向导入导出（含内嵌图片）
    
- 单机 exe 双击运行 + 网页登录访问两种形态
    
- 数据绿色便携（拷文件夹即迁移）
    

---

## 2. 功能需求清单

|编号|功能|说明|优先级|
|---|---|---|---|
|F01|增删改查|12 个字段完整维护|P0|
|F02|模糊搜索|顶部搜索栏，查重 + 快速定位|P0|
|F03|相似去重|归一化 + 相似度打分 + 分级提示|P0|
|F04|点击图片进详情|卡片封面点击 → 详情弹窗|P0|
|F05|详情内改/删|详情页提供修改和删除入口|P0|
|F06|Excel 导出|含内嵌图片|P1|
|F07|Excel 导入|支持图片（内嵌/压缩包/URL）|P1|
|F08|网页登录|账号密码 + 会话 Cookie|P1|
|F09|桌面 exe|双击即用，绿色便携|P1|
|F10|全库查重|一键找出重复条目|P2|
|F11|GitHub Actions|自动打包 Windows exe|P1|

---

## 3. 技术选型

|层|选型|理由|
|---|---|---|
|后端框架|**FastAPI**|异步、自带 OpenAPI、前后端共用一套|
|数据库|**SQLite**（标准库 sqlite3）|零依赖、单文件、便携|
|桌面外壳|**pywebview**|复用 Web 前端，体积小（30–50MB），跨平台|
|打包|**PyInstaller（onedir）**|启动快、路径稳定；onefile 首次启动慢且易出坑|
|Excel|**openpyxl + Pillow**|读写 xlsx、内嵌图片锚定|
|认证|**itsdangerous 签名 Cookie + scrypt**|无状态、够用、无需引入 JWT 库|
|前端|**原生 HTML/CSS/JS**|无构建步骤、单文件维护、调试简单|
|CI|**GitHub Actions（windows-latest）**|免本地环境打包，产物挂 Release|

---

## 4. 系统架构

text

┌─────────────────────────────────────────────────┐
│                   浏览器 / 桌面窗口               │
│         (templates/login.html + index.html)      │
└────────────────────┬────────────────────────────┘
                     │ HTTP (127.0.0.1 或局域网 IP)
┌────────────────────▼────────────────────────────┐
│                  FastAPI (app.py)                │
│   /api/login  /api/games  /api/export  /api/import│
│                /api/games/{id}                   │
└───┬────────────┬────────────┬────────────────────┘
    │            │            │
┌───▼───┐  ┌────▼────┐  ┌────▼─────────┐
│ db.py │  │dedup.py │  │ excel_io.py  │
│SQLite │  │归一化+   │  │ openpyxl     │
│users  │  │相似度    │  │ + Pillow     │
│games  │  │          │  │              │
└───┬───┘  └─────────┘  └──────┬───────┘
    │                          │
┌───▼──────────────────────────▼───────┐
│   data/  （exe 同级，绿色便携）        │
│   ├── games.db                       │
│   └── images/*.jpg                   │
└──────────────────────────────────────┘

桌面形态：desktop.py 启动 uvicorn 线程 + pywebview 窗口
Web  形态：直接 uvicorn 启动，浏览器访问

**同一套代码两种形态**：`desktop.py` 只是在 `app.py` 外面套了一层窗口，数据库、业务逻辑完全共享。

---

## 5. 目录结构

text

game-manager/
├── desktop.py                 # 桌面入口（阶段七）
├── app.py                     # FastAPI 应用（阶段五）
├── db.py                      # 数据库（阶段二）
├── dedup.py                   # 去重算法（阶段三）
├── excel_io.py                # Excel 导入导出（阶段四）
├── templates/
│   ├── login.html             # 登录页
│   └── index.html             # 主界面（搜索 + 卡片 + 详情）
├── assets/
│   └── icon.ico               # 应用图标（可选）
├── data/                      # 运行时生成，不进 Git
│   ├── games.db
│   └── images/
├── pyinstaller.spec           # 打包配置（阶段八）
├── build.py                   # 本地一键打包
├── requirements.txt
├── .gitignore
├── .github/
│   └── workflows/
│       └── build.yml          # CI（阶段九）
├── IMPLEMENTATION.md          # 本文档
└── README.md                  # 面向用户

---

## 6. 环境准备

### 6.1 本地开发环境

bash

# 要求 Python 3.10+
python --version
# 创建虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
# 安装依赖
pip install -r requirements.txt

`requirements.txt`：

txt

fastapi>=0.110
uvicorn[standard]>=0.27
python-multipart>=0.0.9
pywebview>=4.4
openpyxl>=3.1
pillow>=10.0
itsdangerous>=2.1
pyinstaller>=6.0

### 6.2 系统依赖

|平台|依赖|
|---|---|
|Windows|Edge WebView2 Runtime（Win10 1803+ / Win11 一般自带）|
|macOS|无（用 WKWebView）|
|Linux|`sudo apt install libwebkit2gtk-4.1-dev`|

### 6.3 创建目录骨架

bash

mkdir -p game-manager && cd game-manager
mkdir -p templates assets data/images .github/workflows
touch desktop.py app.py db.py dedup.py excel_io.py \
      requirements.txt .gitignore README.md

---

## 7. 阶段一：项目初始化

### 步骤

1. `git init` 初始化仓库
    
2. 创建 `.gitignore`
    
3. 建好目录骨架（见 6.3）
    

### `.gitignore`

gitignore

# Python
__pycache__/
*.py[cod]
.venv/
venv/
*.egg-info/
# 运行时数据（★重要：不要提交用户数据）
data/
!data/.gitkeep
# 打包产物
build/
dist/
*.spec.bak
# 系统
.DS_Store
Thumbs.db
# 临时
*.log
*.db-journal

### 验证

bash

git status   # 应只看到源码和配置，不含 data/ 与 dist/

---

## 8. 阶段二：数据库层（db.py）

### 目标

- 定义 `users` 和 `games` 两张表
    
- 提供 `connect()`、密码哈希/校验、初始化管理员
- 数据目录由环境变量 `GAME_DATA_DIR` 控制（桌面模式下指向 exe 同级）
    

### 完整代码 `db.py`

python

import os, sqlite3, hashlib, secrets
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
def connect():
    os.makedirs(IMG_DIR, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con
def hash_pw(pw: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt,
                        n=2**14, r=8, p=1, dklen=32)
    return "scrypt$" + salt.hex() + "$" + dk.hex()
def verify_pw(pw: str, stored: str) -> bool:
    try:
        _, salt_hex, dk_hex = stored.split("$")
        dk = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt_hex),
                            n=2**14, r=8, p=1, dklen=32)
        return secrets.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False
def ensure_admin(username="admin", password=None):
    """首次运行创建管理员。密码为 None 时自动生成随机密码并打印。"""
    con = connect()
    if con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
        return
    if password is None:
        password = secrets.token_urlsafe(9)
        print(f"[init] 管理员账号：{username} / {password}（请登录后立即修改）")
    con.execute("INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)",
                (username, hash_pw(password),
                 datetime.now().isoformat(timespec="seconds")))
    con.commit()

### 验证

bash

python -c "import db; db.ensure_admin(); print(db.DB_PATH)"
# 应打印 data/games.db 路径，并在 data/ 下生成 games.db

用 SQLite 客户端打开确认两张表存在。

---

## 9. 阶段三：去重算法（dedup.py）

### 目标

把任意写法归一化成可比较的字符串，再算相似度打分。

### 完整代码 `dedup.py`

python

import re, unicodedata
from difflib import SequenceMatcher
_BRACKET = re.compile(r"[（(\[【〔].*?[)）\]】〕]")
_VER = re.compile(r"\b(v|ver|version|build)\s*[\d._]+", re.I)
_NOISE = re.compile(r"(中文版|汉化版|官方版|豪华版|完整版|年度版|决定版|"
                    r"终极版|重制版|重置版|复刻版|标准版|典藏版|数字版|"
                    r"破解版|绿色版|免安装|整合版|合集|dlc|pc版|安卓版|手机版)", re.I)
_PUNCT = re.compile(r"[^\u4e00-\u9fffa-z0-9]+")
def normalize(name: str) -> str:
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", name).lower()  # 全角转半角 + 小写
    s = _BRACKET.sub(" ", s)                         # 去括号内容
    s = _VER.sub(" ", s)                             # 去版本号
    s = _NOISE.sub(" ", s)                           # 去版本词
    return _PUNCT.sub("", s)                         # 去标点空格
def _bigrams(s):
    return {s[i:i+2] for i in range(len(s)-1)} if len(s) > 1 else ({s} if s else set())
def _jaccard(a, b):
    A, B = _bigrams(a), _bigrams(b)
    return len(A & B) / len(A | B) if A and B else 0.0
def similarity(a: str, b: str) -> float:
    """输入必须已 normalize，返回 0~1"""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    s = 0.6 * _jaccard(a, b) + 0.4 * SequenceMatcher(None, a, b).ratio()
    if a in b or b in a:
        lr = min(len(a), len(b)) / max(len(a), len(b))
        s = max(s, 0.55 + 0.35 * lr)
    return round(s, 4)

### 阈值约定

|分数|含义|行为|
|---|---|---|
|≥ 0.85|强重复|保存时拦截，需人工确认|
|0.60 ~ 0.85|弱相关|提示，不阻塞|
|< 0.60|不相关|不展示|

### 验证

python

from dedup import normalize, similarity
a = normalize("塞尔达传说：王国之泪（中文版）")
b = normalize("塞尔达传说 王国之泪 v1.2.0")
print(a, b, similarity(a, b))   # 应 >= 0.9

---

## 10. 阶段四：Excel 导入导出（excel_io.py）

### 目标

- **导出**：把图片作为浮动对象锚定到「游戏图片」列对应行
    
- **导入**：解析表头、按 anchor 行号回填图片、复用去重逻辑批量入库
    

### 完整代码 `excel_io.py`

python

import os, io, uuid
from openpyxl import Workbook, load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from PIL import Image as PILImage
import dedup
HEADERS = ["游戏名","游戏类型","游戏编号","游戏图片","保存时间","下载链接",
           "使用方法","推荐指数","本地状态","游戏年份","保存位置"]
FIELDS  = ["name","type","code","cover","saved_at","download_url",
           "how_to","rating","local_status","year","location"]
WIDTHS  = [32, 12, 14, 22, 20, 42, 42, 10, 12, 10, 22]
IMG_H   = 90
ROW_PT  = 70
HEADER_ALIAS = {
    "游戏名":"name","名称":"name","游戏名称":"name",
    "游戏类型":"type","类型":"type",
    "游戏编号":"code","编号":"code",
    "游戏图片":"cover","图片":"cover","封面":"cover",
    "保存时间":"saved_at","时间":"saved_at",
    "下载链接":"download_url","链接":"download_url",
    "使用方法":"how_to","说明":"how_to",
    "推荐指数":"rating","评分":"rating",
    "本地状态":"local_status","状态":"local_status",
    "游戏年份":"year","年份":"year",
    "保存位置":"location","位置":"location",
}
# ---------- 导出 ----------
def export_xlsx(rows, img_dir) -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "游戏库"
    ws.append(HEADERS)
    for c in ws[1]:
        c.font = Font(bold=True)
    for i, w in enumerate(WIDTHS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    for r, row in enumerate(rows, 2):
        for c, f in enumerate(FIELDS, 1):
            if f == "cover":
                continue
            ws.cell(r, c, row[f] if row[f] is not None else "")
        cover = (row["cover"] or "").strip()
        if cover and not cover.startswith(("http://", "https://")):
            path = os.path.join(img_dir, cover)
            if os.path.isfile(path):
                try:
                    img = XLImage(path)
                    ratio = IMG_H / img.height
                    img.height = IMG_H
                    img.width = int(img.width * ratio)
                    ws.add_image(img, f"D{r}")
                    ws.row_dimensions[r].height = ROW_PT
                    continue
                except Exception:
                    pass
        ws.cell(r, 4, cover)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
# ---------- 导入 ----------
def _img_bytes(img):
    try:
        return img._data()
    except Exception:
        ref = getattr(img, "ref", None)
        if hasattr(ref, "getvalue"):
            return ref.getvalue()
        if hasattr(ref, "read"):
            pos = ref.tell(); ref.seek(0); d = ref.read(); ref.seek(pos); return d
    return None
def _save_image(data: bytes, img_dir: str) -> str:
    im = PILImage.open(io.BytesIO(data))
    fmt = (im.format or "PNG").lower()
    ext = "jpg" if fmt in ("jpeg", "jpg") else fmt
    fn = f"{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(img_dir, fn), "wb") as f:
        f.write(data)
    return fn
def _num(v, d):
    try: return float(v)
    except Exception: return d
def _int(v):
    try: return int(float(v))
    except Exception: return None
def import_xlsx(xlsx_bytes: bytes, con, img_dir: str,
                zip_images: dict | None = None,
                dry_run: bool = True,
                dup_threshold: float = 0.85) -> dict:
    wb = load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.active
    header = {}
    for col in range(1, ws.max_column + 1):
        v = (ws.cell(1, col).value or "").strip()
        if v in HEADER_ALIAS:
            header[col] = HEADER_ALIAS[v]
    if "name" not in header.values():
        return {"ok": False, "error": "表头缺少『游戏名』列"}
    inline_imgs = {}
    for img in getattr(ws, "_images", []):
        try:
            r = img.anchor._from.row + 1
            data = _img_bytes(img)
            if data:
                inline_imgs.setdefault(r, data)
        except Exception:
            continue
    existing = [(r["id"], r["name"], r["name_norm"])
                for r in con.execute("SELECT id,name,name_norm FROM games")]
    stats = {"total":0,"inserted":0,"skipped_dup":0,
             "skipped_invalid":0,"images":0,"details":[]}
    batch = []
    for r in range(2, ws.max_row + 1):
        data = {}
        for col, field in header.items():
            v = ws.cell(r, col).value
            data[field] = "" if v is None else str(v).strip()
        if not any(data.values()):
            continue
        stats["total"] += 1
        name = data.get("name", "").strip()
        if not name:
            stats["skipped_invalid"] += 1
            stats["details"].append({"row": r, "name": "", "status": "缺游戏名"})
            continue
        norm = dedup.normalize(name)
        hit = None
        for gid, gname, gnorm in existing:
            if gnorm == norm or dedup.similarity(norm, gnorm) >= dup_threshold:
                hit = (gid, gname); break
        if not hit:
            for b in batch:
                if b["name_norm"] == norm or \
                   dedup.similarity(norm, b["name_norm"]) >= dup_threshold:
                    hit = (None, b["name"] + "（本表内）"); break
        if hit:
            stats["skipped_dup"] += 1
            stats["details"].append({"row": r, "name": name,
                                     "status": f"疑似重复 → {hit[1]}"})
            continue
        cover = ""
        if r in inline_imgs:
            cover = "（内嵌）"
            if not dry_run:
                cover = _save_image(inline_imgs[r], img_dir)
            stats["images"] += 1
        else:
            ref = data.get("cover", "")
            if ref and zip_images and ref in zip_images:
                cover = "（zip）"
                if not dry_run:
                    cover = _save_image(zip_images[ref], img_dir)
                stats["images"] += 1
            elif ref.startswith(("http://", "https://")):
                cover = ref
        rec = {
            "name": name, "name_norm": norm, "name_pinyin": "",
            "type": data.get("type",""), "code": data.get("code") or None,
            "cover": cover, "saved_at": data.get("saved_at") or None,
            "download_url": data.get("download_url",""),
            "how_to": data.get("how_to",""),
            "rating": _num(data.get("rating"), 0),
            "local_status": data.get("local_status") or "未下载",
            "year": _int(data.get("year")),
            "location": data.get("location",""),
        }
        batch.append(rec)
        if not dry_run:
            try:
                con.execute("""INSERT INTO games(name,name_norm,name_pinyin,type,code,
                    cover,saved_at,download_url,how_to,rating,local_status,year,location)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (rec["name"], rec["name_norm"], rec["name_pinyin"], rec["type"],
                     rec["code"], rec["cover"], rec["saved_at"], rec["download_url"],
                     rec["how_to"], rec["rating"], rec["local_status"], rec["year"],
                     rec["location"]))
                stats["inserted"] += 1
                stats["details"].append({"row": r, "name": name, "status": "已导入"})
            except Exception as e:
                stats["skipped_invalid"] += 1
                stats["details"].append({"row": r, "name": name, "status": f"失败:{e}"})
        else:
            stats["inserted"] += 1
            stats["details"].append({"row": r, "name": name, "status": "可导入（预检）"})
    if not dry_run:
        con.commit()
    stats["ok"] = True
    stats["dry_run"] = dry_run
    return stats

### 图片导入的三种方式

|方式|Excel 里怎么填|说明|
|---|---|---|
|A 内嵌|图片插入到「游戏图片」列|最常用，按 anchor 行号定位|
|B 文件名|写 `zelda.jpg`，另附压缩包|按文件名匹配 zip|
|C 外链|写 `https://...`|不下载，原样存库|

### 验证

python

import db, excel_io
con = db.connect()
rows = [dict(r) for r in con.execute("SELECT * FROM games")]
buf = excel_io.export_xlsx(rows, db.IMG_DIR)
open("test.xlsx", "wb").write(buf.read())
# 打开 test.xlsx，确认图片在单元格里

---

## 11. 阶段五：Web 后端（app.py）

### 目标

提供 REST API：登录/登出、增删改查、搜索、查重、导入导出。

### 完整代码 `app.py`

python

import os, io, time, zipfile
from datetime import datetime
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import db, dedup, excel_io
SECRET_FILE = os.path.join(db.BASE, ".secret")
if os.path.exists(SECRET_FILE):
    SECRET = open(SECRET_FILE).read().strip()
else:
    SECRET = os.environ.get("GAME_SECRET") or __import__("secrets").token_urlsafe(48)
    try:
        os.makedirs(db.BASE, exist_ok=True)
        open(SECRET_FILE, "w").write(SECRET)
    except Exception:
        pass
serializer = URLSafeTimedSerializer(SECRET, salt="session")
MAX_XLSX = 30 * 1024 * 1024
SESSION_DAYS = 7
app = FastAPI(title="游戏库")
app.mount("/images", StaticFiles(directory=db.IMG_DIR, check_dir=False), name="images")
# ---------- 认证 ----------
def current_user(request: Request) -> str:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(401, "未登录")
    try:
        data = serializer.loads(token, max_age=SESSION_DAYS * 86400)
    except (BadSignature, SignatureExpired):
        raise HTTPException(401, "登录已过期")
    return data["u"]
_fails = {}
def _check_limit(ip):
    rec = _fails.get(ip)
    if rec and time.time() - rec[1] < 300 and rec[0] >= 8:
        raise HTTPException(429, "失败次数过多，请 5 分钟后再试")
@app.post("/api/login")
async def login(request: Request):
    ip = request.client.host if request.client else "?"
    _check_limit(ip)
    body = await request.json()
    u, p = body.get("username",""), body.get("password","")
    con = db.connect()
    row = con.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
    if not row or not db.verify_pw(p, row["password_hash"]):
        rec = _fails.setdefault(ip, [0, time.time()])
        if time.time() - rec[1] > 300:
            rec[:] = [0, time.time()]
        rec[0] += 1
        raise HTTPException(401, "用户名或密码错误")
    _fails.pop(ip, None)
    token = serializer.dumps({"u": u})
    resp = JSONResponse({"ok": True, "username": u})
    resp.set_cookie("session", token, httponly=True, samesite="lax",
                    max_age=SESSION_DAYS * 86400,
                    secure=bool(os.environ.get("HTTPS")))
    return resp
@app.post("/api/logout")
def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("session")
    return resp
@app.get("/api/me")
def me(user: str = Depends(current_user)):
    return {"ok": True, "username": user}
# ---------- 页面 ----------
def _page(name):
    p = os.path.join(os.path.dirname(__file__), "templates", name)
    return HTMLResponse(open(p, encoding="utf-8").read())
@app.get("/login")
def login_page(): return _page("login.html")
@app.get("/")
def index(): return _page("index.html")
# ---------- 查询 ----------
@app.get("/api/games")
def list_games(q: str = "", user: str = Depends(current_user)):
    con = db.connect()
    if q.strip():
        qn = dedup.normalize(q)
        out = []
        for row in con.execute("SELECT * FROM games"):
            s = dedup.similarity(qn, row["name_norm"])
            if s >= 0.35:
                out.append({**dict(row), "score": s})
        out.sort(key=lambda x: -x["score"])
        return out[:50]
    rows = con.execute("SELECT * FROM games ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]
@app.get("/api/games/{gid}")
def get_game(gid: int, user: str = Depends(current_user)):
    con = db.connect()
    row = con.execute("SELECT * FROM games WHERE id=?", (gid,)).fetchone()
    if not row:
        raise HTTPException(404, "不存在")
    return dict(row)
# ---------- 新增 ----------
@app.post("/api/games")
async def add_game(request: Request, user: str = Depends(current_user)):
    data = await request.json()
    force = bool(data.pop("force", False))
    norm = dedup.normalize(data.get("name",""))
    con = db.connect()
    cands = []
    for row in con.execute("SELECT * FROM games"):
        s = dedup.similarity(norm, row["name_norm"])
        if s >= 0.6:
            cands.append({**dict(row), "score": s})
    cands.sort(key=lambda x: -x["score"])
    strong = [c for c in cands if c["score"] >= 0.85]
    if strong and not force:
        return JSONResponse({"ok": False, "reason": "疑似重复",
                             "candidates": strong[:5]}, 409)
    cur = con.execute("""INSERT INTO games(name,name_norm,type,code,cover,saved_at,
        download_url,how_to,rating,local_status,year,location)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (data.get("name",""), norm, data.get("type",""),
         data.get("code") or None, data.get("cover",""),
         data.get("saved_at") or datetime.now().strftime("%Y-%m-%d %H:%M"),
         data.get("download_url",""), data.get("how_to",""),
         float(data.get("rating") or 0),
         data.get("local_status") or "未下载",
         data.get("year") or None, data.get("location","")))
    con.commit()
    return {"ok": True, "id": cur.lastrowid}
# ---------- 修改 ----------
@app.put("/api/games/{gid}")
async def update_game(gid: int, request: Request, user: str = Depends(current_user)):
    data = await request.json()
    norm = dedup.normalize(data.get("name",""))
    con = db.connect()
    con.execute("""UPDATE games SET name=?,name_norm=?,type=?,code=?,cover=?,saved_at=?,
        download_url=?,how_to=?,rating=?,local_status=?,year=?,location=? WHERE id=?""",
        (data.get("name",""), norm, data.get("type",""),
         data.get("code") or None, data.get("cover",""),
         data.get("saved_at"), data.get("download_url",""),
         data.get("how_to",""), float(data.get("rating") or 0),
         data.get("local_status") or "未下载",
         data.get("year") or None, data.get("location",""), gid))
    con.commit()
    return {"ok": True}
# ---------- 删除 ----------
@app.delete("/api/games/{gid}")
def delete_game(gid: int, user: str = Depends(current_user)):
    con = db.connect()
    con.execute("DELETE FROM games WHERE id=?", (gid,))
    con.commit()
    return {"ok": True}
# ---------- 全库查重 ----------
@app.get("/api/games/duplicates")
def duplicates(user: str = Depends(current_user)):
    con = db.connect()
    rows = list(con.execute("SELECT id,name,name_norm FROM games"))
    used, groups = set(), []
    for i, a in enumerate(rows):
        if a["id"] in used: continue
        grp = [dict(a)]
        for b in rows[i+1:]:
            if b["id"] in used: continue
            if dedup.similarity(a["name_norm"], b["name_norm"]) >= 0.85:
                grp.append(dict(b)); used.add(b["id"])
        if len(grp) > 1:
            used.add(a["id"]); groups.append(grp)
    return groups
# ---------- 导出 ----------
@app.get("/api/export/excel")
def export_excel(user: str = Depends(current_user)):
    con = db.connect()
    rows = [dict(r) for r in con.execute("SELECT * FROM games ORDER BY id")]
    buf = excel_io.export_xlsx(rows, db.IMG_DIR)
    fn = f"games_{datetime.now():%Y%m%d_%H%M}.xlsx"
    return StreamingResponse(buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fn}"'})
# ---------- 导入 ----------
@app.post("/api/import/excel")
async def import_excel(file: UploadFile = File(...),
                       images_zip: UploadFile | None = File(None),
                       dry_run: int = Form(1),
                       user: str = Depends(current_user)):
    raw = await file.read()
    if len(raw) > MAX_XLSX:
        raise HTTPException(413, "文件过大")
    zip_imgs = {}
    if images_zip and images_zip.filename:
        zraw = await images_zip.read()
        if len(zraw) > MAX_XLSX:
            raise HTTPException(413, "图片包过大")
        with zipfile.ZipFile(io.BytesIO(zraw)) as z:
            for n in z.namelist():
                if n.lower().endswith((".png",".jpg",".jpeg",".webp",".gif",".bmp")):
                    zip_imgs[os.path.basename(n)] = z.read(n)
    con = db.connect()
    return excel_io.import_xlsx(raw, con, db.IMG_DIR,
                                zip_images=zip_imgs, dry_run=bool(dry_run))
if __name__ == "__main__":
    db.ensure_admin()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

### 验证（Web 模式）

bash

python app.py
# 浏览器打开 http://127.0.0.1:8000/login
# 用终端里打印的随机账号登录

用 curl 或浏览器 DevTools 调 `/api/games` 确认返回 `[]`。

---

## 12. 阶段六：Web 前端（templates/）

### 目标

- 登录页：账号密码 + 错误提示
    
- 主界面：顶部搜索栏 + 卡片网格 + 详情弹窗 + 增删改
    

### `templates/login.html`

html

<!doctype html><html lang="zh"><meta charset="utf-8">
<title>登录 · 游戏库</title>
<style>
body{font:15px system-ui;background:#0f1115;display:grid;place-items:center;
     height:100vh;margin:0;color:#e8eaed}
.box{background:#171a21;padding:28px 32px;border-radius:14px;
     box-shadow:0 8px 30px #0006;width:300px}
input,button{width:100%;padding:10px;margin:6px 0;box-sizing:border-box;
     border:1px solid #2a2f3a;border-radius:9px;background:#1e222b;color:inherit;font:inherit}
button{background:#5b8cff;color:#fff;border:0;cursor:pointer;margin-top:12px}
#msg{color:#ef4444;font-size:13px;min-height:18px}
</style>
<div class="box"><h3 style="margin:0 0 14px">🎮 游戏库登录</h3>
<input id="u" placeholder="用户名" autocomplete="username">
<input id="p" type="password" placeholder="密码" autocomplete="current-password">
<button onclick="go()">登录</button><div id="msg"></div></div>
<script>
async function go(){
  const r = await fetch('/api/login',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({username:u.value,password:p.value})});
  if(r.ok) location.href='/';
  else msg.textContent='登录失败：'+(await r.json()).detail;
}
p.onkeydown = e => e.key==='Enter' && go();
</script></html>

### `templates/index.html`

html

<!doctype html><html lang="zh"><meta charset="utf-8">
<title>游戏管理</title>
<style>
:root{
  --bg:#0f1115; --panel:#171a21; --panel-2:#1e222b;
  --text:#e8eaed; --muted:#8b93a1; --line:#2a2f3a;
  --accent:#5b8cff; --danger:#ef4444; --radius:14px;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
  font:14px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:10;background:rgba(15,17,21,.85);
  backdrop-filter:blur(12px);border-bottom:1px solid var(--line);
  padding:14px 28px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.btn{padding:9px 16px;border-radius:9px;border:1px solid var(--line);
  background:var(--panel);color:var(--text);font:inherit;cursor:pointer}
.btn:hover{background:var(--panel-2)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.search{flex:1;max-width:520px;position:relative;min-width:200px}
.search input{width:100%;padding:11px 16px 11px 42px;border-radius:999px;
  border:1px solid var(--line);background:var(--panel);color:var(--text);
  font:inherit;outline:none;transition:.2s}
.search input:focus{border-color:var(--accent);box-shadow:0 0 0 3px #5b8cff22}
.search::before{content:"⌕";position:absolute;left:16px;top:50%;
  transform:translateY(-52%);color:var(--muted);font-size:18px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));
  gap:22px;padding:24px 28px 48px}
.card{background:var(--panel);border-radius:var(--radius);overflow:hidden;
  cursor:pointer;border:1px solid transparent;
  transition:transform .18s,box-shadow .18s,border-color .18s}
.card:hover{transform:translateY(-5px);box-shadow:0 14px 34px #0008;
  border-color:#ffffff14}
.cover{aspect-ratio:3/4;background:var(--panel-2);overflow:hidden}
.cover img{width:100%;height:100%;object-fit:cover;display:block}
.cover .ph{display:grid;place-items:center;height:100%;color:var(--muted);font-size:12px}
.card-body{padding:12px 14px 14px}
.card-title{font-weight:600;font-size:14px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
  line-clamp:2;overflow:hidden;min-height:2.8em}
.card-meta{display:flex;justify-content:space-between;align-items:center;
  margin-top:8px;color:var(--muted);font-size:12px}
.stars{color:#f5b942;letter-spacing:1px}
.card-actions{display:flex;gap:8px;margin-top:10px;opacity:0;transition:opacity .15s}
.card:hover .card-actions{opacity:1}
.card-actions button{flex:1;padding:7px 0;border-radius:9px;border:1px solid var(--line);
  background:var(--panel-2);color:var(--text);font:inherit;cursor:pointer}
.card-actions .del:hover{background:#3a1a1d;border-color:#7f2a2a;color:#ffb4b4}
.mask{position:fixed;inset:0;background:#0008;display:none;place-items:center;
  z-index:20;padding:20px}
.dialog{background:var(--panel);border-radius:16px;padding:24px;
  width:min(820px,96vw);max-height:90vh;overflow:auto;border:1px solid var(--line)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.grid2 label{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--muted)}
.grid2 input,.grid2 textarea,.grid2 select{padding:9px 11px;border-radius:9px;
  border:1px solid var(--line);background:var(--panel-2);color:var(--text);font:inherit}
.full{grid-column:1/-1}
.kv{display:grid;grid-template-columns:90px 1fr;gap:8px 12px;font-size:13px}
.kv span{color:var(--muted)}
.dup{background:#3a2a1a;border:1px solid #7f5a2a;color:#ffd9a8;
  padding:10px;border-radius:9px;margin:10px 0;font-size:13px}
</style>
<header>
  <b style="font-size:16px">🎮 游戏库</b>
  <div class="search"><input id="q" placeholder="搜索游戏名，查重或快速定位…" autocomplete="off"></div>
  <button class="btn primary" onclick="openEdit()">＋ 新增</button>
  <button class="btn" onclick="exportXlsx()">导出</button>
  <button class="btn" onclick="imp.click()">导入</button>
  <input id="imp" type="file" accept=".xlsx" hidden onchange="doImport(this)">
  <span style="flex:1"></span>
  <span id="who" style="color:var(--muted);font-size:13px"></span>
  <button class="btn" onclick="logout()">退出</button>
</header>
<main class="grid" id="grid"></main>
<div class="mask" id="mask"><div class="dialog" id="dlg"></div></div>
<script>
const $ = s => document.querySelector(s);
let timer, editId = null;
fetch('/api/me').then(r => r.ok ? r.json() : location.href='/login')
  .then(d => who.textContent = d.username + ' ｜');
$('#q').oninput = () => { clearTimeout(timer); timer = setTimeout(load, 280); };
async function load(){
  const q = $('#q').value.trim();
  const rows = await (await fetch('/api/games?q=' + encodeURIComponent(q))).json();
  grid.innerHTML = rows.map(g => `
    <div class="card" onclick="openDetail(${g.id})">
      <div class="cover">${coverHtml(g)}</div>
      <div class="card-body">
        <div class="card-title">${esc(g.name)}</div>
        <div class="card-meta">
          <span>${esc(g.year || '')}</span>
          <span class="stars">${'★'.repeat(Math.round(g.rating||0))}</span>
        </div>
        <div class="card-actions" onclick="event.stopPropagation()">
          <button onclick="openEditById(${g.id})">修改</button>
          <button class="del" onclick="delGame(${g.id},'${escAttr(g.name)}')">删除</button>
        </div>
      </div>
    </div>`).join('');
}
function coverHtml(g){
  if (!g.cover) return `<div class="ph">暂无封面</div>`;
  const src = /^https?:\/\//.test(g.cover) ? g.cover : '/images/' + g.cover;
  return `<img src="${src}" loading="lazy"
    onerror="this.parentNode.innerHTML='<div class=ph>加载失败</div>'">`;
}
function esc(s){ return String(s??'').replace(/[&<>"]/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function escAttr(s){ return esc(s).replace(/'/g, '&#39;'); }
async function openDetail(id){
  const g = await (await fetch('/api/games/' + id)).json();
  const src = g.cover ? (/^https?:/.test(g.cover) ? g.cover : '/images/'+g.cover) : '';
  dlg.innerHTML = `
    <div style="display:grid;grid-template-columns:280px 1fr;gap:22px">
      <div style="border-radius:12px;overflow:hidden;background:var(--panel-2);aspect-ratio:3/4">
        ${src ? `<img src="${src}" style="width:100%;height:100%;object-fit:cover">` : '暂无封面'}
      </div>
      <div>
        <h2 style="margin:0 0 6px;font-size:22px">${esc(g.name)}</h2>
        <div style="color:var(--muted);margin-bottom:16px">
          ${esc(g.type||'—')} ｜ ${esc(g.year||'—')} ｜ 编号 ${esc(g.code||'—')}
        </div>
        <div class="kv">
          <span>推荐指数</span><b>${'★'.repeat(Math.round(g.rating||0))}</b>
          <span>本地状态</span><b>${esc(g.local_status||'—')}</b>
          <span>保存位置</span><b>${esc(g.location||'—')}</b>
          <span>保存时间</span><b>${esc((g.saved_at||'').slice(0,16))}</b>
          <span>下载链接</span><b>${g.download_url
            ? `<a href="${escAttr(g.download_url)}" target="_blank">打开</a>` : '—'}</b>
        </div>
        <div style="margin-top:16px">
          <div style="color:var(--muted);font-size:12px;margin-bottom:4px">使用方法</div>
          <div style="white-space:pre-wrap;background:var(--panel-2);padding:12px;
               border-radius:10px;max-height:160px;overflow:auto">${esc(g.how_to||'暂无')}</div>
        </div>
        <div style="margin-top:22px;display:flex;gap:10px;justify-content:flex-end">
          <button class="btn" onclick="closeDlg()">关闭</button>
          <button class="btn primary" onclick="openEditById(${g.id})">修改</button>
          <button class="btn" style="color:#ffb4b4;border-color:#7f2a2a"
                  onclick="delGame(${g.id},'${escAttr(g.name)}')">删除</button>
        </div>
      </div>
    </div>`;
  mask.style.display = 'grid';
}
async function openEditById(id){
  const g = await (await fetch('/api/games/' + id)).json();
  openEdit(g);
}
function openEdit(g = {}){
  editId = g.id || null;
  dlg.innerHTML = `
    <h3 style="margin:0 0 16px">${editId ? '编辑' : '新增'}游戏</h3>
    <div class="grid2">
      <label>游戏名<input id="f_name" value="${escAttr(g.name||'')}"></label>
      <label>游戏类型<input id="f_type" value="${escAttr(g.type||'')}"></label>
      <label>游戏编号<input id="f_code" value="${escAttr(g.code||'')}"></label>
      <label>游戏年份<input id="f_year" type="number" value="${g.year||''}"></label>
      <label>保存时间<input id="f_saved_at" type="datetime-local"
        value="${g.saved_at ? String(g.saved_at).replace(' ','T').slice(0,16) : ''}"></label>
      <label>推荐指数<input id="f_rating" type="number" step="0.5" min="0" max="5"
        value="${g.rating||''}"></label>
      <label>本地状态<input id="f_local_status" value="${escAttr(g.local_status||'未下载')}"></label>
      <label>保存位置<input id="f_location" value="${escAttr(g.location||'')}"></label>
      <label class="full">下载链接<input id="f_download_url" value="${escAttr(g.download_url||'')}"></label>
      <label class="full">游戏图片（文件名或 URL）<input id="f_cover" value="${escAttr(g.cover||'')}"></label>
      <label class="full">使用方法<textarea id="f_how_to" rows="3">${esc(g.how_to||'')}</textarea></label>
    </div>
    <div id="dupHint"></div>
    <div style="margin-top:16px;text-align:right;display:flex;gap:10px;justify-content:flex-end">
      <button class="btn" onclick="closeDlg()">取消</button>
      <button class="btn primary" onclick="saveGame()">保存</button>
    </div>`;
  mask.style.display = 'grid';
  $('#f_name').focus();
  $('#f_name').onblur = checkDup;
}
async function checkDup(){
  const n = $('#f_name').value.trim();
  if (!n) return;
  const rows = await (await fetch('/api/games?q=' + encodeURIComponent(n))).json();
  const strong = rows.filter(r => r.score >= 0.85 && r.id !== editId);
  dupHint.innerHTML = strong.length
    ? `<div class="dup">⚠ 库中已有相似条目：<b>${strong.map(r=>esc(r.name)).join(' / ')}</b></div>`
    : '';
}
async function saveGame(){
  const body = {};
  for (const k of ['name','type','code','year','saved_at','rating',
                    'local_status','location','download_url','cover','how_to'])
    body[k] = $('#f_'+k).value;
  body.saved_at = body.saved_at ? body.saved_at.replace('T',' ') : null;
  body.force = false;
  const url = editId ? '/api/games/' + editId : '/api/games';
  const method = editId ? 'PUT' : 'POST';
  let r = await fetch(url, {method,
    headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  if (r.status === 409){
    const d = await r.json();
    const names = d.candidates.map(c =>
      `${c.name}（${(c.score*100).toFixed(0)}%）`).join('\n');
    if (confirm('疑似重复：\n' + names + '\n\n仍要保存吗？')){
      body.force = true;
      r = await fetch(url, {method,
        headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
    } else return;
  }
  const d = await r.json();
  if (!d.ok && r.status !== 200) return alert(d.reason || '保存失败');
  closeDlg(); load();
}
async function delGame(id, name){
  if (!confirm(`确定删除「${name}」？此操作不可撤销。`)) return;
  await fetch('/api/games/' + id, {method:'DELETE'});
  closeDlg(); load();
}
function closeDlg(){ mask.style.display = 'none'; }
function exportXlsx(){ location.href = '/api/export/excel'; }
async function doImport(input){
  const f = input.files[0]; if (!f) return;
  const fd1 = new FormData(); fd1.append('file', f); fd1.append('dry_run','1');
  const pre = await (await fetch('/api/import/excel',{method:'POST',body:fd1})).json();
  if (!pre.ok) return alert(pre.error);
  const lines = pre.details.filter(d => d.status !== '已导入').slice(0,20)
    .map(d => `第${d.row}行 ${d.name}：${d.status}`).join('\n');
  const ok = confirm(`预检结果：\n总计 ${pre.total} 行\n可导入 ${pre.inserted} 行\n` +
    `重复跳过 ${pre.skipped_dup} 行\n无效 ${pre.skipped_invalid} 行\n图片 ${pre.images} 张\n\n` +
    (lines ? '问题明细（前20条）：\n' + lines + '\n\n' : '') + '确认执行导入？');
  if (!ok){ input.value=''; return; }
  const fd2 = new FormData(); fd2.append('file', f); fd2.append('dry_run','0');
  const res = await (await fetch('/api/import/excel',{method:'POST',body:fd2})).json();
  alert(`导入完成：新增 ${res.inserted}，跳过重复 ${res.skipped_dup}，图片 ${res.images}`);
  input.value=''; load();
}
async function logout(){
  await fetch('/api/logout',{method:'POST'}); location.href='/login';
}
load();
</script></html>

### 验证

1. 启动 `python app.py`
    
2. 登录 → 新增 3 条游戏（其中两条名字相似）→ 第三条保存时应弹 409 确认框
    
3. 点卡片 → 详情弹窗 → 修改 → 保存 → 列表刷新
    
4. 详情里删除 → 卡片消失
    

---

## 13. 阶段七：桌面封装（desktop.py）

### 目标

后台线程跑 uvicorn → 等端口可连 → 开 pywebview 窗口。

### 完整代码 `desktop.py`

python

import os, sys, time, socket, threading
def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))
BASE_DIR = app_dir()
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(os.path.join(DATA_DIR, "images"), exist_ok=True)
os.environ["GAME_DATA_DIR"] = DATA_DIR
import db
import uvicorn
from app import app
HOST = "127.0.0.1"
START_PORT = 18763
def _port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, port)) != 0
def pick_port(start):
    p = start
    while p < start + 20:
        if _port_free(p): return p
        p += 1
    raise RuntimeError("找不到可用端口")
def start_server(port):
    config = uvicorn.Config(app, host=HOST, port=port, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if not _port_free(port):
            return server
        time.sleep(0.05)
    raise RuntimeError("服务启动超时")
def main():
    db.ensure_admin()
    port = pick_port(START_PORT)
    start_server(port)
    url = f"http://{HOST}:{port}"
    import webview
    webview.create_window(
        "游戏库管理器", url=url,
        width=1360, height=860, min_size=(1100, 700),
        text_select=True, confirm_close=False,
    )
    webview.start(debug=os.environ.get("DEBUG") == "1")
if __name__ == "__main__":
    main()

### 验证

bash

python desktop.py
# 应弹出原生窗口，内容与浏览器一致
# 关闭窗口后进程自动退出

---

## 14. 阶段八：PyInstaller 打包

### 步骤

1. 准备图标 `assets/icon.ico`（256×256，可选）
    
2. 创建 `pyinstaller.spec`
    
3. 创建 `build.py`
    
4. 执行打包
    

### `pyinstaller.spec`

python

# -*- mode: python ; coding: utf-8 -*-
datas = [
    ("templates", "templates"),
    ("assets", "assets"),
]
hiddenimports = [
    "webview.platforms.edgechromium",
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
]
a = Analysis(
    ["desktop.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter","matplotlib","numpy","pandas"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="游戏库管理器",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="assets/icon.ico",
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name="游戏库管理器",
)

> 没有图标就把 `icon="assets/icon.ico"` 一行删掉；`datas` 里的 `assets` 也一并去掉。

### `build.py`

python

import subprocess, sys, os, shutil
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)
    for d in ("build", "dist"):
        shutil.rmtree(d, ignore_errors=True)
    subprocess.run([sys.executable, "-m", "PyInstaller",
                    "pyinstaller.spec", "--noconfirm", "--clean"], check=True)
    out_data = os.path.join("dist", "游戏库管理器", "data", "images")
    os.makedirs(out_data, exist_ok=True)
    print("\n✅ 打包完成：dist/游戏库管理器/")
    print("   整个文件夹拷给用户，双击 exe 即用。")
if __name__ == "__main__":
    main()

### 执行

bash

python build.py

### 产物

text

dist/游戏库管理器/
├── 游戏库管理器.exe
├── _internal/          ← 运行时依赖
└── data/               ← 数据（绿色持久化）
    └── images/

### 验证

1. 双击 `dist/游戏库管理器/游戏库管理器.exe`
    
2. 窗口出现 → 登录 → 增删改查
    
3. 关掉重开 → 数据还在
    
4. 整个文件夹拷到另一台 Win10/11 → 双击 → 数据还在
    

---

## 15. 阶段九：GitHub 开源与 CI

### 15.1 发布前必改

1. **默认管理员密码**：`db.ensure_admin()` 默认随机生成并打印到控制台。桌面 exe 无控制台，建议改为：首次运行时把随机密码写到 `data/初始密码.txt`，登录后提示用户删除。
    
2. **`.secret` 文件**：已在 `app.py` 里持久化到 `data/.secret`，不要提交 Git。
    
3. **`.gitignore`**：确认 `data/`、`dist/`、`build/`、`.venv/` 都在忽略列表。
    

### 15.2 `.github/workflows/build.yml`

yaml

name: Build Windows EXE
on:
  push:
    branches: [ main ]
    tags: [ "v*" ]
  workflow_dispatch:
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Build
        run: python -m PyInstaller pyinstaller.spec --noconfirm --clean
      - name: Prepare data folder
        run: mkdir dist\游戏库管理器\data\images
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: game-manager-windows
          path: dist/游戏库管理器
      - name: Create Release
        if: startsWith(github.ref, 'refs/tags/v')
        uses: softprops/action-gh-release@v2
        with:
          files: dist/游戏库管理器/游戏库管理器.exe
          draft: false

### 15.3 README 模板（面向用户）

markdown

# 🎮 游戏库管理器
本地优先的游戏资源管理工具，支持模糊搜索、相似去重、Excel 导入导出、桌面 exe 双击运行。
## 下载
前往 [Releases](../../releases) 下载最新的 `游戏库管理器.zip`，解压到**桌面或 D 盘**（不要放 `C:\Program Files`），双击 `游戏库管理器.exe`。
> ⚠️ 需要 Windows 10 1803+ / Windows 11（64 位）。
> 如果窗口空白，请安装 [Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)。
## 功能
- 12 字段完整维护
- 顶部搜索栏：模糊匹配 + 查重 + 快速定位
- 点击卡片封面进入详情，详情内可修改/删除
- Excel 导入导出（含内嵌图片）
- 数据在 exe 同级 `data/` 目录，拷文件夹即迁移
## 从源码运行
```bash
pip install -r requirements.txt
python desktop.py          # 桌面窗口
# 或
python app.py              # 网页模式 http://127.0.0.1:8000

首次运行会在终端打印管理员账号密码。

## 打包

bash

python build.py            # 产物在 dist/游戏库管理器/

## 数据备份

整个 `data/` 文件夹就是全部数据。升级程序时**只覆盖 exe 和 `_internal/`，保留 `data/`**。

## License

MIT

text

### 15.4 发版流程
```bash
git add .
git commit -m "feat: initial release"
git tag v1.0.0
git push origin main --tags

Actions 会自动打包并把 exe 挂到 Release。

---

## 16. 测试清单

发版前在一台**没装 Python 的干净 Windows 机器**上按顺序过：

|#|测试项|预期|
|---|---|---|
|1|拷整个文件夹 → 双击 exe|出现登录页|
|2|用初始密码登录|进入主界面|
|3|新增游戏 + 传封面|保存成功，卡片显示封面|
|4|搜索游戏名|命中已有条目，卡片正常|
|5|点卡片封面|详情弹窗全字段正确|
|6|详情里点修改|表单填好，保存后列表更新|
|7|详情里点删除|二次确认后卡片消失|
|8|导出 Excel|图片在单元格里可见|
|9|导入同一份 Excel|预检提示"疑似重复"，执行后不重复入库|
|10|关程序重开|数据还在|
|11|整个文件夹拷到另一台电脑|数据还在|
|12|删掉 `data/` 再启动|自动重建空库|
|13|无 WebView2 的机器|给出可读的错误提示|

---

## 17. 部署与使用

### 17.1 单机（桌面 exe）

- 下载 zip → 解压到可写目录 → 双击 exe
    
- 数据在 `data/`，拷文件夹即迁移
    
- 升级：只覆盖 exe 和 `_internal/`，保留 `data/`
    

### 17.2 局域网共享（Web 模式）

一台机器常驻运行：

bash

python app.py
# 或打包成 exe 但那台机器不关机

局域网其他人浏览器访问 `http://那台机器IP:8000`，走登录页。数据只有一份，天然一致。

### 17.3 公网访问

必须 HTTPS，用 Caddy 一行搞定：

bash

caddy reverse-proxy --from games.example.com --to 127.0.0.1:8000

nginx 反代注意 `client_max_body_size 64m;`。

---

## 18. 常见问题 FAQ

**Q1：双击 exe 窗口空白 / 报错？**  
装 [Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)，重启程序。

**Q2：提示"无法写入 data 目录"？**  
exe 放在了 `C:\Program Files` 等无写权限的位置。移到桌面或 D 盘。

**Q3：杀毒软件报毒？**  
PyInstaller 打包的 exe 常见误报。加白名单，或在 GitHub 上提供源码让用户自己打包。

**Q4：能否直接在 mac/Linux 用？**  
Windows exe 不能。需在对应平台重新打包（pywebview 跨平台，CI 加 runner 即可）。

**Q5：多人同时用一份数据？**  
不要共享 `data/` 文件夹（SQLite 会锁冲突）。改用 Web 模式，一台机器跑服务，其他人浏览器访问。

**Q6：导入 Excel 图片位置错一行？**  
WPS 导出的 xlsx 有时 anchor 偏移。先用「预检」模式核对行号与游戏名，或改用「文件名 + 压缩包」方式导入。

**Q7：怎么备份？**  
整个 `data/` 文件夹就是全部数据；或用「导出 Excel」（图片已内嵌）。

**Q8：忘记管理员密码？**  
删除 `data/games.db` 里的 users 表记录，重启会重新生成。或写个脚本调 `db.ensure_admin("admin","新密码")`。

---

## 19. 后续扩展路线图

|优先级|功能|说明|
|---|---|---|
|P1|图片上传接口|目前靠文件名/URL，加一个 `/api/upload` 支持拖拽上传|
|P1|别名表|解决官方/民间译名差异（"塞尔达" ↔ "Zelda"）|
|P2|拼音搜索|`pypinyin` 存全拼，支持同音错字|
|P2|全库查重 UI|已有 `/api/games/duplicates`，前端加个按钮展示分组|
|P2|多用户隔离|`games` 加 `owner_id`，按用户隔离数据|
|P3|标签系统|多对多标签，替代单一"类型"字段|
|P3|游戏时长记录|开始/结束时间，统计总时长|
|P3|云同步|WebDAV / S3 备份 `data/`|
|P3|语义搜索|引入 embedding 模型做向量召回|

---

**文档结束。** 按阶段 1 → 9 顺序执行，每一步都有验证方法。遇到问题优先查第 18 章 FAQ。