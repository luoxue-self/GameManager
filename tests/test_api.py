import io
import secrets
import zipfile

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import db
from app import app

PASSWORD = "test-pass-123"


def _png(color=(90, 140, 255)):
    buf = io.BytesIO()
    Image.new("RGB", (600, 800), color).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        r = c.post("/api/login",
                   json={"username": "admin", "password": PASSWORD})
        assert r.status_code == 200, r.text
        yield c


def test_anonymous_is_redirected_or_rejected():
    with TestClient(app) as c:
        r = c.get("/api/games")
        assert r.status_code == 401
        r = c.get("/", follow_redirects=False)
        assert r.status_code in (302, 307)
        assert r.headers["location"] == "/login"
        assert c.get("/login").status_code == 200
        # 封面图同样需要登录
        assert c.get("/images/whatever.png").status_code == 401


def test_wrong_password(client):
    r = client.post("/api/login",
                    json={"username": "admin", "password": "wrong-password"})
    assert r.status_code == 401


def test_health(client):
    r = client.get("/api/health")
    body = r.json()
    assert body["ok"] is True
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["cache-control"] == "no-store"


def test_full_crud_flow(client):
    # 清空，保证可重复执行
    for g in client.get("/api/games").json():
        client.delete(f"/api/games/{g['id']}")

    # 新增
    r = client.post("/api/games", json={
        "name": "塞尔达传说：王国之泪", "type": "冒险", "year": 2023,
        "rating": 5, "local_status": "已下载", "location": "D:/Games/Zelda",
        "download_url": "https://example.com/zelda", "how_to": "解压即玩",
    })
    assert r.status_code == 200, r.text
    gid = r.json()["id"]

    # 拼音全拼 / 首字母搜索
    for query in ("saierda", "sedc", "sai er da"):
        hits = client.get("/api/games", params={"q": query}).json()
        assert any(h["name"] == "塞尔达传说：王国之泪"
                   and h["score"] >= 0.9 for h in hits), query

    # 相似名字 → 拦截
    r = client.post("/api/games", json={"name": "塞尔达传说 王国之泪 中文版"})
    assert r.status_code == 409
    cands = r.json()["candidates"]
    assert cands and cands[0]["name"] == "塞尔达传说：王国之泪"

    # force 后入库
    r = client.post("/api/games", json={
        "name": "塞尔达传说 王国之泪 中文版", "force": True})
    assert r.status_code == 200, r.text
    gid2 = r.json()["id"]

    # 空名字 → 400
    assert client.post("/api/games", json={"name": "   "}).status_code == 400

    # 列表 / 模糊搜索
    assert len(client.get("/api/games").json()) == 2
    hits = client.get("/api/games", params={"q": "王国之泪"}).json()
    assert len(hits) == 2
    assert hits[0]["score"] >= 0.85

    # 详情
    g = client.get(f"/api/games/{gid}").json()
    assert g["name"] == "塞尔达传说：王国之泪"
    assert g["year"] == 2023 and g["rating"] == 5.0
    assert client.get("/api/games/999999").status_code == 404

    # 上传封面 → 鉴权访问
    r = client.post("/api/upload",
                    files={"file": ("cover.png", _png(), "image/png")})
    assert r.status_code == 200, r.text
    filename = r.json()["filename"]
    assert client.get(f"/images/{filename}").status_code == 200

    # 非图片文件被拒
    r = client.post("/api/upload",
                    files={"file": ("x.txt", b"not-an-image", "text/plain")})
    assert r.status_code == 400

    # 修改
    r = client.put(f"/api/games/{gid}", json={
        "name": "塞尔达传说：王国之泪", "type": "冒险", "year": 2023,
        "rating": 5, "cover": filename, "local_status": "已下载",
        "saved_at": "2024-05-01T10:00",
        "download_url": "https://example.com/zelda",
        "how_to": "解压即玩", "location": "D:/Games/Zelda",
    })
    assert r.status_code == 200, r.text
    updated = client.get(f"/api/games/{gid}").json()
    assert updated["cover"] == filename
    assert updated["saved_at"] == "2024-05-01 10:00"

    # 全库查重
    groups = client.get("/api/games/duplicates").json()
    assert isinstance(groups, list)
    assert any(len(grp) >= 2 for grp in groups)

    # 编号唯一
    assert client.put(f"/api/games/{gid}", json={
        "name": "塞尔达传说：王国之泪", "code": "C-1"}).status_code == 200
    assert client.put(f"/api/games/{gid2}", json={
        "name": "塞尔达传说 王国之泪 中文版", "code": "C-1"}).status_code == 409

    # 导出
    r = client.get("/api/export/excel")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml")
    xlsx = r.content
    assert len(xlsx) > 5000

    # 导入同一份文件 → 预检全部判重
    r = client.post(
        "/api/import/excel",
        files={"file": ("games.xlsx", xlsx,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"dry_run": "1"})
    assert r.status_code == 200, r.text
    stats = r.json()
    assert stats["total"] == 2 and stats["skipped_dup"] == 2
    assert stats["dry_run"] is True

    # 删除
    assert client.delete(f"/api/games/{gid}").status_code == 200
    assert client.get(f"/api/games/{gid}").status_code == 404
    assert client.delete(f"/api/games/{gid2}").status_code == 200


def test_backup_zip(client):
    for g in client.get("/api/games").json():
        client.delete(f"/api/games/{g['id']}")

    up = client.post("/api/upload",
                     files={"file": ("c.png", _png((20, 160, 120)), "image/png")})
    assert up.status_code == 200
    filename = up.json()["filename"]
    gid = client.post("/api/games",
                      json={"name": "备份测试", "cover": filename}).json()["id"]

    r = client.get("/api/backup")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/zip")
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        names = set(z.namelist())
        assert {"games.db", "README.txt"} <= names
        assert f"images/{filename}" in names
        assert "备份" in z.read("README.txt").decode("utf-8")

    assert client.delete(f"/api/games/{gid}").status_code == 200


def test_corrupt_excel_returns_400(client):
    r = client.post("/api/import/excel",
                    files={"file": ("bad.xlsx", b"this is not an xlsx",
                                    "application/octet-stream")},
                    data={"dry_run": "1"})
    assert r.status_code == 400
    assert "Excel" in r.json()["detail"]


def test_password_change_flow():
    username = "pwuser_" + secrets.token_hex(3)
    con = db.connect()
    con.execute("INSERT INTO users(username,password_hash,created_at) "
                "VALUES(?,?,?)",
                (username, db.hash_pw("old-pass-1"), "2024-01-01"))
    con.commit()
    con.close()

    with TestClient(app) as c:
        assert c.post("/api/login", json={
            "username": username, "password": "old-pass-1"}).status_code == 200

        # 旧密码错误 / 新密码过短
        r = c.post("/api/password", json={
            "old_password": "wrong", "new_password": "new-pass-1"})
        assert r.status_code == 400
        r = c.post("/api/password", json={
            "old_password": "old-pass-1", "new_password": "123"})
        assert r.status_code == 400

        r = c.post("/api/password", json={
            "old_password": "old-pass-1", "new_password": "new-pass-1"})
        assert r.status_code == 200, r.text
        # 当前会话仍有效
        assert c.get("/api/me").status_code == 200

        c.post("/api/logout")
        assert c.post("/api/login", json={
            "username": username, "password": "old-pass-1"}).status_code == 401
        assert c.post("/api/login", json={
            "username": username, "password": "new-pass-1"}).status_code == 200


def test_logout_invalidates_session():
    with TestClient(app) as c:
        assert c.post("/api/login", json={
            "username": "admin", "password": PASSWORD}).status_code == 200
        assert c.get("/api/games").status_code == 200
        assert c.post("/api/logout").status_code == 200
        assert c.get("/api/games").status_code == 401
