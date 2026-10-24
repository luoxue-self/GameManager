# 🎮 游戏库管理器

本地优先（local-first）的游戏资源管理工具：卡片式浏览、模糊搜索、相似去重、Excel 双向导入导出（含内嵌图片），
既可打包成**双击即用的 Windows exe**，也能以**网页登录**的方式在局域网共享。数据全部放在程序同级的 `data/` 文件夹里，拷走即迁移。

![主界面](docs/screenshot.png)

## ✨ 功能

| 功能 | 说明 |
|---|---|
| 完整字段维护 | 游戏名、类型、编号、图片、保存时间、下载链接、使用方法、推荐指数、本地状态、游戏年份、保存位置 |
| 模糊搜索 | 顶部搜索栏，按归一化 + 相似度排序，「王国之泪」能搜到「塞尔达传说：王国之泪」 |
| 相似去重 | 名称归一化 + 相似度打分：≥85% 保存时拦截确认，60%–85% 仅提示 |
| 卡片 → 详情 | 点击卡片查看全部字段，详情内可直接修改 / 删除 |
| 封面图片 | 支持本地上传（自动压缩到长边 1200px）、图片 URL、文件名 |
| Excel 导出 | 图片作为浮动对象内嵌到「游戏图片」列，可直接在 WPS / Excel 里看到 |
| Excel 导入 | 支持内嵌图片、文件名 + zip 图片包、外链三种来源；先预检再入库 |
| 全库查重 | 一键按 ≥85% 相似度分组，点击条目直达详情 |
| 登录保护 | 账号密码 + scrypt 哈希 + itsdangerous 签名 Cookie；同一 IP 连续失败 8 次锁定 5 分钟 |
| 两种形态 | `desktop.py` 原生窗口（pywebview） / `app.py` 网页模式 |
| 绿色便携 | 全部数据在 `data/`，整个文件夹拷贝即迁移 |

<details>
<summary>展开查看详情弹窗</summary>

![详情弹窗](docs/screenshot-detail.png)

</details>

## 🚀 快速开始

### 方式一：下载 exe（普通用户）

1. 到 [Releases](../../releases) 下载最新的 `游戏库管理器.zip`；
2. 解压到**桌面或 D 盘**（不要放 `C:\Program Files` 这类无写权限目录）；
3. 双击 `游戏库管理器.exe`；
4. 首次启动会自动生成管理员账号，密码写在 `data/初始密码.txt`，登录后请修改密码并删除该文件。

> ⚠️ 需要 Windows 10 1803+ / Windows 11（64 位）。
> 如果窗口空白，请安装 [Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) 后重启程序。

### 方式二：从源码运行

要求 Python 3.10+。

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

python desktop.py     # 桌面窗口
# 或
python app.py         # 网页模式：http://127.0.0.1:8000
```

首次运行会在终端打印管理员账号密码，同时写入 `data/初始密码.txt`。

### 局域网 / 公网访问

```bash
python app.py                                   # 0.0.0.0:8000
# 局域网：浏览器访问 http://那台机器的IP:8000
```

公网务必套 HTTPS，例如用 Caddy：

```bash
caddy reverse-proxy --from games.example.com --to 127.0.0.1:8000
```

## 🗂 数据、备份与升级

```
data/
├── games.db          # SQLite：users + games
├── images/           # 封面图片（uuid 命名）
├── .secret           # 会话签名密钥
├── 初始密码.txt       # 仅首次生成时写入，登录后可删除
└── 启动日志.txt       # 桌面入口的启动/异常日志（无控制台 exe 排查用）
```

- **备份**：拷走整个 `data/` 即可；也可以用「导出 Excel」（图片已内嵌）。
- **升级程序**：只覆盖 exe 与 `_internal/`，**保留 `data/`**。
- **迁移电脑**：整个程序文件夹拷到新机器，双击 exe，数据还在。
- ⚠️ 不要多人同时共享同一份 `data/` 文件夹（SQLite 会锁冲突）。多人使用请走 Web 模式，由一台机器常驻服务。

## 📥 Excel 导入格式

导出文件的第一行即标准表头：

```
游戏名 | 游戏类型 | 游戏编号 | 游戏图片 | 保存时间 | 下载链接 | 使用方法 | 推荐指数 | 本地状态 | 游戏年份 | 保存位置
```

导入时兼容这些别名：`名称/游戏名称`、`类型`、`编号`、`图片/封面`、`时间`、`链接`、`说明`、`评分`、`状态`、`年份`、`位置`。
表头可以在前 10 行内任意位置（会自动跳过标题行），但**必须包含「游戏名」列**。

封面有三种来源：

| 方式 | Excel 里怎么填 | 说明 |
|---|---|---|
| A 内嵌 | 图片插入到「游戏图片」列 | 最常用，按图片锚点行号回填 |
| B 文件名 | 写 `zelda.jpg`，同时选择 zip 图片包 | 按文件名匹配压缩包内图片 |
| C 外链 | 写 `https://…` | 不下载，原样存库 |

导入流程分两步：**预检**只统计不写库，确认后再执行。名称相似度 ≥85% 的行会被判重跳过。

