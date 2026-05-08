# Cripper

Clipboard-based file & directory encryption tool — encrypt/decrypt via system clipboard with AES-128-CBC (Fernet).

## Install

```bash
pip install -e .
```

**Requirements:** Python >= 3.8, `click`, `cryptography`, `pyperclip`

## Usage

```bash
cripper encrypt <path>       # file or directory → clipboard (Base64 ciphertext)
cripper decrypt <output-dir>  # clipboard → restored files
```

Decrypt output is written to `<output-dir>/<original-name>`.

## Key Management

On first run, a Fernet key is auto-generated at `~/.cripper` (non-Windows: `chmod 600`). Delete the file to regenerate a new key.

## `.cripperignore`

Place a `.cripperignore` file in any directory to exclude matching files/directories when encrypting a directory tree. Patterns follow `.gitignore` conventions:

- `*.log` — ignore all `.log` files (any nesting level)
- `build/` — ignore the `build` directory and everything inside
- `sub/*.tmp` — ignore `.tmp` files directly inside `sub/`
- Lines starting with `#` are comments; blank lines are skipped

Ignore files are checked recursively — a pattern in a parent directory applies to all subdirectories.

## Encryption Format

Binary payload: `[1B type][4B name-len (big-endian)][name (UTF-8)][content]`, then Fernet-encrypted, Base64-encoded.

| Type | Content |
|------|---------|
| `0x00` | Raw file bytes |
| `0x01` | tar.gz archive of directory tree |

## Fallback

If clipboard access fails (e.g. headless environments), encrypted data is written to `default.enc` in the current directory.

## License

Apache 2.0 — see [LICENSE](LICENSE)
