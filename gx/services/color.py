import os
import sys

class ANSI:
    reset = "\u001b[0m"
    bold = "\u001b[1m"
    cyan = "\u001b[36m"
    yellow = "\u001b[33m"
    green = "\u001b[32m"
    red = "\u001b[31m"
    gray = "\u001b[90m"

def supports_color() -> bool:
    if os.environ.get("FORCE_COLOR") is not None and os.environ.get("FORCE_COLOR") != "0":
        return True

    if os.environ.get("NO_COLOR") is not None:
        return False

    return sys.stdout.isatty()

def colorize(text: str, color: str) -> str:
    if not supports_color():
        return text
    return f"{color}{text}{ANSI.reset}"
