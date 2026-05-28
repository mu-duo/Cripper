from colorama import Fore, Style


def calc_size(result):
    """Recursively calculate the size of an object in bytes."""
    size = len(result.encode("ascii"))
    if size < 1024:
        return f"{size} bytes"
    elif size < 1024**2:
        return f"{size / 1024:.2f} KB"
    elif size < 1024**3:
        return f"{size / 1024**2:.2f} MB"
    else:
        return f"{size / 1024**3:.2f} GB"


def error(msg):
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {msg}")


def warning(msg):
    print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} {msg}")


def info(msg):
    print(f"{Fore.GREEN}[INFO]{Style.RESET_ALL} {msg}")


def debug(msg):
    print(f"{Fore.BLUE}[DEBUG]{Style.RESET_ALL} {msg}")


def trace(msg):
    print(f"{Style.DIM}{Fore.CYAN}[TRACE]{Style.RESET_ALL} {msg}")


def red(msg):
    return f"{Fore.RED}{msg}{Style.RESET_ALL}"


def green(msg):
    return f"{Fore.GREEN}{msg}{Style.RESET_ALL}"


def yellow(msg):
    return f"{Fore.YELLOW}{msg}{Style.RESET_ALL}"


def blue(msg):
    return f"{Fore.BLUE}{msg}{Style.RESET_ALL}"


def magenta(msg):
    return f"{Fore.MAGENTA}{msg}{Style.RESET_ALL}"


def cyan(msg):
    return f"{Fore.CYAN}{msg}{Style.RESET_ALL}"


def white(msg):
    return f"{Fore.WHITE}{msg}{Style.RESET_ALL}"


def bold(msg):
    return f"{Style.BRIGHT}{msg}{Style.RESET_ALL}"


def gray(msg):
    return f"{Style.DIM}{msg}{Style.RESET_ALL}"
