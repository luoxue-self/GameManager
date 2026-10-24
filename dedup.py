"""游戏名归一化 + 相似度打分。

用法：
    a = normalize("塞尔达传说：王国之泪（中文版）")
    b = normalize("塞尔达传说 王国之泪 v1.2.0")
    similarity(a, b)   # 0 ~ 1

阈值约定：
    >= 0.85  强重复，保存时拦截，需人工确认
    0.60~0.85  弱相关，提示但不阻塞
    < 0.60   不相关，不展示
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache

try:  # 可选依赖：没装 pypinyin 时只做中文/英文匹配
    from pypinyin import Style, lazy_pinyin
except Exception:  # pragma: no cover - 取决于部署环境
    Style = None
    lazy_pinyin = None

HAS_PINYIN = lazy_pinyin is not None

_BRACKET = re.compile(r"[（(\[【〔].*?[)）\]】〕]")
_VER = re.compile(r"\b(v|ver|version|build)\s*[\d._]+", re.I)
_NOISE = re.compile(
    r"(中文版|汉化版|官方版|豪华版|完整版|年度版|决定版|"
    r"终极版|重制版|重置版|复刻版|标准版|典藏版|数字版|"
    r"破解版|绿色版|免安装|整合版|合集|dlc|pc版|安卓版|手机版)", re.I)
_PUNCT = re.compile(r"[^\u4e00-\u9fffa-z0-9]+")
_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize(name: str) -> str:
    """全角转半角 + 小写 + 去括号 / 版本号 / 版本词 / 标点空格。"""
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", name).lower()
    s = _BRACKET.sub(" ", s)
    s = _VER.sub(" ", s)
    s = _NOISE.sub(" ", s)
    return _PUNCT.sub("", s)


def _bigrams(s: str) -> set[str]:
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else ({s} if s else set())


def _jaccard(a: str, b: str) -> float:
    A, B = _bigrams(a), _bigrams(b)
    return len(A & B) / len(A | B) if A and B else 0.0


def similarity(a: str, b: str) -> float:
    """输入必须已 normalize，返回 0~1。"""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    s = 0.6 * _jaccard(a, b) + 0.4 * SequenceMatcher(None, a, b).ratio()
    if a in b or b in a:
        lr = min(len(a), len(b)) / max(len(a), len(b))
        s = max(s, 0.55 + 0.35 * lr)
    return round(s, 4)


@lru_cache(maxsize=8192)
def pinyin(name: str) -> tuple[str, str]:
    """返回 (全拼, 拼音首字母)，只保留小写字母和数字。

    例：'塞尔达传说：王国之泪' -> ('saierdachuanshuowangguozhilei', 'sedcswgzl')
    没安装 pypinyin 时返回 ('', '')，此时搜索退化为原来的中文/英文匹配。
    """
    if not name or lazy_pinyin is None:
        return "", ""
    try:
        # 不要用 errors="ignore"：它会把英文/数字整段丢掉
        full = "".join(lazy_pinyin(name)).lower()
        initials = "".join(
            lazy_pinyin(name, style=Style.FIRST_LETTER)).lower()
    except Exception:
        return "", ""
    return _ALNUM.sub("", full), _ALNUM.sub("", initials)


def _row_value(row, key: str) -> str:
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        return ""
    if value is None:
        return ""
    return str(value).strip()


def search_score(q: str, row) -> float:
    """搜索打分：中文/英文相似度 + 拼音全拼 / 首字母匹配。

    row 需要提供 name_norm，另可选 name_pinyin、name_initials。
    """
    qn = normalize(q)
    if not qn:
        return 0.0
    name_norm = _row_value(row, "name_norm")
    score = similarity(qn, name_norm)
    if name_norm and qn in name_norm:
        score = max(score, 0.9)

    # 纯 ASCII 查询才走拼音（中文查询由 similarity 处理）
    pq = _ALNUM.sub("", q.lower())
    py = _row_value(row, "name_pinyin")
    if len(pq) >= 2 and pq.isalnum() and py:
        initials = _row_value(row, "name_initials")
        if pq in py:
            score = max(score, 0.95)
        elif initials and pq in initials:
            score = max(score, 0.92)
        else:
            fuzzy = similarity(pq, py)
            if fuzzy >= 0.75:
                score = max(score, fuzzy)
    return round(score, 4)


def best_match(name: str, rows, threshold: float = 0.85):
    """在 rows（含 name_norm 的序列）中找最相似的一条。

    返回 (row, score) 或 (None, 0.0)。仅用于需要单个最佳命中的场景。
    """
    norm = normalize(name)
    if not norm:
        return None, 0.0
    best, best_score = None, 0.0
    for row in rows:
        score = similarity(norm, row["name_norm"])
        if score > best_score:
            best, best_score = row, score
    if best_score < threshold:
        return None, best_score
    return best, best_score
