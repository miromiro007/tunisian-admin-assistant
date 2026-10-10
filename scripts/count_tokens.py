"""Experiment: how many tokens does the same sentence cost in EN / FR / AR?

Run from the project root:  python scripts/count_tokens.py
"""

import tiktoken  
# Same meaning, three languages.
SAMPLES: dict[str, str] = {
    "English": "How do I register a company in Tunisia?",
    "French": "Comment créer une entreprise en Tunisie ?",
    "Arabic": "كيف يمكنني تأسيس شركة في تونس؟",
}


def show_pieces(encoding: tiktoken.Encoding, text: str) -> list[str]:
    """Return the text piece of each token, to SEE how the text is cut."""
    token_ids = encoding.encode(text)
    # An Arabic letter can be split across several tokens (raw bytes),
    # so errors="replace" shows a placeholder character when a piece is incomplete.
    return [
        encoding.decode_single_token_bytes(t).decode("utf-8", errors="replace")
        for t in token_ids
    ]

def main() -> None:
    # cl100k_base is the tokenizer family used by GPT-3.5 / GPT-4.
    encoding = tiktoken.get_encoding("cl100k_base")

    print(f"{'Language':<10} {'Chars':>6} {'Tokens':>7} {'Chars/token':>12}")
    print("-" * 40)

    for language, text in SAMPLES.items():
        n_chars = len(text)
        n_tokens = len(encoding.encode(text))
        print(f"{language:<10} {n_chars:>6} {n_tokens:>7} {n_chars / n_tokens:>12.2f}")

    print("\nHow each sentence is cut into tokens:\n")
    for language, text in SAMPLES.items():
        print(f"[{language}] {show_pieces(encoding, text)}")


if __name__ == "__main__":
    main()