# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
pip install -e .              # install in editable mode
pip install -e ".[doc,dev]"   # install with docs + test deps
cripper --help                # CLI entry point
python -m cripper             # fallback if the script entry fails
```

## Commands

| Command | Purpose |
|---------|---------|
| `cripper encrypt <path>` | Encrypt file or directory → clipboard (Base64 ciphertext) |
| `cripper decrypt <output-dir>` | Clipboard → restored files |
| `cripper decrypt -f <file> <output-dir>` | Ciphertext file → restored files |
| `encripper <path>` | Shorthand for `cripper encrypt` |
| `decripper <output-dir>` | Shorthand for `cripper decrypt` |
| `engitcrypt` | Encrypt working-tree changes to clipboard |
| `engitcrypt -c <commit>` | Encrypt files changed in a specific commit |

## Running Tests

```bash
pytest                          # all tests (no test files exist yet)
```

There are no test files in the repo as of v0.3.1; tests directory is not yet created.

## Building Docs

```bash
cd doc && make html             # or: sphinx-build -M html source build
```

Sphinx auto-generated API docs from `cripper.*` modules using `sphinx.ext.autodoc`. ReadTheDocs theme.

## Architecture

```
cripper/
├── __init__.py    → from .cli import main
├── __main__.py    → invokes cli()
├── cli.py         → Click command group + standalone commands (encripper/decripper)
├── crypto.py      → Fernet encrypt/decrypt, tar.gz dir packing, .cripperignore handling
├── config.py      → ~/.cripper key file (auto-generated on first run)
├── engitcrypt.py  → git-aware encryption: changed/committed files → single payload
└── util.py        → colorama-based logging (info/trace/debug/error) + calc_size()
```

**Data flow:** `encrypt_path(path)` → builds a binary payload with `[1B type][4B name-len][name][content]` → Fernet encrypt → Base64 → clipboard. Files get `type=0x00` (raw bytes), directories get `type=0x01` (tar.gz in memory).

**Key management:** `~/.cripper` stores a Fernet key. Delete to regenerate. `config.get_or_create_key()` handles first-run generation and subsequent reads.

**Ignore patterns:** `.cripperignore` files follow `.gitignore` conventions, processed via `py_walk.get_parser_from_file()`. Recursively merged — parent-directory patterns apply to all subdirectories. Symlinks are always skipped.

**engitcrypt workflow:** detects dirty working tree → stashes if needed → checks out target commit → encrypts changed files → restores original branch. Single file encrypted directly; multiple files tar.gz'd preserving directory structure.

## Dependencies

- `click>=8.0` — CLI framework
- `cryptography>=3.0` — Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256)
- `py-walk>=0.3.0` — `.gitignore`-style pattern matching for `.cripperignore`
- `pyperclip>=1.8` — cross-platform clipboard access
- Dev: `pytest>=9.0`, `sphinx>=9.0`, `sphinx-rtd-theme>=3.0`

## Clipboard Fallback

If `pyperclip` can't access the clipboard (headless environments), encrypted output is written to `default.enc` in the current working directory instead.

## Code Style

No linter/formatter config in the repo. Follow PEP 8 conventions as established in existing code: type hints on public functions, docstrings on public functions (single-line or concise), imports at module level.
