import subprocess
import sys
from typing import List

def run_clipboard_command(command: str, args: List[str], text_input: str) -> None:
    subprocess.run(
        [command] + args,
        input=text_input,
        text=True,
        capture_output=True,
        check=True
    )

def copy_to_clipboard(text: str) -> None:
    if sys.platform == "darwin":
        run_clipboard_command("pbcopy", [], text)
        return

    if sys.platform == "win32":
        run_clipboard_command("clip.exe", [], text)
        return

    # Linux / other Unix
    try:
        run_clipboard_command("wl-copy", [], text)
        return
    except Exception:
        try:
            run_clipboard_command("xclip", ["-selection", "clipboard"], text)
            return
        except Exception:
            raise RuntimeError("Clipboard copy failed on Linux. Install `wl-copy` or `xclip` and try again.")
