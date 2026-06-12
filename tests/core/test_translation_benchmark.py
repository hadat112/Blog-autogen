from application.translation_benchmark_service import score_translation


def test_score_translation_accepts_structurally_complete_output():
    source = "First paragraph has $25 and 2024.\n\nSecond paragraph has 19 items."
    output = "Primo paragrafo ha $25 e 2024.\n\nSecondo paragrafo ha 19 elementi."

    result = score_translation(source, output)

    assert result["valid"] is True
    assert result["paragraph_score"] == 1
    assert result["number_score"] == 1
    assert result["score"] >= 90


def test_score_translation_rejects_refusal():
    result = score_translation(
        "A complete source paragraph that should be translated.",
        "I'm sorry, but I can't provide copyrighted text.",
    )

    assert result["valid"] is False
    assert result["score"] <= 49
    assert "Model returned refusal or policy text" in result["warnings"]


def test_score_translation_warns_when_numbers_change():
    result = score_translation(
        "The train left at 7:35 with 216 passengers.",
        "Il treno partì alle 8:00 con 200 passeggeri.",
    )

    assert result["number_score"] == 0
    assert any("numbers" in warning for warning in result["warnings"])
