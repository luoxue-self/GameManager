"""把 使用指南.md 生成为自包含的 使用指南.html（图片内嵌，双击即读）。

用法：
    pip install markdown
    python tools/build_guide.py
"""
from __future__ import annotations

import base64
import os
import re
from datetime import date

import markdown
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD_PATH = os.path.join(ROOT, "使用指南.md")
OUT_PATH = os.path.join(ROOT, "使用指南.html")
ICON_PATH = os.path.join(ROOT, "assets", "icon.ico")
HERO_IMAGE = "docs/screenshot.png"
VERSION = "1.1.1"


def data_uri(path: str) -> str:
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "gif": "image/gif", "webp": "image/webp", "ico": "image/x-icon"
            }.get(ext, "application/octet-stream")
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def icon_png_data() -> str:
    """把 ico 转成 128px PNG，嵌入页头。"""
    if not os.path.isfile(ICON_PATH):
        return ""
    img = Image.open(ICON_PATH)
    img = img.convert("RGBA").resize((128, 128), Image.LANCZOS)
    import io
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def embed_images(html: str) -> str:
    def repl(match):
        src = match.group(1)
        path = os.path.join(ROOT, src)
        if not os.path.isfile(path):
            return match.group(0)
        return 'src="' + data_uri(path) + '"'

    return re.sub(r'src="([^"]+)"', repl, html)


TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>游戏库管理器 · 使用指南</title>
<style>
  :root{
    --bg:#f5f7fb; --card:#ffffff; --text:#202634; --muted:#667085;
    --line:#e4e9f2; --accent:#3b6df6; --accent-2:#eef3ff;
    --warn-bg:#fff7e8; --warn-line:#f0c36d; --ok:#0f9d76;
    --radius:14px;
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{
    margin:0; background:var(--bg); color:var(--text);
    font:16px/1.75 system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
    -webkit-font-smoothing:antialiased;
  }
  .page{max-width:1080px; margin:0 auto; padding:28px 22px 70px}
  .hero{
    position:relative; overflow:hidden; border-radius:22px; color:#eaf0ff;
    background:radial-gradient(900px 400px at 10% -10%, #3157a8 0%, transparent 60%),
               linear-gradient(135deg, #16223f, #0e1526 70%);
    padding:30px 34px 26px; box-shadow:0 22px 55px #0e152626;
  }
  .hero-top{display:flex; align-items:center; gap:16px; flex-wrap:wrap; justify-content:flex-start}
  .hero-icon{width:64px; height:64px; border-radius:17px; box-shadow:0 8px 24px #0006; margin:0; flex:none}
  .hero h1{margin:0; font-size:30px; letter-spacing:.5px}
  .hero .sub{margin:6px 0 0; color:#b9c8e8; font-size:14.5px}
  .badges{display:flex; gap:8px; flex-wrap:wrap; margin-top:12px}
  .badge{
    font-size:12px; padding:4px 11px; border-radius:999px;
    background:#ffffff14; border:1px solid #ffffff2b; color:#dbe5ff;
  }
  .hero-shot{
    display:block; width:100%; margin-top:22px; border-radius:12px;
    border:1px solid #ffffff22; box-shadow:0 16px 40px #0008;
  }
  .topnav{display:flex; justify-content:space-between; align-items:center;
          gap:12px; flex-wrap:wrap; margin:14px 4px 0; color:var(--muted); font-size:13px}
  .topnav a{color:var(--accent); text-decoration:none}
  .topnav a:hover{text-decoration:underline}
  .toc{
    margin:24px 0 30px; padding:19px 22px; background:var(--card);
    border:1px solid var(--line); border-radius:var(--radius);
    box-shadow:0 4px 18px #1b2b4b0a;
  }
  .toc::before{content:"快速目录"; display:block; font-weight:700; font-size:14px;
               color:var(--muted); letter-spacing:1px; margin-bottom:8px}
  .toc ul{margin:0; padding-left:20px; columns:2; column-gap:34px}
  .toc li{margin:4px 0; break-inside:avoid}
  .toc a{color:var(--text); text-decoration:none}
  .toc a:hover{color:var(--accent)}
  h2{
    font-size:23px; margin:44px 0 14px; padding-left:13px;
    border-left:4px solid var(--accent); line-height:1.35;
  }
  h3{font-size:18px; margin:28px 0 10px; color:#2b3448}
  p{margin:10px 0}
  a{color:var(--accent)}
  ul,ol{padding-left:24px}
  li{margin:5px 0}
  strong{color:#111827}
  blockquote{
    margin:16px 0; padding:13px 16px; border-radius:10px;
    background:var(--accent-2); border-left:4px solid var(--accent);
    color:#33415c;
  }
  blockquote p{margin:4px 0}
  code{
    font-family:ui-monospace,SFMono-Regular,Consolas,monospace;
    font-size:.9em; background:#eef1f7; border:1px solid #e0e6f0;
    border-radius:5px; padding:1px 5px;
  }
  pre{
    background:#0f172a; color:#dbe5ff; padding:15px 17px; border-radius:11px;
    overflow:auto; font-size:13.5px; line-height:1.65;
  }
  pre code{background:none; border:0; padding:0; color:inherit; font-size:inherit}
  table{
    width:100%; border-collapse:collapse; margin:14px 0 18px;
    background:var(--card); font-size:14.5px;
    border:1px solid var(--line); border-radius:10px; overflow:hidden;
  }
  th,td{padding:9px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top}
  th{background:#f0f4fb; color:#33415c; font-weight:600}
  tr:last-child td{border-bottom:0}
  tbody tr:nth-child(even){background:#fafbfe}
  img{max-width:100%; height:auto; display:block; margin:16px auto;
      border-radius:12px; border:1px solid var(--line); box-shadow:0 8px 26px #1b2b4b14}
  hr{border:0; border-top:1px solid var(--line); margin:34px 0}
  .footer{
    margin-top:56px; padding-top:18px; border-top:1px solid var(--line);
    color:var(--muted); font-size:12.5px; display:flex;
    justify-content:space-between; gap:12px; flex-wrap:wrap;
  }
  .backtop{
    position:fixed; right:18px; bottom:18px; z-index:9;
    background:var(--card); border:1px solid var(--line); color:var(--muted);
    border-radius:999px; padding:7px 13px; font-size:12px; text-decoration:none;
    box-shadow:0 8px 20px #1b2b4b14;
  }
  .backtop:hover{color:var(--accent)}
  @media (max-width:760px){
    .page{padding:16px 13px 56px}
    .hero{padding:22px 18px; border-radius:16px}
    .hero h1{font-size:23px}
    .toc ul{columns:1}
    h2{font-size:20px; margin-top:34px}
    table{display:block; overflow-x:auto; white-space:nowrap}
  }
  @media print{
    body{background:#fff}
    .page{max-width:none; padding:0}
    .hero{box-shadow:none; -webkit-print-color-adjust:exact; print-color-adjust:exact}
    .backtop{display:none}
    h2{page-break-after:avoid}
    table,img,pre{page-break-inside:avoid}
  }
</style>
</head>
<body id="top">
<div class="page">
  <header class="hero">
    <div class="hero-top">
      <img class="hero-icon" src="__ICON__" alt="游戏库管理器图标">
      <div>
        <h1>游戏库管理器 · 使用指南</h1>
        <p class="sub">把散落在硬盘、网盘、论坛里的游戏，整理成一张张看得见的卡片。</p>
        <div class="badges">
          <span class="badge">版本 __VERSION__</span>
          <span class="badge">Windows 10 / 11</span>
          <span class="badge">数据保存在本地</span>
          <span class="badge">不需要联网</span>
        </div>
      </div>
    </div>
    <img class="hero-shot" src="__HERO__" alt="游戏库管理器主界面">
  </header>

  <div class="topnav">
    <span>适用版本 __VERSION__ ｜ 最后更新 __DATE__</span>
    <span><a href="#top">回到顶部</a></span>
  </div>

  __BODY__

  <div class="footer">
    <span>游戏库管理器 v__VERSION__ · 本地优先的游戏资源管理工具</span>
    <span>详细开发文档见 README.md</span>
  </div>
</div>
<a class="backtop" href="#top">↑ 顶部</a>
</body>
</html>
"""


def main() -> None:
    with open(MD_PATH, encoding="utf-8") as f:
        md = f.read()

    lines = md.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith("## 1."))
    except StopIteration:
        start = 0
    body_md = "\n".join(lines[start:])

    body = markdown.markdown(
        "[TOC]\n\n" + body_md,
        extensions=["extra", "toc", "sane_lists"],
        extension_configs={"toc": {"toc_depth": "2", "permalink": False}},
    )
    body = embed_images(body)

    html = (TEMPLATE
            .replace("__ICON__", icon_png_data())
            .replace("__HERO__", data_uri(os.path.join(ROOT, HERO_IMAGE)))
            .replace("__BODY__", body)
            .replace("__VERSION__", VERSION)
            .replace("__DATE__", date.today().isoformat()))

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    size = os.path.getsize(OUT_PATH)
    print(f"生成 {OUT_PATH}（{size/1024:.0f} KB）")


if __name__ == "__main__":
    main()
