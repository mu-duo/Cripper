使用说明
========

安装
----

.. code-block:: bash

   pip install cripper

依赖：Python >= 3.8, ``click``, ``cryptography``, ``pyperclip``。

编译文档
--------

.. code-block:: bash

   pip install -e ".[doc]"
   cd doc
   make html      # Linux/macOS
   make.bat html  # Windows

HTML 输出位于 ``doc/build/html/``。

命令说明
--------

``cripper``
~~~~~~~~~~~

.. code-block:: bash

   cripper encrypt <path>         # 加密文件/目录 → 剪贴板（Base64 密文）
   cripper decrypt <output-dir>   # 剪贴板 → 还原文件

``encripper`` / ``decripper``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

独立的入口命令，功能等价于 ``cripper encrypt`` 和 ``cripper decrypt``：

.. code-block:: bash

   encripper <path>
   decripper <output-dir>

``decripper`` 也支持 ``-f FILE`` 从文件读取密文而非剪贴板。

``engitcrypt``
~~~~~~~~~~~~~~

将 git 工作树中的变更文件加密为单个剪贴板载荷。

.. code-block:: bash

   engitcrypt              # 加密所有变更（已暂存 + 未暂存 + 未跟踪）
   engitcrypt -c <commit>  # 加密指定 commit 中的变更文件

单个文件直接加密；多个文件会被打包为保留目录结构的 tar 归档。

密钥管理
--------

首次运行时，自动在 ``~/.cripper`` 生成 Fernet 密钥。非 Windows 系统上文件权限设为 ``0o600``。

若要更换密钥，删除 ``~/.cripper`` 即可，下次运行时会重新生成。

加密格式
--------

**二进制载荷结构：**

.. code-block:: text

   [1B 类型][4B 名称长度 (大端)][名称 (UTF-8)][内容]

======  ======================
 类型    内容
======  ======================
 0x00    原始文件字节
 0x01    目录树的 tar.gz 归档
======  ======================

载荷经过 Fernet 加密，再 Base64 编码后放入剪贴板。

降级方案
--------

如果剪贴板不可用（如无桌面环境），加密数据会写入当前目录的 ``default.enc`` 文件中。

解密时也可使用 ``-f FILE`` 从文件读取密文：

.. code-block:: bash

   cripper decrypt /tmp/out -f ciphertext.enc

``.cripperignore``
------------------

在任意目录下放置 ``.cripperignore`` 文件，可在加密该目录树时排除匹配的文件/目录。规则遵循 ``.gitignore`` 约定：

- ``*.log`` — 忽略所有 ``.log`` 文件（任意嵌套层级）
- ``build/`` — 忽略 ``build`` 目录及其内容
- ``sub/*.tmp`` — 忽略仅在 ``sub/`` 目录下的 ``.tmp`` 文件

以 ``#`` 开头的行为注释，空行会被跳过。``.cripperignore`` 文件本身始终被排除。

忽略文件会递归向上查找——父目录中定义的规则对所有子目录生效。最后匹配的规则优先；否定规则（``!``）可重新包含文件。

许可证
------

Apache 2.0 — 参见 `LICENSE <https://github.com/nichunlong/Cripper/blob/main/LICENSE>`_。
