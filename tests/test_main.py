import pytest

from main import normalize_language


def test_normalize_language_full_names_and_codes():
    assert normalize_language("ukraina") == "uk"
    assert normalize_language("ukrainian") == "uk"
    assert normalize_language("english") == "en"
    assert normalize_language("uk") == "uk"
    assert normalize_language("en") == "en"


def test_normalize_language_rejects_unknown_language():
    with pytest.raises(ValueError):
        normalize_language("japanese")
