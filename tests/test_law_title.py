"""Tests for header removal and law title propagation."""
from app.ingestion.pdf_loader import PageText, strip_repeated_lines
from app.ingestion.pipeline import law_titles_by_page


def _page(number: int, text: str, header: str | None = None) -> PageText:
    return PageText("doc_fr.pdf", number, text, "fr", header)


def test_law_titles_are_carried_forward() -> None:
    pages = [
        _page(1, "a"),
        _page(2, "b", header="LOI A"),
        _page(3, "c"),
        _page(4, "d", header="LOI B"),
        _page(5, "e"),
    ]
    assert law_titles_by_page(pages) == [None, "LOI A", "LOI A", "LOI B", "LOI B"]


def test_repeated_header_and_footer_are_removed_and_header_is_kept() -> None:
    pages = [
        _page(n, f"LOI N°60-30 DU 1960\nArt.{n}.- texte de l'article\nFOOTER/XX")
        for n in range(1, 11)
    ]
    cleaned = strip_repeated_lines(pages)
    assert len(cleaned) == 10
    for page in cleaned:
        assert page.header == "LOI N°60-30 DU 1960"
        assert "FOOTER" not in page.text
        assert "LOI N°60-30" not in page.text
        assert page.text.startswith("Art.")  # the article heading is protected content

def test_banner_is_removed_but_not_kept_as_title() -> None:
    pages = [
        _page(n, f"BANNIERE DU PROJET\nArt.{n}.- texte de l'article") for n in range(1, 11)
    ]
    cleaned = strip_repeated_lines(pages)
    assert all("BANNIERE" not in page.text for page in cleaned)
    assert all(page.header is None for page in cleaned)