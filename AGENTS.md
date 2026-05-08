# AGENTS.md

## Install & Run
```bash
pip install -e .
cripper --help
python -m cripper                  # fallback
```

## Commands
- `cripper encrypt <path>` — file or directory to clipboard (ciphertext)
- `cripper decrypt <output-dir>` — clipboard → restored files

## Architecture
- `cripper/cli.py` — Click commands (`encrypt`, `decrypt`)
- `cripper/crypto.py` — Fernet encryption + tar.gz directory archiving
- `cripper/config.py` — key auto-created at `~/.cripper`; delete to regenerate
- Binary payload: `[1B type][4B name-len][name][content]`, then Fernet‑encrypted, base64'd

## No test/lint/CI
No tests, no lint config, no CI in this repo.
