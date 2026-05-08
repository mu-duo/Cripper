import base64
import fnmatch
import io
import tarfile
from pathlib import Path

from cryptography.fernet import Fernet

from .config import IGNORE_FILE, get_or_create_key


def _get_fernet():
    key = get_or_create_key()
    return Fernet(key.encode() if isinstance(key, str) else key)


def _build_file_payload(filepath):
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


def _read_ignore_patterns(dirpath):
    """Load patterns from IGNORE_FILE in dirpath if it exists."""
    ignore_file = dirpath / IGNORE_FILE
    patterns = []
    if ignore_file.is_file():
        with open(ignore_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    return patterns


def _matches_pattern(rel_path, pattern):
    """Check if a relative path matches an ignore pattern."""
    rel = rel_path.replace("\\", "/")
    p = pattern.replace("\\", "/")

    if fnmatch.fnmatch(rel, p):
        return True

    # Directory pattern (ends with /) — match dir and its contents
    if p.endswith("/"):
        p_dir = p[:-1]
        if rel == p_dir or rel.startswith(p_dir + "/"):
            return True
        if fnmatch.fnmatch(rel, p_dir):
            return True

    # Match filename alone (handles patterns without slash like *.pyc)
    if "/" not in p:
        if fnmatch.fnmatch(Path(rel).name, p):
            return True

    return False


def _is_entry_ignored(entry, all_patterns, basepath):
    """Check whether entry should be excluded by any inherited pattern."""
    if entry.name == IGNORE_FILE:
        return True

    for pattern_base, pattern in all_patterns:
        try:
            rel = str(entry.relative_to(pattern_base))
        except ValueError:
            continue
        if _matches_pattern(rel, pattern):
            return True
    return False


def _walk_and_add(tar, dirpath, basepath, inherited_patterns=None):
    """Recursively add files to tar, respecting .cripperignore rules."""
    if inherited_patterns is None:
        inherited_patterns = []

    local = [(dirpath, p) for p in _read_ignore_patterns(dirpath)]
    all_patterns = inherited_patterns + local

    try:
        entries = sorted(dirpath.iterdir(), key=lambda p: p.name)
    except PermissionError:
        return

    for entry in entries:
        if entry.is_symlink():
            continue

        if _is_entry_ignored(entry, all_patterns, basepath):
            continue

        if entry.is_dir():
            _walk_and_add(tar, entry, basepath, all_patterns)
        elif entry.is_file():
            arcname = entry.relative_to(basepath).as_posix()
            tar.add(entry, arcname=arcname)
            print(f"Encrypted {entry}")


def _build_dir_payload(dirpath):
    path = Path(dirpath)
    buf = io.BytesIO()

    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        _walk_and_add(tar, path, path)

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
        payload = _build_file_payload(p)
    elif p.is_dir():
        payload = _build_dir_payload(p)
    else:
        raise ValueError(f"{path} is neither a file nor a directory")

    f = _get_fernet()
    encrypted = f.encrypt(payload)
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_to(data_b64, output_dir):
    f = _get_fernet()
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
