from pathlib import Path

from tools import clean


def test_collect_targets_never_touches_data_or_release_zip(tmp_path: Path):
    (tmp_path / "build").mkdir()
    (tmp_path / "dist").mkdir()
    (tmp_path / "data" / "images").mkdir(parents=True)
    (tmp_path / "data" / "games.db").write_text("private", encoding="utf-8")
    (tmp_path / "data" / ".secret").write_text("secret", encoding="utf-8")
    (tmp_path / "release").mkdir()
    (tmp_path / "release" / "游戏库管理器-v1.1.1-整合包.zip").write_text(
        "zip", encoding="utf-8")
    (tmp_path / "release" / "游戏库管理器-v1.1.1").mkdir()
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__pycache__").mkdir()
    (tmp_path / "pkg" / "a.pyc").write_text("x", encoding="utf-8")

    targets = clean.collect_targets(tmp_path)
    names = {p.name for p in targets}

    assert "build" in names and "dist" in names
    assert "游戏库管理器-v1.1.1" in names       # staging 目录可以清理
    assert "游戏库管理器-v1.1.1-整合包.zip" not in names
    assert not any("data" in p.parts for p in targets)
    assert all(p.suffix != ".zip" for p in targets)


def test_collect_targets_is_deduplicated(tmp_path: Path):
    cache = tmp_path / "pkg" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "x.pyc").write_text("x", encoding="utf-8")
    targets = clean.collect_targets(tmp_path)
    # 父目录 __pycache__ 会覆盖里面的 .pyc，不会重复列出
    assert targets.count(cache) == 1
    assert all(p.suffix != ".pyc" for p in targets)
