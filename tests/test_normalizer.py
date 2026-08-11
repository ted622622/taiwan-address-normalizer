from __future__ import annotations

import pytest

from taiwan_address_normalizer import (
    address_house_number,
    address_key,
    area_tokens,
    normalize,
    normalize_many,
    normalize_with_report,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (" 臺北市 大同區 延平北路二段57號 3樓 ", "台北市大同區延平北路2段57號3F"),
        ("11493台北市內湖區內湖路一段360巷15號8樓", "台北市內湖區內湖路1段360巷15號8F"),
        ("桃園縣八德市介壽路一段991號", "桃園市八德區介壽路1段991號"),
        ("台中縣大里市塗城路724號", "台中市大里區塗城路724號"),
        ("彰化縣員林鎮育英路28號", "彰化縣員林市育英路28號"),
        ("桃園市龜山區文化二路38-11號", "桃園市龜山區文化二路38-11號"),
        ("桃園市龜山區文化二路38－11號", "桃園市龜山區文化二路38-11號"),
        ("台中市台中港路三段107號", "台中市台灣大道3段107號"),
        ("新北市永和區褔和路158號", "新北市永和區福和路158號"),
    ],
)
def test_safe_normalization(source: str, expected: str) -> None:
    assert normalize(source) == expected


def test_safe_mode_preserves_multiple_destinations_and_floor_list() -> None:
    assert normalize("桃園縣八德市介壽路一段991、993號") == "桃園市八德區介壽路1段991、993號"
    assert normalize("屏東縣屏東市廣東路690號1、2樓") == "屏東縣屏東市廣東路690號1、2F"
    assert address_house_number("桃園縣八德市介壽路一段991、993號") == 991


def test_aggressive_mode_can_reduce_compound_destination() -> None:
    assert normalize("桃園縣八德市介壽路一段991、993號", mode="aggressive") == "桃園市八德區介壽路1段991號"


def test_only_aggressive_mode_interprets_hyphen_and_missing_house_marker() -> None:
    assert normalize("桃園市龜山區文化二路38-11號") == "桃園市龜山區文化二路38-11號"
    assert normalize("桃園市龜山區文化二路38-11號", mode="aggressive") == "桃園市龜山區文化二路38之11號"
    assert normalize("桃園市龜山區文化二路38") == "桃園市龜山區文化二路38"
    assert normalize("桃園市龜山區文化二路38", mode="aggressive") == "桃園市龜山區文化二路38號"


def test_aggressive_mode_can_infer_known_city_from_district() -> None:
    assert normalize("中壢市中美路51號2樓") == "中壢區中美路51號2F"
    assert normalize("中壢市中美路51號2樓", mode="aggressive") == "桃園市中壢區中美路51號2F"


def test_aggressive_mode_does_not_guess_ambiguous_district_city() -> None:
    assert normalize("東區大智路100號", mode="aggressive") == "東區大智路100號"
    assert normalize("大安區中山路100號", mode="aggressive") == "大安區中山路100號"


def test_aggressive_mode_preserves_explicit_city_for_ambiguous_district() -> None:
    assert normalize("台中市大安區中山路100號", mode="aggressive") == "台中市大安區中山路100號"


def test_aggressive_mode_interprets_hyphenated_house_number_as_subnumber() -> None:
    assert normalize("桃園縣八德市介壽路一段991-993號", mode="aggressive") == "桃園市八德區介壽路1段991之993號"


def test_safe_mode_preserves_basement_marker() -> None:
    assert normalize("台北市大安區忠孝東路四段50地下之2號") == "台北市大安區忠孝東路4段50地下之2號"
    assert normalize("台北市大安區忠孝東路四段50地下之2號", mode="aggressive") == "台北市大安區忠孝東路4段50之2號"