> WPS 导出的 xlsx 偶尔出现图片锚点偏移。遇到错行时先用预检核对行号，或改用「文件名 + zip」方式。

## 🔌 API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/login` | 登录，写入会话 Cookie |
| POST | `/api/logout` | 退出登录 |
| GET | `/api/me` | 当前用户 |
| GET | `/api/games?q=` | 列表 / 模糊搜索（带 `score` 相似度） |
| GET | `/api/games/duplicates` | 全库查重分组 |
| GET | `/api/games/{id}` | 详情 |
| POST | `/api/games` | 新增（高度相似会返回 409，可带 `force: true`） |
| PUT | `/api/games/{id}` | 修改（只更新传入字段，相似仅提示） |
| DELETE | `/api/games/{id}` | 删除（同时清理无人引用的封面） |
| POST | `/api/upload` | 上传封面，返回文件名 |
| GET | `/api/export/excel` | 导出 xlsx（含内嵌图片） |
| POST | `/api/import/excel` | 导入 xlsx + 可选 zip 图片包 |
| GET | `/api/health` | 健康检查（桌面端等端口就绪用） |

交互式文档：启动后访问 `http://127.0.0.1:8000/docs`。

## 🧱 技术选型

| 层 | 选型 | 理由 |
|---|---|---|
| 后端 | FastAPI + uvicorn | 异步、自带 OpenAPI，前后端一套 |
| 数据库 | SQLite（标准库 sqlite3） | 零依赖、单文件、便携 |
| 桌面外壳 | pywebview | 复用 Web 前端，体积小 |
| 打包 | PyInstaller（onedir） | 启动快、路径稳定 |
| Excel | openpyxl + Pillow | 读写 xlsx、内嵌图片锚定 |
| 认证 | itsdangerous 签名 Cookie + scrypt | 无状态、够用 |
| 前端 | 原生 HTML/CSS/JS | 无构建步骤、单文件维护 |
| CI | GitHub Actions | 自动测试 + 打包 Windows exe |

## 🏗 架构

![架构图](docs/architecture.png)

- 浏览器 / pywebview 窗口共用同一套 `templates/` 页面，访问同一套 REST API；
- `db.py`（SQLite）、`dedup.py`（归一化 + 相似度）、`excel_io.py`（openpyxl + Pillow）各自独立，方便单测；
- 桌面形态只是在 FastAPI 外面套了一层窗口，数据目录统一由 `GAME_DATA_DIR` 指定。

## 📦 打包

```bash
python build.py            # 产物在 dist/游戏库管理器/
```

> ⚠️ `build.py` 会先清空 `dist/` 再打包。如果 `dist/游戏库管理器/` 里已经在存数据，
> 请先备份 `dist/游戏库管理器/data/`，打包完成后放回。

打包产物：

```
dist/游戏库管理器/
├── 游戏库管理器.exe
├── _internal/          ← 运行时依赖
└── data/               ← 首次运行后生成的数据
    └── images/
```

推送到 `main` 或打 `v*` 标签时，GitHub Actions 会自动测试并打包；打标签还会把 exe 挂到 Release。

## 🧪 测试

```bash
pip install pytest httpx
python -m pytest -q
```

覆盖：归一化 / 相似度阈值、管理员与表结构、编号唯一索引、Excel 导出→清库→导入往返（含内嵌图片）、
zip 图片匹配、缺表头报错、登录鉴权、增删改查、409 判重、上传、查重、导出、导入预检。

## 🛠 目录结构

```
game-manager/
├── desktop.py                 # 桌面入口（uvicorn 线程 + pywebview）
├── app.py                     # FastAPI 应用
├── db.py                      # SQLite / 密码哈希 / 初始管理员
├── dedup.py                   # 归一化 + 相似度
├── excel_io.py                # Excel 导入导出
├── templates/
│   ├── login.html
│   └── index.html
├── assets/icon.ico
├── tests/                     # pytest 用例
├── data/                      # 运行时数据（不进 Git）
├── pyinstaller.spec
├── build.py
├── requirements.txt
├── .github/workflows/build.yml
├── IMPLEMENTATION.md          # 完整实现文档（按阶段）
└── README.md
```

## ❓ 常见问题

**Q：双击 exe 窗口空白 / 报错？**
先看 `data/启动日志.txt` 里记录的异常；窗口空白通常是缺 Edge WebView2 Runtime，安装后重启程序。

**Q：提示「无法写入 data 目录」？**
程序被放在 `C:\Program Files` 等无写权限位置，移到桌面或 D 盘。

**Q：杀毒软件报毒？**
PyInstaller 打包的 exe 常见误报，加白名单，或用源码自行打包。

**Q：忘记管理员密码？**
删除 `data/games.db` 中的 users 记录后重启会重新生成，或执行：
```bash
python -c "import db; db.ensure_admin('admin','新密码')"
```

**Q：能直接在 macOS / Linux 用吗？**
Windows exe 不行；源码可以运行（pywebview 跨平台，Linux 需 `libwebkit2gtk-4.1-dev`），
桌面窗口依赖 `pywebview`，也可只用 `python app.py` 走浏览器。

## 📄 License

MIT
