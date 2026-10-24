import dedup


def test_normalize_example_from_spec():
    a = dedup.normalize("塞尔达传说：王国之泪（中文版）")
    b = dedup.normalize("塞尔达传说 王国之泪 v1.2.0")
    assert a == "塞尔达传说王国之泪"
    assert b == "塞尔达传说王国之泪"
    assert dedup.similarity(a, b) >= 0.9


def test_normalize_removes_version_and_noise():
    assert dedup.normalize("艾尔登法环 豪华版（PC版）") == "艾尔登法环"
    assert dedup.normalize("ＢＬＯＯＤＢＯＲＮＥ v1.09") == "bloodborne"
    assert dedup.normalize("") == ""


def test_similarity_bounds():
    assert dedup.similarity("", "abc") == 0.0
    name = dedup.normalize("星露谷物语")
    assert dedup.similarity(name, name) == 1.0


def test_partial_name_is_searchable_but_not_strong_dup():
    short = dedup.normalize("王国之泪")
    full = dedup.normalize("塞尔达传说：王国之泪")
    score = dedup.similarity(short, full)
    assert score >= 0.35        # 搜索能命中
    assert score < 0.85         # 但不该被判为强重复


def test_unrelated_games_score_low():
    a = dedup.normalize("艾尔登法环")
    b = dedup.normalize("星露谷物语")
    assert dedup.similarity(a, b) < 0.6
