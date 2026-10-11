"""Measure retrieval quality: did the right chunk come back, and at which rank?

Ground truth is simple: for each test question we list words that MUST appear in the
right chunk. A search "hits at rank r" if the r-th result contains all of them.
"""
import unicodedata


def normalize(text: str) -> str:
    """Unicode NFKC, lower case, single spaces: '55  ans' matches '55 ans'."""
    return " ".join(unicodedata.normalize("NFKC", text).lower().split())


def first_hit_rank(contents: list[str], keywords: list[str]) -> int | None:
    """1-based rank of the first chunk containing ALL keywords, or None if no chunk does."""
    wanted = [normalize(keyword) for keyword in keywords]
    for rank, content in enumerate(contents, start=1):
        text = normalize(content)
        if all(keyword in text for keyword in wanted):
            return rank
    return None


def hit_rate(ranks: list[int | None], k: int) -> float:
    """Share of questions whose right chunk is in the top k (hit@k)."""
    if not ranks:
        return 0.0
    return sum(1 for r in ranks if r is not None and r <= k) / len(ranks)


def mean_reciprocal_rank(ranks: list[int | None]) -> float:
    """Average of 1/rank (0 when not found): 1.0 = always first, 0.5 = typically second."""
    if not ranks:
        return 0.0
    return sum(1 / r for r in ranks if r is not None) / len(ranks)


def build_report(
    questions: list[dict], ranks: dict[str, list[int | None]], k_values: tuple[int, ...] = (1, 3, 5)
) -> str:
    """Markdown report: scores per config and language, then the rank of every question."""
    header = "".join(f" hit@{k} |" for k in k_values)
    lines = [
        "## Scores by chunking configuration",
        "",
        f"| config | language | questions |{header} MRR |",
        "|---|---|---:|" + "---:|" * (len(k_values) + 1),
    ]
    for config, config_ranks in ranks.items():
        for language in ("fr", "ar", "all"):
            selected = [
                r for q, r in zip(questions, config_ranks) if language == "all" or q["language"] == language
            ]
            if not selected:
                continue
            rates = "".join(f" {hit_rate(selected, k):.0%} |" for k in k_values)
            lines.append(
                f"| {config} | {language} | {len(selected)} |{rates} {mean_reciprocal_rank(selected):.2f} |"
            )

    lines += ["", "## Rank of the right chunk per question ('-' = not found)", ""]
    lines.append("| id | language | " + " | ".join(ranks) + " |")
    lines.append("|---|---|" + "---:|" * len(ranks))
    for index, question in enumerate(questions):
        cells = " | ".join(str(r[index]) if r[index] is not None else "-" for r in ranks.values())
        lines.append(f"| {question['id']} | {question['language']} | {cells} |")
    return "\n".join(lines) + "\n"