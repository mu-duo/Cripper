"""Test gitignore-style pattern matching for .cripperignore using py_walk."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from py_walk import get_parser_from_file, get_parser_from_list

from cripper.crypto import read_ignore_patterns, is_ignore

FIXTURE = Path(__file__).parent / "fixture"


# ---------------------------------------------------------------------------
# read_ignore_patterns 测试
# ---------------------------------------------------------------------------

def test_read_ignore_patterns_returns_parser():
    """读取 .cripperignore 应返回 Parser 对象"""
    parser = read_ignore_patterns(FIXTURE)
    assert parser is not None
    assert hasattr(parser, "match")


def test_read_ignore_patterns_no_file():
    """不存在 .cripperignore 的目录应返回 None"""
    parser = read_ignore_patterns(FIXTURE / "docs")
    assert parser is None


def test_read_nested_ignore():
    """读取嵌套 .cripperignore"""
    parser = read_ignore_patterns(FIXTURE / "src")
    assert parser is not None
    # src/.cripperignore 包含 *.pyc，应匹配 cache.pyc
    assert parser.match(FIXTURE / "src" / "cache.pyc")
    assert not parser.match(FIXTURE / "src" / "main.py")


# ---------------------------------------------------------------------------
# is_ignore 单元测试 (使用 get_parser_from_list 构建 parser)
# ---------------------------------------------------------------------------

def test_simple_extension():
    """*.log 应匹配任意目录下的 .log 文件"""
    parser = get_parser_from_list(["*.log"], FIXTURE)
    assert is_ignore(FIXTURE / "debug.log", [parser])
    assert is_ignore(FIXTURE / "src" / "debug.log", [parser])
    assert not is_ignore(FIXTURE / "debug.txt", [parser])


def test_negation():
    """! 取反模式应被正确处理"""
    parser = get_parser_from_list(["*.log", "!important.log"], FIXTURE)
    assert is_ignore(FIXTURE / "debug.log", [parser])
    assert not is_ignore(FIXTURE / "important.log", [parser])


def test_cripperignore_always_ignored():
    """.cripperignore 文件始终被忽略"""
    parser = get_parser_from_list([], FIXTURE)
    assert is_ignore(FIXTURE / ".cripperignore", [parser])
    assert is_ignore(FIXTURE / "src" / ".cripperignore", [parser])


def test_no_match():
    """完全不匹配的路径"""
    parser = get_parser_from_list(["*.log", "build/"], FIXTURE)
    assert not is_ignore(FIXTURE / "readme.txt", [parser])
    assert not is_ignore(FIXTURE / "src" / "main.py", [parser])


def test_multiple_parsers():
    """多个 parser 叠加：任一匹配即忽略"""
    p1 = get_parser_from_list(["*.log"], FIXTURE)
    p2 = get_parser_from_list(["build/"], FIXTURE)
    assert is_ignore(FIXTURE / "debug.log", [p1, p2])
    assert is_ignore(FIXTURE / "build", [p1, p2])
    assert not is_ignore(FIXTURE / "readme.txt", [p1, p2])


# ---------------------------------------------------------------------------
# 集成测试 — 模拟 walk_and_add 的遍历行为
# ---------------------------------------------------------------------------

def _build_parsers(dirpath):
    """递归构建所有 .cripperignore 对应的 parser 列表。"""
    parsers = []
    parser = read_ignore_patterns(dirpath)
    if parser is not None:
        parsers.append(parser)
    return parsers


def _walk_and_check(dirpath, root, parsers=None):
    """模拟遍历，返回 (included_files, ignored_files) 两个列表。"""
    if parsers is None:
        parsers = []

    new_parsers = _build_parsers(dirpath)
    parsers = parsers + new_parsers

    included = []
    ignored = []

    try:
        entries = sorted(dirpath.iterdir(), key=lambda p: p.name)
    except PermissionError:
        return included, ignored

    for entry in entries:
        if entry.is_symlink():
            continue
        if is_ignore(entry, parsers):
            ignored.append(entry)
            continue
        if entry.is_dir():
            sub_in, sub_ig = _walk_and_check(entry, root, parsers)
            included.extend(sub_in)
            ignored.extend(sub_ig)
        elif entry.is_file():
            included.append(entry)

    return included, ignored


def test_fixture_included_files():
    """验证应包含的文件"""
    included, ignored = _walk_and_check(FIXTURE, FIXTURE)
    included_rel = sorted(str(p.relative_to(FIXTURE)).replace("\\", "/") for p in included)

    expected = [
        "app.py",
        "docs/readme.txt",
        "important.log",
        "src/lib/util.py",
        "src/main.py",
        "temp_file.txt",
    ]
    assert included_rel == expected, f"Expected {expected}, got {included_rel}"


def test_fixture_ignored_entries():
    """验证应被忽略的条目"""
    included, ignored = _walk_and_check(FIXTURE, FIXTURE)
    ignored_rel = sorted(str(p.relative_to(FIXTURE)).replace("\\", "/") for p in ignored)

    assert "debug.log" in ignored_rel
    assert "error.log" in ignored_rel
    assert "src/cache.pyc" in ignored_rel
    assert "build" in ignored_rel
    assert "dist" in ignored_rel
    assert "docs/temp" in ignored_rel
    assert "node_modules" in ignored_rel
    assert "src/deep/nested/test" in ignored_rel
    assert "src/lib/test" in ignored_rel
    assert "src/temp" in ignored_rel

    # .cripperignore files are always ignored
    assert ".cripperignore" in ignored_rel
    assert "src/.cripperignore" in ignored_rel

    # Files inside ignored dirs should NOT appear (never visited)
    assert "build/output.txt" not in ignored_rel
    assert "dist/bundle.js" not in ignored_rel
    assert "node_modules/some_pkg/index.js" not in ignored_rel
    assert "docs/temp/notes.txt" not in ignored_rel
    assert "src/temp/scratch.txt" not in ignored_rel
    assert "src/lib/test/test_util.py" not in ignored_rel
    assert "src/deep/nested/test/test_deep.py" not in ignored_rel


def test_fixture_ignored_count():
    """验证忽略和包含的数量"""
    included, ignored = _walk_and_check(FIXTURE, FIXTURE)
    assert len(included) == 6, f"Expected 6 included files, got {len(included)}"
    assert len(ignored) == 12, f"Expected 12 ignored entries, got {len(ignored)}"
