"""Print the stored chunks that contain the keywords of one eval question.

Usage (from the project root, venv activated):
    python scripts/find_text.py ar-3
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import connect  # noqa: E402
from app.evaluation import first_hit_rank  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Find the chunk behind an eval question")
    parser.add_argument("question_id")
    parser.add_argument("--config", default="article_1500")
    args = parser.parse_args()

    questions = json.loads((ROOT / "eval" / "questions.json").read_text(encoding="utf-8"))
    question = next(q for q in questions if q["id"] == args.question_id)
    print(f"Question: {question['question']}")
    print(f"Keywords: {question['keywords']}\n")

    with connect() as connection:
        rows = connection.execute(
            "SELECT page, article, content FROM chunks "
            "WHERE chunk_config = %s AND language = %s ORDER BY id",
            (args.config, question["language"]),
        ).fetchall()

    matches = [row for row in rows if first_hit_rank([row[2]], question["keywords"]) == 1]
    print(f"{len(matches)} chunk(s) contain all the keywords\n")
    for page, article, content in matches:
        print(f"--- p.{page}, article {article} ---")
        print(" ".join(content.split())[:900], "\n")


if __name__ == "__main__":
    main()