@pytest.mark.parametrize(
    "source",
    [
        "新北市五股區100巷5弄3號",
        "高雄市苓雅區500巷12弄8號",
        "台北市大安區106巷5弄3號",
    ],
)
def test_safe_mode_preserves_district_adjacent_lane_numbers(source: str) -> None:
    assert normalize(source) == source


def test_embedded_postal_code_before_named_road_is_removed() -> None:
    assert normalize("新北市三重區241忠孝路2號") == "新北市三重區忠孝路2號"


def test_long_digit_run_without_floor_marker_is_preserved() -> None:
    source = f"台北市大安區忠孝東路{('1' * 2000)}號"
    assert normalize(source) == source


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("台北市大安區忠孝東路四段一百號", "台北市大安區忠孝東路4段100號"),
        ("台北市大安區忠孝東路四段一百零二號", "台北市大安區忠孝東路4段102號"),
        ("台北市大安區忠孝東路四段一千二百三十四號", "台北市大安區忠孝東路4段1234號"),
    ],
)
def test_chinese_house_numbers(source: str, expected: str) -> None:
    assert normalize(source) == expected


def test_report_explains_completeness_without_claiming_existence() -> None:
    result = normalize_with_report("台北市大安區忠孝東路四段285號2樓")

    assert result.normalized == "台北市大安區忠孝東路4段285號2F"
    assert result.format_score == 100
    assert result.is_complete is True
    assert result.area_tokens == ("台北市", "大安區", "忠孝東路")
    assert result.warnings == ()


def test_report_flags_missing_parts_and_compound_house_numbers() -> None:
    incomplete = normalize_with_report("忠孝東路四段")
    compound = normalize_with_report("桃園市八德區介壽路一段991、993號")

    assert incomplete.is_complete is False
    assert "missing_city_or_county" in incomplete.warnings
    assert "missing_district" in incomplete.warnings
    assert "missing_house_number" in incomplete.warnings
    assert "multiple_house_numbers" in compound.warnings


def test_address_helpers() -> None:
    source = "台北市大同區延平北路二段57號3樓"

    assert area_tokens(source) == ["台北市", "大同區", "延平北路"]
    assert address_house_number(source) == 57
    assert address_key(source) == "台北市大同區延平北路2段"
    assert normalize_many([source, "桃園縣八德市介壽路一段991號"]) == [
        "台北市大同區延平北路2段57號3F",
        "桃園市八德區介壽路1段991號",
    ]


def test_invalid_mode_fails_closed() -> None:
    with pytest.raises(ValueError, match="mode"):
        normalize("台北市大安區忠孝東路四段285號", mode="guess")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("source", "expected_prefix"),
    [
        ("台北縣板橋市", "新北市板橋區"),
        ("桃園縣中壢市", "桃園市中壢區"),
        ("台中縣大里市", "台中市大里區"),
        ("台南縣新營市", "台南市新營區"),
        ("高雄縣鳳山市", "高雄市鳳山區"),
        ("彰化縣員林鎮", "彰化縣員林市"),
        ("苗栗縣頭份鎮", "苗栗縣頭份市"),
    ],
)
def test_historical_administrative_aliases(source: str, expected_prefix: str) -> None:
    assert normalize(f"{source}中山路1號").startswith(expected_prefix)


@pytest.mark.parametrize(
    "source",
    [
        "台北市大安區忠孝東路四段285號2樓",
        "新北市板橋區市府路1號",
        "桃園縣八德市介壽路一段991號",
        "11493台北市內湖區內湖路一段360巷15號8樓",
        "台中市台中港路三段107號",
        "屏東縣屏東市廣東路690號1、2樓",
        "桃園市龜山區文化二路38－11號",
    ],
)
def test_safe_normalization_is_idempotent(source: str) -> None:
    once = normalize(source)
    assert normalize(once) == once


def test_report_dict_is_json_serializable() -> None:
    import json

    payload = normalize_with_report("台北市大安區忠孝東路四段285號").as_dict()
    assert json.loads(json.dumps(payload, ensure_ascii=False))["is_complete"] is True
