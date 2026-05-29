import base64
import io
import tarfile
from pathlib import Path

from cryptography.fernet import Fernet
from py_walk import get_parser_from_file

from .config import IGNORE_FILE, get_or_create_key
from .util import info, trace, gray, green


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

    info(f"Encrypted {path}")
    return payload


def read_ignore_patterns(dirpath):
    """Load a Parser from IGNORE_FILE in dirpath if it exists.

    Returns a Parser or None.
    """
    ignore_file = dirpath / IGNORE_FILE
    if ignore_file.is_file():
        return get_parser_from_file(str(ignore_file))
    return None


def is_ignore(entry: Path, parsers):
    """Check whether entry should be excluded by gitignore-style patterns.

    Checks the entry against each Parser; returns True if any parser matches.
    Negations (e.g. ``!important.log``) are handled by py_walk internally.
    """
    if entry.name == IGNORE_FILE:
        return True

    for parser in parsers:
        if parser.match(entry):
            return True

    return False


def walk_and_add(tar, dirpath, root, parsers=None):
    """Recursively add files to tar, respecting .cripperignore rules."""
    if parsers is None:
        parsers = []

    parser = read_ignore_patterns(dirpath)
    if parser is not None:
        parsers.append(parser)

    try:
        entries = sorted(dirpath.iterdir(), key=lambda p: p.name)
    except PermissionError:
        return

    for entry in entries:
        if entry.is_symlink():
            continue

        if is_ignore(entry, parsers):
            trace(gray(f"Skipped {entry} due to ignore rules"))
            continue

        if entry.is_dir():
            walk_and_add(tar, entry, root, parsers)
        elif entry.is_file():
            arcname = entry.relative_to(root).as_posix()
            tar.add(entry, arcname=arcname)
            trace(green(f"Encrypted {entry}"))


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
        info(f"Decrypted {output_path}")
        return output_path
    elif type_byte == 1:  # directory
        buf = io.BytesIO(content)
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            for member in tar.getmembers():
                tar.extract(member, output_dir, filter="fully_trusted")
                info(f"Decrypted {output_dir / member.name}")
        return output_dir / name if (output_dir / name).exists() else output_dir
    else:
        raise ValueError(f"Unknown payload type: {type_byte}")
