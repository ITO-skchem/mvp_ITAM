"""Entry point for the PyInstaller onefile build (run Django dev server)."""
import os
import sys
from pathlib import Path


def _ensure_import_path() -> None:
    if getattr(sys, "frozen", False):
        root = Path(getattr(sys, "_MEIPASS", ""))
    else:
        root = Path(__file__).resolve().parent
    s = str(root)
    if s and s not in sys.path:
        sys.path.insert(0, s)


def main() -> None:
    _ensure_import_path()
    if getattr(sys, "frozen", False):
        os.chdir(str(Path(sys.executable).resolve().parent))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "itam_portal.settings")
    from django.core.management import execute_from_command_line

    if len(sys.argv) > 1:
        addr = sys.argv[1]
        extra = sys.argv[2:]
    else:
        addr = "127.0.0.1:8000"
        extra = []
    execute_from_command_line([sys.argv[0], "runserver", addr, "--noreload", *extra])


if __name__ == "__main__":
    main()
