import pytest

from core.run_options import RunOptions, parse_run_tokens


def test_parse_tokens_with_limit_and_with_image():
    opts = parse_run_tokens(["--limit", "3", "--with-image"])
    assert opts.limit == 3
    assert opts.with_image is True
    assert opts.no_image is False


def test_parse_tokens_with_no_image():
    opts = parse_run_tokens(["--no-image"])
    assert opts.no_image is True
    assert opts.with_image is False


def test_parse_conflicting_image_flags_raises():
    with pytest.raises(ValueError):
        parse_run_tokens(["--with-image", "--no-image"])


def test_effective_enable_image_from_flags_and_default():
    opts = RunOptions(limit=None, threads=5, language="uk", debug=False, update=False, with_image=False, no_image=True)
    assert opts.resolve_enable_image(default_from_config=True) is False


def test_parse_tokens_supports_update_flag():
    opts = parse_run_tokens(["--update", "--limit", "1"])
    assert opts.update is True
    assert opts.limit == 1


def test_parse_tokens_supports_crawl_article_url():
    opts = parse_run_tokens(["--crawl", "https://example.com/article"])
    assert opts.crawl_url == "https://example.com/article"



def test_parse_tokens_supports_lang_alias():
    opts = parse_run_tokens(["--lang", "Vietnamese"])
    assert opts.language == "Vietnamese"


def test_parse_tokens_defaults_language_to_ukraina():
    opts = parse_run_tokens([])
    assert opts.language == "Ukraina"

