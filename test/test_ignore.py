"""Test gitignore-style pattern matching for .cripperignore."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cripper.crypto import matches_pattern, read_ignore_patterns, need_ignore

FIXTURE = Path(__file__).parent / "fixture"


# ---------------------------------------------------------------------------
# matches_pattern 单元测试
# ---------------------------------------------------------------------------

def test_simple_extension():
    """裸扩展名匹配：*.log 匹配任意目录下的 .log 文件"""
    assert matches_pattern("debug.log", "*.log")
    assert matches_pattern("src/debug.log", "*.log")
    assert not matches_pattern("debug.txt", "*.log")


def test_negation():
    """! 取反由 need_ignore 层处理，matches_pattern 不关心 !"""
    assert matches_pattern("important.log", "*.log")  # 模式匹配
    # ! 前缀在 read_ignore_patterns 中被剥离


def test_directory_only():
    """以 / 结尾的模式只匹配目录（由 need_ignore 层检查 is_dir）"""
    assert matches_pattern("build", "build/")
    assert matches_pattern("src/build", "build/")
    # 文件不应匹配 dir-only 模式（在 need_ignore 中检查）


def test_double_star_any_depth():
    """**/temp 匹配任意深度的 temp"""
    assert matches_pattern("temp", "**/temp")
    assert matches_pattern("src/temp", "**/temp")
    assert matches_pattern("a/b/c/temp", "**/temp")
    # 仅匹配名为 temp 的条目，不匹配 temp_something
    assert not matches_pattern("temp_file", "**/temp")


def test_double_star_middle():
    """src/**/test 匹配 src 下任意深度的 test"""
    assert matches_pattern("src/test", "src/**/test")
    assert matches_pattern("src/lib/test", "src/**/test")
    assert matches_pattern("src/deep/nested/test", "src/**/test")
    assert not matches_pattern("other/test", "src/**/test")


def test_anchored_slash():
    """以 / 开头的模式锚定到 .cripperignore 所在目录"""
    assert matches_pattern("node_modules", "/node_modules/")
    assert not matches_pattern("src/node_modules", "/node_modules/")


def test_filename_only():
    """不含 / 的模式只匹配文件名，不关心路径"""
    assert matches_pattern("foo/bar/app.py", "app.py")
    assert matches_pattern("app.py", "app.py")
    assert not matches_pattern("foo/bar/main.py", "app.py")


def test_path_specific():
    """含 / 的模式匹配相对于 .cripperignore 的完整路径"""
    assert matches_pattern("src/main.py", "src/main.py")
    assert not matches_pattern("main.py", "src/main.py")


def test_question_mark():
    """? 匹配单个非 / 字符"""
    assert matches_pattern("a.py", "?.py")
    assert matches_pattern("b.py", "?.py")
    assert not matches_pattern("app.py", "?.py")
    # Pattern without slash matches filename in any directory
    assert matches_pattern("xy/a.py", "?.py")


def test_character_class():
    """字符类 [abc]"""
    assert matches_pattern("a.txt", "[abc].txt")
    assert matches_pattern("b.txt", "[abc].txt")
    assert not matches_pattern("d.txt", "[abc].txt")


def test_no_match():
    """完全不匹配的路径"""
    assert not matches_pattern("readme.txt", "*.log")
    assert not matches_pattern("src/main.py", "*.pyc")
    assert not matches_pattern("docs/readme.txt", "build/")


# ---------------------------------------------------------------------------
# read_ignore_patterns 测试
# ---------------------------------------------------------------------------

def test_read_ignore_patterns():
    """读取 .cripperignore 并解析取反标记"""
    patterns = read_ignore_patterns(FIXTURE)
    assert len(patterns) == 7

    negate_flags = [n for n, _ in patterns]
    raw_patterns = [p for _, p in patterns]

    # important.log 应被取反
    assert (True, "important.log") in patterns
    # *.log 不应被取反
    assert (False, "*.log") in patterns
    assert (False, "build/") in patterns
    assert (False, "**/temp") in patterns


def test_read_nested_ignore():
    """读取嵌套 .cripperignore"""
    patterns = read_ignore_patterns(FIXTURE / "src")
    assert len(patterns) == 1
    assert patterns[0] == (False, "*.pyc")


# ---------------------------------------------------------------------------
# need_ignore 集成测试 — 模拟 walk_and_add 的遍历行为
# ---------------------------------------------------------------------------

def _collect_inherited(dirpath, basepath, inherited=None):
    """模拟 walk_and_add 中 inherited_patterns 的构建方式。"""
    if inherited is None:
        inherited = []
    local = [(dirpath, n, p) for n, p in read_ignore_patterns(dirpath)]
    return inherited + local


def _walk_and_check(dirpath, basepath, inherited=None):
    """模拟遍历，返回 (included_files, ignored_files) 两个列表。"""
    if inherited is None:
        inherited = []

    all_patterns = _collect_inherited(dirpath, basepath, inherited)
    included = []
    ignored = []

    try:
        entries = sorted(dirpath.iterdir(), key=lambda p: p.name)
    except PermissionError:
        return included, ignored

    for entry in entries:
        if entry.is_symlink():
            continue
        if need_ignore(entry, all_patterns, basepath):
            ignored.append(entry)
            continue
        if entry.is_dir():
            sub_in, sub_ig = _walk_and_check(entry, basepath, all_patterns)
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
    """验证应被忽略的条目（目录被忽略后不再递归，内部文件不会出现）"""
    included, ignored = _walk_and_check(FIXTURE, FIXTURE)
    ignored_rel = sorted(str(p.relative_to(FIXTURE)).replace("\\", "/") for p in ignored)

    # Directly matched files
    assert "debug.log" in ignored_rel
    assert "error.log" in ignored_rel
    assert "src/cache.pyc" in ignored_rel

    # Directly matched directories (contents not recursed into)
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
    # 2 .cripperignore + 3 files + 7 directories = 12 ignored entries
    assert len(ignored) == 12, f"Expected 12 ignored entries, got {len(ignored)}"
