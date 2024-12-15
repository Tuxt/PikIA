from core import PikIA
import os
from pathlib import Path

ASSETS_DIR = Path(__file__).parent / "assets"

def print_header():
    with open(ASSETS_DIR / "header.txt", "r", encoding="utf-8") as f:
        print(f.read())

def main():
    os.system("cls" if os.name == "nt" else "clear")
    print_header()
    pikia = PikIA()
    pikia.run()


if __name__ == "__main__":
    main()