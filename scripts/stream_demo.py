"""Call POST /ask/stream and print the answer as it arrives, with timings.

Usage (API running on port 8000, venv activated):
    python scripts/stream_demo.py "Avant quelle date l'employeur doit-il verser les cotisations ?"
"""
import argparse
import json
import sys
import time

import httpx

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Streaming demo")
    parser.add_argument("question")
    parser.add_argument("--url", default="http://127.0.0.1:8000/ask/stream")
    args = parser.parse_args()

    started = time.perf_counter()
    first_token: float | None = None
    event = ""

    with httpx.stream("POST", args.url, json={"question": args.question}, timeout=180) as response:
        if response.status_code != 200:
            response.read()
            print(f"HTTP {response.status_code}: {response.text}")
            return
        for line in response.iter_lines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
                elapsed = time.perf_counter() - started
                if event == "sources":
                    print(f"[{len(data['sources'])} sources received after {elapsed:.1f}s]")
                elif event == "token":
                    if first_token is None:
                        first_token = elapsed
                        print(f"[first token after {elapsed:.1f}s]")
                    print(data["text"], end="", flush=True)
                elif event == "done":
                    print(f"\n\n[done after {elapsed:.1f}s] refused={data['refused']} "
                          f"reason={data['refusal_reason']}")
                    for citation in data["citations"]:
                        print(f"  [{citation['number']}] {citation['law_title'] or citation['document']}"
                              f" | Art. {citation['article']} | p.{citation['page']}")
                    print(f"  timings: {data['timings']}")
                elif event == "error":
                    print(f"\n[error {data['status']}] {data['detail']}")


if __name__ == "__main__":
    main()