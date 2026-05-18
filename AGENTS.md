# AGENTS.md

## 交互要求
- 思考过程用中文表述
- 回答也要用中文回复

## Install & Run
```bash
pip install -e .
cripper --help
python -m cripper                  # fallback
```

## Commands
- `encripper <path>` — file or directory to clipboard (ciphertext)
- `decripper <output-dir>` — clipboard → restored files
- `decripper -f <file> <output-dir>` — ciphertext file → restored files
- `cripper encrypt <path>` — same as `encripper`
- `cripper decrypt <output-dir>` — same as `decripper`

## Architecture
- `cripper/cli.py` — Click commands (`encrypt`, `decrypt`)
- `cripper/crypto.py` — Fernet encryption + tar.gz directory archiving
- `cripper/config.py` — key auto-created at `~/.cripper`; delete to regenerate
- Binary payload: `[1B type][4B name-len][name][content]`, then Fernet‑encrypted, base64'd

## No test/lint/CI
No tests, no lint config, no CI in this repo.
