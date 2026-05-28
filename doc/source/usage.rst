Usage
=====

Install
-------

.. code-block:: bash

   pip install -e .

Requirements: Python >= 3.8, ``click``, ``cryptography``, ``pyperclip``.

Commands
--------

``cripper``
~~~~~~~~~~~

.. code-block:: bash

   cripper encrypt <path>        # file or directory → clipboard (Base64 ciphertext)
   cripper decrypt <output-dir>   # clipboard → restored files

``encripper`` / ``decripper``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Standalone entry points equivalent to ``cripper encrypt`` and ``cripper decrypt``:

.. code-block:: bash

   encripper <path>
   decripper <output-dir>

``decripper`` also accepts ``-f FILE`` to read ciphertext from a file instead of clipboard.

``engitcrypt``
~~~~~~~~~~~~~~

Encrypt changed files in a git working tree into a single clipboard payload.

.. code-block:: bash

   engitcrypt              # encrypt all changed files (staged + unstaged + untracked)
   engitcrypt -c <commit>  # encrypt files changed in a specific commit

A single file is encrypted directly; multiple files are packed into a tar archive preserving directory structure.

Key Management
--------------

On first run, a Fernet key is auto-generated at ``~/.cripper``. On non-Windows systems, the file is set to ``0o600`` permissions.

To regenerate the key, delete ``~/.cripper`` — a new key will be created on the next run.

Encryption Format
-----------------

**Binary payload structure:**

.. code-block:: text

   [1B type][4B name-len (big-endian)][name (UTF-8)][content]

+--------+---------------------------------------------------+
| Type   | Content                                           |
+========+===================================================+
| 0x00   | Raw file bytes                                    |
+--------+---------------------------------------------------+
| 0x01   | tar.gz archive of directory tree                  |
+--------+---------------------------------------------------+

The payload is Fernet-encrypted, then Base64-encoded for clipboard transfer.

Fallback
--------

If clipboard access fails (e.g., headless environments or no desktop session), encrypted data is written to ``default.enc`` in the current directory.

Similarly, when decrypting, use ``-f FILE`` to read ciphertext from a file instead of clipboard:

.. code-block:: bash

   cripper decrypt /tmp/out -f ciphertext.enc

``.cripperignore``
------------------

Place a ``.cripperignore`` file in any directory to exclude matching files/directories when encrypting a directory tree. Patterns follow ``.gitignore`` conventions:

- ``*.log`` — ignore all ``.log`` files (any nesting level)
- ``build/`` — ignore the ``build`` directory and everything inside
- ``sub/*.tmp`` — ignore ``.tmp`` files directly inside ``sub/``

Lines starting with ``#`` are comments; blank lines are skipped. The ``.cripperignore`` file itself is always excluded.

Ignore files are checked recursively — a pattern in a parent directory applies to all subdirectories. The last matching pattern wins; negated patterns (``!``) re-include files.

License
-------

Apache 2.0 — see `LICENSE <https://github.com/nichunlong/Cripper/blob/main/LICENSE>`_.
