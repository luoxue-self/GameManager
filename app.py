"""FastAPI 后端：登录 / 增删改查 / 搜索 / 查重 / 图片上传 / Excel 导入导出。

运行：
    python app.py            # http://127.0.0.1:8000
"""
from __future__ import annotations

import io
import os
import secrets
import shutil
import sqlite3
import sys
import tempfile
import time
import traceback
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import (Depends, FastAPI, File, Form, HTTPException, Request,
                     UploadFile)
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               RedirectResponse, StreamingResponse)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from PIL import Image as PILImage
from starlette.background import BackgroundTask

import db
import dedup
import excel_io

# ---------------------------------------------------------------- 基础路径
def _root_dir() -> str:
    """源码运行 = 脚本目录；PyInstaller onedir = _internal 目录。"""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


ROOT = _root_dir()
TEMPLATE_DIR = os.path.join(ROOT, "templates")
ASSET_DIR = os.path.join(ROOT, "assets")

# ---------------------------------------------------------------- 密钥 / 会话
def _load_secret() -> str:
    path = os.path.join(db.BASE, ".secret")
    try:
        with open(path, encoding="utf-8") as f:
            s = f.read().strip()
        if s:
            return s
    except FileNotFoundError:
        pass
    except Exception:
        pass
    s = os.environ.get("GAME_SECRET") or secrets.token_urlsafe(48)
    try:
        os.makedirs(db.BASE, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(s)
    except Exception:
        pass
    return s


SECRET = _load_secret()
serializer = URLSafeTimedSerializer(SECRET, salt="session")
MAX_XLSX = 30 * 1024 * 1024      # 单个 xlsx / zip 上限
MAX_IMAGE = 8 * 1024 * 1024      # 单张封面图上限
MAX_UNZIP = 200 * 1024 * 1024    # 压缩包解压总量上限（防 zip 炸弹）
SESSION_DAYS = 7


@asynccontextmanager
async def lifespan(_app: FastAPI):
    os.makedirs(db.IMG_DIR, exist_ok=True)
    db.ensure_admin()
    _backfill_pinyin()
    yield


def _backfill_pinyin() -> int:
    """给老数据的 name_pinyin / name_initials 补值（一次性迁移）。"""
    if not dedup.HAS_PINYIN:
        return 0
    con = db.connect()
    try:
        rows = con.execute(
            "SELECT id,name FROM games WHERE "
            "name_pinyin IS NULL OR name_pinyin='' OR "
            "name_initials IS NULL OR name_initials=''").fetchall()
        for row in rows:
            full, initials = dedup.pinyin(row["name"])
            con.execute("UPDATE games SET name_pinyin=?, name_initials=? "
                        "WHERE id=?", (full, initials, row["id"]))
        if rows:
            con.commit()
        return len(rows)
    finally:
        con.close()


app = FastAPI(title="游戏库", version="1.1.1", lifespan=lifespan)
os.makedirs(db.IMG_DIR, exist_ok=True)


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    response = await call_next(request)
    if "x-content-type-options" not in response.headers:
        response.headers["X-Content-Type-Options"] = "nosniff"
    if "x-frame-options" not in response.headers:
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
    if "referrer-policy" not in response.headers:
        response.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api/") and \
            "cache-control" not in response.headers:
        response.headers["Cache-Control"] = "no-store"
    return response


# ---------------------------------------------------------------- 认证
def _session_user(request: Request) -> Optional[str]:
    token = request.cookies.get("session")
    if not token:
        return None
    try:
        data = serializer.loads(token, max_age=SESSION_DAYS * 86400)
    except (BadSignature, SignatureExpired):
        return None
    return (data or {}).get("u") or None


def current_user(request: Request) -> str:
    user = _session_user(request)
    if not user:
        raise HTTPException(401, "未登录")
    return user


@app.get("/images/{filename}")
def game_image(filename: str, user: str = Depends(current_user)):
    """封面图也走登录鉴权（原来是公开的 StaticFiles）。"""
    if not filename or filename != os.path.basename(filename) \
            or filename.startswith("."):
        raise HTTPException(404, "图片不存在")
    path = os.path.join(db.IMG_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(404, "图片不存在")
    return FileResponse(path, headers={"Cache-Control": "private, max-age=86400"})


_fails: dict[str, list] = {}
MAX_FAILS = 8
LOCK_SECONDS = 300


def _check_limit(ip: str) -> None:
    rec = _fails.get(ip)
    if rec and time.time() - rec[1] < LOCK_SECONDS and rec[0] >= MAX_FAILS:
        raise HTTPException(429, "失败次数过多，请 5 分钟后再试")


async def _json_body(request: Request) -> dict:
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(400, "请求体必须是 JSON")
    if not isinstance(data, dict):
        raise HTTPException(400, "请求体必须是 JSON 对象")
    return data


@app.post("/api/login")
async def login(request: Request):
    ip = request.client.host if request.client else "?"
    _check_limit(ip)
    body = await _json_body(request)
    username = str(body.get("username") or "").strip()
    password = str(body.get("password") or "")

    con = db.connect()
    try:
        row = con.execute("SELECT * FROM users WHERE username=?",
                          (username,)).fetchone()
    finally:
        con.close()

    if not row or not db.verify_pw(password, row["password_hash"]):
        rec = _fails.setdefault(ip, [0, time.time()])
        if time.time() - rec[1] > LOCK_SECONDS:
            rec[:] = [0, time.time()]
        rec[0] += 1
        raise HTTPException(401, "用户名或密码错误")

    _fails.pop(ip, None)
    token = serializer.dumps({"u": row["username"]})
    resp = JSONResponse({"ok": True, "username": row["username"]})
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
    return {"ok": True, "username": user, "version": app.version}


@app.post("/api/password")
async def change_password(request: Request, user: str = Depends(current_user)):
    body = await _json_body(request)
    old = str(body.get("old_password") or "")
    new = str(body.get("new_password") or "")
    if len(new) < 6:
        raise HTTPException(400, "新密码至少 6 位")
    if new == old:
        raise HTTPException(400, "新密码不能与当前密码相同")

    con = db.connect()
    try:
        row = con.execute("SELECT * FROM users WHERE username=?",
                          (user,)).fetchone()
        if not row or not db.verify_pw(old, row["password_hash"]):
            raise HTTPException(400, "当前密码不正确")
        con.execute("UPDATE users SET password_hash=? WHERE id=?",
                    (db.hash_pw(new), row["id"]))
        con.commit()
    finally:
        con.close()
    return {"ok": True}


@app.get("/api/health")
def health():
    return {"ok": True, "app": "game-manager", "version": app.version}


# ---------------------------------------------------------------- 页面
def _page(name: str) -> HTMLResponse:
    path = os.path.join(TEMPLATE_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(500, f"页面文件缺失：{name}")
    with open(path, encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/")
def index(request: Request):
    if not _session_user(request):
        return RedirectResponse("/login")
    return _page("index.html")


@app.get("/login")
def login_page(request: Request):
    if _session_user(request):
        return RedirectResponse("/")
    return _page("login.html")


@app.get("/favicon.ico")
def favicon():
    path = os.path.join(ASSET_DIR, "icon.ico")
    if os.path.isfile(path):
        return FileResponse(path, media_type="image/x-icon")
    raise HTTPException(404, "无图标")


# ---------------------------------------------------------------- 查询
@app.get("/api/games")
def list_games(q: str = "", user: str = Depends(current_user)):
    con = db.connect()
    try:
        if q.strip():
            out = []
            for row in con.execute("SELECT * FROM games"):
                score = dedup.search_score(q, row)
                if score >= 0.35:
                    out.append({**dict(row), "score": score})
            out.sort(key=lambda x: -x["score"])
            return out[:50]
        rows = con.execute("SELECT * FROM games ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


@app.get("/api/games/duplicates")
def duplicates(user: str = Depends(current_user)):
    """全库查重：按 0.85 阈值把条目分组返回。"""
    con = db.connect()
    try:
        rows = list(con.execute(
            "SELECT id,name,name_norm FROM games ORDER BY id"))
    finally:
        con.close()

    used, groups = set(), []
    for i, a in enumerate(rows):
        if a["id"] in used:
            continue
        group = [{**dict(a), "score": 1.0}]
        for b in rows[i + 1:]:
            if b["id"] in used:
                continue
            score = dedup.similarity(a["name_norm"], b["name_norm"])
            if score >= 0.85:
                group.append({**dict(b), "score": score})
                used.add(b["id"])
        if len(group) > 1:
            used.add(a["id"])
            groups.append(group)
    return groups


@app.get("/api/games/{gid}")
def get_game(gid: int, user: str = Depends(current_user)):
    con = db.connect()
    try:
        row = con.execute("SELECT * FROM games WHERE id=?", (gid,)).fetchone()
    finally:
        con.close()
    if not row:
        raise HTTPException(404, "不存在")
    return dict(row)


# ---------------------------------------------------------------- 写入校验
def _text(v, default: str = "") -> str:
    return default if v is None else str(v).strip()


def _rating(v) -> float:
    try:
        return max(0.0, min(5.0, round(float(v), 1)))
    except (TypeError, ValueError):
        return 0.0


def _year(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _saved_at(v):
    """统一成 YYYY-MM-DD HH:MM（前端 datetime-local 会带 T）。"""
    s = _text(v)
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return s


def _candidates(con, norm: str, exclude_id: int | None = None):
    """返回 (strong, weak)：相似度 >=0.85 的强候选、0.6~0.85 的弱候选。"""
    cands = []
    for row in con.execute("SELECT * FROM games"):
        if exclude_id is not None and row["id"] == exclude_id:
            continue
        score = dedup.similarity(norm, row["name_norm"] or "")
        if score >= 0.6:
            cands.append({**dict(row), "score": score})
    cands.sort(key=lambda x: -x["score"])
    strong = [c for c in cands if c["score"] >= 0.85]
    weak = [c for c in cands if c["score"] < 0.85]
    return strong, weak


def _payload(data: dict) -> dict:
    return {
        "name": _text(data.get("name")),
        "type": _text(data.get("type")),
        "code": _text(data.get("code")) or None,
        "cover": _text(data.get("cover")),
        "saved_at": _saved_at(data.get("saved_at")),
        "download_url": _text(data.get("download_url")),
        "how_to": _text(data.get("how_to")),
        "rating": _rating(data.get("rating")),
        "local_status": _text(data.get("local_status")) or "未下载",
        "year": _year(data.get("year")),
        "location": _text(data.get("location")),
    }


def _dup_response(strong: list) -> JSONResponse:
    return JSONResponse(
        {"ok": False, "reason": "疑似重复",
         "candidates": [{k: v for k, v in c.items() if k != "how_to"}
                        for c in strong[:5]]},
        status_code=409)


# ---------------------------------------------------------------- 新增
@app.post("/api/games")
async def add_game(request: Request, user: str = Depends(current_user)):
    data = await _json_body(request)
    force = bool(data.pop("force", False))
    rec = _payload(data)
    if not rec["name"]:
        raise HTTPException(400, "游戏名不能为空")
    norm = dedup.normalize(rec["name"])
    py_full, py_ini = dedup.pinyin(rec["name"])

    con = db.connect()
    try:
        strong, weak = _candidates(con, norm)
        if strong and not force:
            return _dup_response(strong)
        try:
            cur = con.execute(
                """INSERT INTO games(name,name_norm,name_pinyin,name_initials,
                   type,code,cover,saved_at,download_url,how_to,rating,
                   local_status,year,location)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (rec["name"], norm, py_full, py_ini, rec["type"], rec["code"],
                 rec["cover"], rec["saved_at"] or db.now_str(),
                 rec["download_url"], rec["how_to"], rec["rating"],
                 rec["local_status"], rec["year"], rec["location"]))
            con.commit()
        except sqlite3.IntegrityError:
            con.rollback()
            return JSONResponse(
                {"ok": False, "reason": "游戏编号已被占用，请换一个编号"},
                status_code=409)
        return {"ok": True, "id": cur.lastrowid,
                "warnings": [{"id": w["id"], "name": w["name"],
                              "score": w["score"]} for w in weak[:5]]}
    finally:
        con.close()


# ---------------------------------------------------------------- 修改
GAME_FIELDS = ["name", "type", "code", "cover", "saved_at", "download_url",
               "how_to", "rating", "local_status", "year", "location"]


@app.put("/api/games/{gid}")
async def update_game(gid: int, request: Request,
                      user: str = Depends(current_user)):
    data = await _json_body(request)
    data.pop("force", None)  # 修改不阻塞，兼容前端传来的 force 字段

    con = db.connect()
    try:
        old = con.execute("SELECT * FROM games WHERE id=?", (gid,)).fetchone()
        if not old:
            raise HTTPException(404, "不存在")
        # 只更新请求里带上的字段，没带的保留原值（避免误清空封面等）
        merged = {k: old[k] for k in GAME_FIELDS}
        merged.update({k: v for k, v in data.items() if k in GAME_FIELDS})
        rec = _payload(merged)
        if not rec["name"]:
            raise HTTPException(400, "游戏名不能为空")
        norm = dedup.normalize(rec["name"])
        py_full, py_ini = dedup.pinyin(rec["name"])

        # 修改时只提示相似条目，不阻塞（否则改个说明都要弹确认框）
        strong, weak = _candidates(con, norm, exclude_id=gid)
        warnings = [{"id": c["id"], "name": c["name"], "score": c["score"]}
                    for c in (strong + weak)[:5]]
        try:
            con.execute(
                """UPDATE games SET name=?,name_norm=?,name_pinyin=?,
                   name_initials=?,type=?,code=?,cover=?,saved_at=?,
                   download_url=?,how_to=?,rating=?,local_status=?,year=?,
                   location=? WHERE id=?""",
                (rec["name"], norm, py_full, py_ini, rec["type"], rec["code"],
                 rec["cover"], rec["saved_at"] or old["saved_at"],
                 rec["download_url"], rec["how_to"], rec["rating"],
                 rec["local_status"], rec["year"], rec["location"], gid))
            con.commit()
        except sqlite3.IntegrityError:
            con.rollback()
            return JSONResponse(
                {"ok": False, "reason": "游戏编号已被占用，请换一个编号"},
                status_code=409)
        return {"ok": True, "warnings": warnings}
    finally:
        con.close()


# ---------------------------------------------------------------- 删除
@app.delete("/api/games/{gid}")
def delete_game(gid: int, user: str = Depends(current_user)):
    con = db.connect()
    try:
        row = con.execute("SELECT cover FROM games WHERE id=?",
                          (gid,)).fetchone()
        if not row:
            raise HTTPException(404, "不存在")
        con.execute("DELETE FROM games WHERE id=?", (gid,))
        con.commit()
    finally:
        con.close()
    # 若封面不再被任何条目引用，顺手删掉图片文件（失败不影响结果）
    cover = (row["cover"] or "").strip()
    if cover and not cover.startswith(("http://", "https://")):
        con = db.connect()
        try:
            still = con.execute("SELECT 1 FROM games WHERE cover=?",
                                (cover,)).fetchone()
        finally:
            con.close()
        if not still:
            path = os.path.join(db.IMG_DIR, cover)
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:
                pass
    return {"ok": True}


# ---------------------------------------------------------------- 图片上传
@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...),
                       user: str = Depends(current_user)):
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "空文件")
    if len(raw) > MAX_IMAGE:
        raise HTTPException(413, "图片过大（限 8MB）")
    try:
        PILImage.open(io.BytesIO(raw)).verify()
    except Exception:
        raise HTTPException(400, "不是有效的图片文件")
    try:
        filename = excel_io.save_image_bytes(raw, db.IMG_DIR, max_side=1200)
    except Exception as e:
        raise HTTPException(400, f"图片处理失败：{e}")
    return {"ok": True, "filename": filename, "url": f"/images/{filename}"}


# ---------------------------------------------------------------- 导出
@app.get("/api/export/excel")
def export_excel(user: str = Depends(current_user)):
    con = db.connect()
    try:
        rows = [dict(r) for r in con.execute("SELECT * FROM games ORDER BY id")]
    finally:
        con.close()
    buf = excel_io.export_xlsx(rows, db.IMG_DIR)
    filename = f"games_{datetime.now():%Y%m%d_%H%M}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument"
                   ".spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                 "Content-Length": str(buf.getbuffer().nbytes)})


# ---------------------------------------------------------------- 备份
@app.get("/api/backup")
def backup_data(user: str = Depends(current_user)):
    """把 games.db + images/ 打成 zip（用 SQLite backup API 保证快照一致）。"""
    tmpdir = tempfile.mkdtemp(prefix="gm-backup-")
    db_copy = os.path.join(tmpdir, "games.db")
    zip_path = os.path.join(tmpdir, "backup.zip")
    try:
        con = db.connect()
        dst = sqlite3.connect(db_copy)
        try:
            con.backup(dst)
        finally:
            dst.close()
            con.close()

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(db_copy, "games.db")
            if os.path.isdir(db.IMG_DIR):
                for name in sorted(os.listdir(db.IMG_DIR)):
                    path = os.path.join(db.IMG_DIR, name)
                    if os.path.isfile(path):
                        z.write(path, f"images/{name}")
            z.writestr(
                "README.txt",
                "游戏库管理器数据备份\n\n"
                "恢复方法：关闭程序，把本压缩包里的 games.db 和 images/\n"
                "覆盖到程序同级的 data/ 目录后重新启动。\n")
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(500, f"备份失败：{e}")

    filename = f"game-manager-backup_{datetime.now():%Y%m%d_%H%M}.zip"
    return FileResponse(zip_path, media_type="application/zip",
                        filename=filename,
                        background=BackgroundTask(shutil.rmtree, tmpdir, True))


# ---------------------------------------------------------------- 导入
def _read_zip(raw: bytes) -> dict:
    out: dict[str, bytes] = {}
    total = 0
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = os.path.basename(info.filename)
            if not name.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")):
                continue
            total += info.file_size
            if total > MAX_UNZIP:
                raise HTTPException(413, "图片包解压后过大")
            data = z.read(info)
            if len(data) > MAX_XLSX:
                raise HTTPException(413, "压缩包内单张图片过大")
            out[name] = data
    return out


@app.post("/api/import/excel")
async def import_excel(file: UploadFile = File(...),
                       images_zip: UploadFile | None = File(None),
                       dry_run: int = Form(1),
                       on_dup: str = Form("skip"),
                       user: str = Depends(current_user)):
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "空文件")
    if len(raw) > MAX_XLSX:
        raise HTTPException(413, "文件过大（限 30MB）")
    on_dup = (on_dup or "skip").strip().lower()
    if on_dup not in ("skip", "update"):
        raise HTTPException(400, "on_dup 只能是 skip 或 update")

    zip_imgs: dict = {}
    if images_zip is not None and images_zip.filename:
        zraw = await images_zip.read()
        if len(zraw) > MAX_XLSX:
            raise HTTPException(413, "图片包过大（限 30MB）")
        try:
            zip_imgs = _read_zip(zraw)
        except zipfile.BadZipFile:
            raise HTTPException(400, "图片包不是有效的 zip 文件")

    con = db.connect()
    try:
        result = excel_io.import_xlsx(raw, con, db.IMG_DIR,
                                      zip_images=zip_imgs,
                                      dry_run=bool(int(dry_run)),
                                      on_dup=on_dup)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(400, f"无法解析 Excel 文件：{e}")
    finally:
        con.close()
    if not result.get("ok"):
        raise HTTPException(400, result.get("error") or "导入失败")
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
