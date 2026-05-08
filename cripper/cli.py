import click
import pyperclip
from pathlib import Path

from cripper.config import DEFAULT_ENCRYPTION_FILE

from .crypto import encrypt_path, decrypt_to


@click.group()
def cli():
    """Cripper — clipboard-based file encryption/decryption tool."""


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def encrypt(path):
    """Encrypt a file or directory and copy ciphertext to clipboard."""
    try:
        result = encrypt_path(path)
    except Exception as e:
        raise click.ClickException(str(e))

    p = Path(path)
    label = "file" if p.is_file() else "directory"

    try:
        pyperclip.copy(result)
        click.echo(f"Encrypted {label} '{p.name}'.")
    except pyperclip.PyperclipException:
        with open(DEFAULT_ENCRYPTION_FILE, "w") as fh:
            fh.write(result)
        click.echo(f"Encrypted {label} '{p.name}' and saved to {DEFAULT_ENCRYPTION_FILE}.")


@cli.command()
@click.argument("output_dir", type=click.Path())
@click.option(
    "-f", "--file", "input_file",
    type=click.Path(exists=True, dir_okay=False),
    help="Read ciphertext from file instead of clipboard.",
)
def decrypt(output_dir, input_file):
    """Decrypt clipboard content into the specified output directory."""
    if input_file:
        data = Path(input_file).read_text()
    else:
        try:
            data = pyperclip.paste()
        except pyperclip.PyperclipException:
            raise click.ClickException(
                "Cannot read from clipboard. Use -f FILE to read from a file instead."
            )

    if not data:
        raise click.ClickException("No ciphertext found.")

    try:
        dest = decrypt_to(data, output_dir)
    except Exception as e:
        raise click.ClickException(f"Decryption failed: {e}")

    click.echo(f"Decrypted to: {dest}")


def main():
    cli()
