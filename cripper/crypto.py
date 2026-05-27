import base64
import io
import re
import tarfile
from pathlib import Path

from cryptography.fernet import Fernet

from .config import IGNORE_FILE, get_or_create_key


def get_fernet():
    key = get_or_create_key()
    return Fernet(key.encode() if isinstance(key, str) else key)


def build_file_payload(filepath):
    path = Path(filepath)
    with open(path, "rb") as fh:
        content = fh.read()

    name_bytes = path.name.encode("utf-8")
    payload = b"\x00"  # type 0 = file
    payload += len(name_bytes).to_bytes(4, "big")
    payload += name_bytes
    payload += content

    print(f"Encrypted {path}")
    return payload


def _glob_to_regex(pattern):
    """Convert a gitignore glob pattern to a regex string."""
    i = 0
    n = len(pattern)
    parts = []

    while i < n:
        if pattern[i : i + 2] == "**":
            if i + 3 <= n and pattern[i + 2] == "/":
                # **/ — match zero or more directories
                if i == 0:
                    parts.append(r"(?:.*/)?")
                else:
                    # The preceding / was already appended as a literal; pop it
                    if parts and parts[-1] == "/":
                        parts.pop()
                    parts.append(r"/(?:.*/)?")
                i += 3
            elif i + 2 == n:
                # trailing ** — match everything inside
                if parts and parts[-1] == "/":
                    parts.pop()
                parts.append(r"(?:/.*)?")
                i += 2
            else:
                parts.append(r".*")
                i += 2
        elif pattern[i] == "*":
            parts.append(r"[^/]*")
            i += 1
        elif pattern[i] == "?":
            parts.append(r"[^/]")
            i += 1
        elif pattern[i] == "[":
            parts.append("[")
            i += 1
        elif pattern[i] == "]":
            parts.append("]")
            i += 1
        elif pattern[i] in r".^${}()|+\\":
            parts.append("\\" + pattern[i])
            i += 1
        else:
            parts.append(pattern[i])
            i += 1

    return "".join(parts)


def read_ignore_patterns(dirpath):
    """Load patterns from IGNORE_FILE in dirpath if it exists.

    Returns a list of (negate, pattern) tuples.
    """
    ignore_file = dirpath / IGNORE_FILE
    patterns = []
    if ignore_file.is_file():
        with open(ignore_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n").rstrip(" ")
                if not line or line.startswith("#"):
                    continue
                negate = False
                if line.startswith("!"):
                    negate = True
                    line = line[1:]
                patterns.append((negate, line))
    return patterns


def matches_pattern(rel_path, pattern):
    """Check if a relative path matches a gitignore-style pattern."""
    rel = rel_path.replace("\\", "/")

    # Trailing / means match directories only (caller checks via need_ignore)
    if pattern.endswith("/"):
        pattern = pattern.rstrip("/")

    # Leading / anchors to the directory containing .cripperignore.
    # Once anchored, the pattern must match the full relative path.
    anchored = pattern.startswith("/")
    if anchored:
        pattern = pattern[1:]

    has_slash = "/" in pattern

    if not has_slash and not anchored:
        match_against = Path(rel).name
    else:
        match_against = rel

    regex = "^" + _glob_to_regex(pattern) + "$"
    return bool(re.match(regex, match_against))


def need_ignore(entry, all_patterns, basepath):
    """Check whether entry should be excluded by gitignore-style patterns.

    The last matching pattern wins; a negated pattern (!) re-includes the file.
    """
    if entry.name == IGNORE_FILE:
        return True

    result = False
    is_dir = entry.is_dir()

    for pattern_base, negate, pattern in all_patterns:
        try:
            rel = str(entry.relative_to(pattern_base))
        except ValueError:
            continue

        if pattern.endswith("/") and not is_dir:
            continue

        if matches_pattern(rel, pattern):
            result = not negate

    return result


def walk_and_add(tar, dirpath, basepath, inherited_patterns=None):
    """Recursively add files to tar, respecting .cripperignore rules."""
    if inherited_patterns is None:
        inherited_patterns = []

    local = [(dirpath, negate, p) for negate, p in read_ignore_patterns(dirpath)]
    all_patterns = inherited_patterns + local

    try:
        entries = sorted(dirpath.iterdir(), key=lambda p: p.name)
    except PermissionError:
        return

    for entry in entries:
        if entry.is_symlink():
            continue

        if need_ignore(entry, all_patterns, basepath):
            continue

        if entry.is_dir():
            walk_and_add(tar, entry, basepath, all_patterns)
        elif entry.is_file():
            arcname = entry.relative_to(basepath).as_posix()
            tar.add(entry, arcname=arcname)
            print(f"Encrypted {entry}")


def build_dir_payload(dirpath):
    path = Path(dirpath)
    buf = io.BytesIO()

    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        walk_and_add(tar, path, path)

    tar_bytes = buf.getvalue()

    name_bytes = path.name.encode("utf-8")
    payload = b"\x01"  # type 1 = directory
    payload += len(name_bytes).to_bytes(4, "big")
    payload += name_bytes
    payload += tar_bytes
    return payload


def encrypt_path(path):
    p = Path(path)
    if p.is_file():
        payload = build_file_payload(p)
    elif p.is_dir():
        payload = build_dir_payload(p)
    else:
        raise ValueError(f"{path} is neither a file nor a directory")

    f = get_fernet()
    encrypted = f.encrypt(payload)
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_to(data_b64, output_dir):
    f = get_fernet()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    encrypted = base64.b64decode(data_b64)
    payload = f.decrypt(encrypted)

    type_byte = payload[0]
    name_len = int.from_bytes(payload[1:5], "big")
    name = payload[5 : 5 + name_len].decode("utf-8")
    content = payload[5 + name_len :]

    if type_byte == 0:  # file
        output_path = output_dir / name
        with open(output_path, "wb") as fh:
            fh.write(content)
        print(f"Decrypted {output_path}")
        return output_path
    elif type_byte == 1:  # directory
        buf = io.BytesIO(content)
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            for member in tar.getmembers():
                tar.extract(member, output_dir, filter="fully_trusted")
                print(f"Decrypted {output_dir / member.name}")
        return output_dir / name if (output_dir / name).exists() else output_dir
    else:
        raise ValueError(f"Unknown payload type: {type_byte}")
