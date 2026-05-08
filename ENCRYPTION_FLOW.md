# Cripper 加密/解密流程说明

## 1. 密钥管理

密钥存储在用户目录下的 `~/.cripper` 文件中。

- 首次运行时，系统使用 `cryptography.fernet.Fernet.generate_key()` 自动生成一个 32 字节的 Fernet 对称密钥，写入 `~/.cripper`
- 后续运行时直接读取该文件中的密钥
- 如需更换密钥，删除 `~/.cripper` 后重新运行即可自动生成新密钥
- 非 Windows 系统上文件权限设为 `0o600`

```python
# config.py
CONFIG_PATH = Path.home() / ".cripper"
key = Fernet.generate_key().decode()   # 生成并写入
key = CONFIG_PATH.read_text().strip()  # 后续读取
```

---

## 2. 加密流程 (`cripper encrypt <path>`)

### 2.1 整体流程

```
输入 path → 判断类型 → 构建载荷(payload) → Fernet 加密 → Base64 编码 → 写入剪切板
```

### 2.2 载荷结构 (payload)

统一的二进制头部 + 内容体：

| 偏移 | 大小 | 说明 |
|-------|------|------|
| 0 | 1 byte | 类型标识：`0x00` = 文件，`0x01` = 目录 |
| 1 | 4 bytes | 原始名称长度（Big-Endian uint32） |
| 5 | N bytes | 原始名称（UTF-8 编码） |
| 5+N | 剩余 | 加密前的原始内容 |

### 2.3 加密文件

1. 以二进制方式读取文件全部内容
2. 取文件名（不含路径）作为 `name`
3. 构建载荷：
   ```
   [0x00] [name_len(4B)] [name(UTF-8)] [file_content]
   ```
4. 用 Fernet 密钥对载荷进行加密
5. 对加密结果进行 Base64 编码
6. 将 Base64 字符串写入系统剪切板

**示例：** 加密 `/home/user/notes.txt`（内容为 `hello`）
```
载荷: 00 00 00 00 09 6E 6F 74 65 73 2E 74 78 74 68 65 6C 6C 6F
       ↑   ↑                 ↑ notes.txt (9 bytes)           ↑ hello
     type  name_len=9
```
→ Fernet 加密 → Base64 → 剪切板

### 2.4 加密目录

1. 遍历目录下所有文件，使用 `tarfile` 在内存中创建 **tar.gz** 压缩包
   - `arcname = file_path.relative_to(dir_path.parent)` 保留完整目录树结构
   - 例如：`/home/user/project/src/main.py` → tar 中的条目为 `project/src/main.py`
2. 取目录名（不含父路径）作为 `name`
3. 构建载荷：
   ```
   [0x01] [name_len(4B)] [name(UTF-8)] [tar.gz_bytes]
   ```
4. 用 Fernet 密钥对载荷进行加密
5. Base64 编码后写入剪切板

**目录保留结构示例：**
```
输入目录: /home/user/myproject/
├── main.py
└── lib/
    └── utils.py

tar.gz 内部结构:
  myproject/
  myproject/main.py
  myproject/lib/
  myproject/lib/utils.py
```
解密时将完整还原此目录树。

---

## 3. 解密流程 (`cripper decrypt <output-dir>`)

### 3.1 整体流程

```
读取剪切板 → Base64 解码 → Fernet 解密 → 解析载荷头 → 还原文件/目录
```

### 3.2 详细步骤

1. 从系统剪切板读取 Base64 字符串
2. Base64 解码，得到 Fernet 加密的二进制数据
3. 使用 `~/.cripper` 中的密钥进行 Fernet 解密，得到原始载荷
4. 解析载荷头部：
   - `payload[0]` — 类型标识
   - `payload[1:5]` — 名称长度（Big-Endian uint32）
   - `payload[5:5+n]` — 原始名称（UTF-8）
   - `payload[5+n:]` — 内容数据
5. 根据类型还原：

**类型 0（文件）：**
- 在 `output_dir` 下创建文件，文件名为解析出的 `name`
- 写入 `content` 数据

**类型 1（目录）：**
- 创建一个 `BytesIO` 流指向 `content` 数据
- 使用 `tarfile.open(mode='r:gz')` 解压
- 调用 `tar.extractall(output_dir)` 还原整个目录树

6. 返回最终还原路径

### 3.3 错误处理

- 剪切板无法读取 → `ClickException("Cannot read from clipboard.")`
- 剪切板为空 → `ClickException("Clipboard is empty.")`
- Base64 解码失败 / Fernet 解密失败 / 载荷解析失败 → `ClickException(f"Decryption failed: {e}")`

---

## 4. 依赖项

```
click>=8.0           # CLI 框架
cryptography>=3.0    # Fernet 对称加密
pyperclip>=1.8       # 系统剪切板操作
```

## 5. 安全提示

- 密钥存储在 `~/.cripper`，无密码保护，任何能读取该文件的程序均可解密剪贴板内容
- Fernet 使用 AES-128-CBC + HMAC-SHA256，提供加密和完整性校验
- 加密后的数据经 Base64 编码放在剪切板中，不直接暴露二进制密文
