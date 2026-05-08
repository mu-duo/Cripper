from setuptools import setup, find_packages

setup(
    name="cripper",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0",
        "cryptography>=3.0",
        "pyperclip>=1.8",
    ],
    entry_points={
        "console_scripts": [
            "cripper=cripper.cli:main",
        ],
    },
    python_requires=">=3.8",
)
