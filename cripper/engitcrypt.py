import shutil
import subprocess
import tempfile
from pathlib import Path

import click
import pyperclip

from .config import DEFAULT_ENCRYPTION_FILE
from .crypto import encrypt_path
from .util import calc_size


def _get_changed_files():
    """Return list of changed files in the working tree (staged + unstaged + untracked)."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise click.ClickException(f"git diff failed: {result.stderr.strip()}")

    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True
    )

    files = []
    if result.stdout.strip():
        files.extend(f for f in result.stdout.strip().split("\n") if f)
    if untracked.stdout.strip():
        files.extend(f for f in untracked.stdout.strip().split("\n") if f)

    return files


def _get_commit_files(commit):
    """Return list of files changed in a specific commit."""
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "-r", "--name-only", commit],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise click.ClickException(f"git diff-tree failed: {result.stderr.strip()}")

    return [f for f in result.stdout.strip().split("\n") if f]


def _is_working_tree_dirty():
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True
    )
    return bool(result.stdout.strip())


def _encrypt_files(files):
    existing = []
    for f in files:
        filepath = Path(f)
        if filepath.is_file():
            existing.append(f)
        else:
            click.echo(f"  Skipping '{f}' (not an existing file)")

    if not existing:
        return

    if len(existing) == 1:
        result = encrypt_path(existing[0])
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            # The archive root name is arbitrary; use "changes"
            root = tmp / "changes"
            root.mkdir()
            for f in existing:
                dest = root / f
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
            result = encrypt_path(str(root))

    try:
        pyperclip.copy(result)
        label = "file" if len(existing) == 1 else "files"
        click.echo(f"Encrypted {len(existing)} {label} → clipboard.")
        click.echo(f"content size: {calc_size(result)}")
    except pyperclip.PyperclipException:
        out = Path(DEFAULT_ENCRYPTION_FILE)
        out.write_text(result, encoding="ascii")
        click.echo(f"Encrypted {len(existing)} file(s) → {out}")
        click.echo(f"content size: {calc_size(result)}")


@click.command()
@click.option(
    "-c", "--commit",
    default=None,
    help="Encrypt files changed in the given commit instead of the working tree.",
)
def engitcrypt(commit):
    """Encrypt changed files into a single clipboard payload.

    In the default mode, all changed files in the working tree (staged,
    unstaged, and untracked) are collected.  A single file is encrypted
    directly; multiple files are packed into a tar archive preserving
    their directory structure before encryption.

    With --commit, the files changed in the given commit are encrypted
    instead.
    """
    if commit:
        original_ref = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True
        ).stdout.strip()

        stashed = False
        if _is_working_tree_dirty():
            click.echo("Working tree is dirty. Stashing changes...")
            subprocess.run(
                ["git", "stash", "push", "--include-untracked", "-m", "engitcrypt auto stash"],
                check=True, capture_output=True
            )
            stashed = True

        try:
            subprocess.run(
                ["git", "checkout", commit],
                check=True, capture_output=True
            )
            files = _get_commit_files(commit)

            if not files:
                click.echo(f"No files changed in commit {commit}.")
                return

            click.echo(f"Encrypting {len(files)} file(s) from commit '{commit}':")
            _encrypt_files(files)
        finally:
            subprocess.run(
                ["git", "checkout", original_ref],
                check=True, capture_output=True
            )
            if stashed:
                click.echo("Restoring stashed changes...")
                subprocess.run(
                    ["git", "stash", "pop"],
                    check=True, capture_output=True
                )
    else:
        files = _get_changed_files()

        if not files:
            click.echo("No changed files in the working tree.")
            return

        click.echo(f"Encrypting {len(files)} changed file(s):")
        _encrypt_files(files)


def main_engitcrypt():
    engitcrypt()
