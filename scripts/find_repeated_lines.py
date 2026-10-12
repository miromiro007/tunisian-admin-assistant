"""Diagnostic: find lines that repeat at the top/bottom of many pages.

Usage (from the project root, venv activated):
    python scripts/find_repeated_lines.py
    python scripts/find_repeated_lines.py --edge 2 --min-share 0.05
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

# Make "import app" work when started as `python scripts/find_repeated_lines.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.pdf_loader import load_pdf  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

RAW_DIR = Path("data/raw")


def normalize_line(line: str) -> str:
    """Digits -> '#', so 'Page 321' and 'Page 322' become the same key."""
    return re.sub(r"\d+", "#", line).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Find repeated header/footer lines")
    parser.add_argument("--edge", type=int, default=3, help="lines checked at top and bottom")
    parser.add_argument("--min-share", type=float, default=0.10, help="minimum share of pages")
    args = parser.parse_args()

    for pdf_path in sorted(RAW_DIR.glob("*.pdf")):
        pages = load_pdf(pdf_path)
        counter: Counter[str] = Counter()
        examples: dict[str, str] = {}

        for page in pages:
            lines = page.text.split("\n")
            edge_lines = lines[: args.edge] + lines[-args.edge :]
            # set(): a line repeated twice on the SAME page counts once.
            for key in {normalize_line(line) for line in edge_lines}:
                counter[key] += 1
            for line in edge_lines:
                examples.setdefault(normalize_line(line), line)

        print(f"\n=== {pdf_path.name}: {len(pages)} pages ===")
        shown = 0
        for key, count in counter.most_common():
            share = count / len(pages)
            if share < args.min_share:
                break
            print(f"{count:4d} pages ({share:5.1%})  {examples[key][:90]}")
            shown += 1
            if shown >= 15:
                break
        if shown == 0:
            print("  No line above the threshold.")


if __name__ == "__main__":
    main()