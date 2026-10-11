"""Simple tests for the cleaning rules in app/ingestion/pdf_loader.py.

Run from the project root (venv activated):
    python -m pytest tests -v
"""
from pathlib import Path

import pytest

from app.ingestion.pdf_loader import clean_text, language_from_filename


def test_nfkc_turns_arabic_presentation_forms_into_normal_letters() -> None:
    # "ﺍﻟﻔﺼل" is written with presentation forms; it must become "الفصل".
    assert clean_text("ﺍﻟﻔﺼل 5") == "الفصل 5"


def test_garbage_characters_are_removed() -> None:
    assert clean_text("abc\ue821def\ufffd") == "abcdef"


def test_arabic_diacritics_and_space_before_them_are_removed() -> None:
    assert clean_text("تسل ّط") == "تسلط"


def test_french_hyphenated_word_is_rejoined() -> None:
    assert clean_text("les condi-\ntions de travail") == "les conditions de travail"


def test_punctuation_only_lines_are_dropped() -> None:
    assert clean_text("première ligne\n.\n:\nseconde ligne") == "première ligne\nseconde ligne"


def test_extra_spaces_are_collapsed() -> None:
    assert clean_text("a    b \t c") == "a b c"


def test_lone_page_number_on_first_line_is_removed() -> None:
    assert clean_text("71\nالفصل 174\nنص") == "الفصل 174\nنص"


def test_number_inside_a_line_is_kept() -> None:
    assert clean_text("237 ANNEXES A LA LOI") == "237 ANNEXES A LA LOI"


def test_language_is_read_from_file_name() -> None:
    assert language_from_filename(Path("code_du_travail_ar_2004.pdf")) == "ar"
    assert language_from_filename(Path("cnss_textes_fr_2007.pdf")) == "fr"


def test_file_name_without_language_raises_an_error() -> None:
    with pytest.raises(ValueError):
        language_from_filename(Path("document.pdf"))