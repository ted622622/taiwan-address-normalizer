from __future__ import annotations

import csv
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

ADDRESS_DATA = Path(__file__).resolve().parent / "data"

NormalizationMode = Literal["safe", "aggressive"]


@dataclass(frozen=True, slots=True)
class AddressResult:
    """Normalized text plus format-level signals.

    The score describes address completeness, not whether the address exists and
    not whether a geocoder will find it.
    """

    original: str
    normalized: str
    mode: NormalizationMode
    warnings: tuple[str, ...]
    area_tokens: tuple[str, ...]
    house_number: int | None
    format_score: int

    @property
    def is_complete(self) -> bool:
        return self.format_score == 100

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["is_complete"] = self.is_complete
        return payload


SECTION_ALIASES = {
    "一": "1",
    "二": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
    "十": "10",
}
ROAD_ALIASES = {
    "峨嵋街": "峨眉街",
    "台中港路": "台灣大道",
}
OMITTED_DISTRICT_MARKERS = {
    "台北市內湖": "台北市內湖區",
}
CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

TW_CITY_TOKENS = [
    "台北市",
    "新北市",
    "桃園市",
    "台中市",
    "台南市",
    "高雄市",
    "基隆市",
    "新竹市",
    "新竹縣",
    "苗栗縣",
    "彰化縣",
    "南投縣",
    "雲林縣",
    "嘉義市",
    "嘉義縣",
    "屏東縣",
    "宜蘭縣",
    "花蓮縣",
    "台東縣",
    "澎湖縣",
    "金門縣",
    "連江縣",
]
TAIWAN_CITY_NAMES = (
    "台北市",
    "臺北市",
    "新北市",
    "桃園市",
    "台中市",
    "臺中市",
    "台南市",
    "臺南市",
    "高雄市",
    "基隆市",
    "新竹市",
    "嘉義市",
    "新竹縣",
    "苗栗縣",
    "彰化縣",
    "南投縣",
    "雲林縣",
    "嘉義縣",
    "屏東縣",
    "宜蘭縣",
    "花蓮縣",
    "台東縣",
    "臺東縣",
    "澎湖縣",
    "金門縣",
    "連江縣",
)
DISTRICT_CITY_PREFIXES = {
    "三重區": "新北市",
    "板橋區": "新北市",
    "新莊區": "新北市",
    "中和區": "新北市",
    "永和區": "新北市",
    "中壢區": "桃園市",
    "桃園區": "桃園市",
    "豐原區": "台中市",
    "新營區": "台南市",
    "鳳山區": "高雄市",
    "林園區": "高雄市",
    "彰化市": "彰化縣",
    "員林市": "彰化縣",
    "南投市": "南投縣",
    "頭份市": "苗栗縣",
    "竹南鎮": "苗栗縣",
    "苗栗市": "苗栗縣",
    "通霄鎮": "苗栗縣",
    "竹東鎮": "新竹縣",
    "羅東鎮": "宜蘭縣",
    "宜蘭市": "宜蘭縣",
    "花蓮市": "花蓮縣",
    "馬公市": "澎湖縣",
    "金城鎮": "金門縣",
    "東港鎮": "屏東縣",
    "屏東市": "屏東縣",
    "台東市": "台東縣",
}


DISTRICT_CITY_PREFIXES.update(
    {
        "土城區": "新北市",
        "蘆洲區": "新北市",
        "新店區": "新北市",
        "樹林區": "新北市",
        "汐止區": "新北市",
        "淡水區": "新北市",
        "中山區": "台北市",
        "大安區": "台北市",
        "士林區": "台北市",
        "北投區": "台北市",
        "沙鹿區": "台中市",
        "后里區": "台中市",
        "潭子區": "台中市",
        "大甲區": "台中市",
        "大里區": "台中市",
        "太平區": "台中市",
        "大雅區": "台中市",
        "佳里區": "台南市",
        "永康區": "台南市",
        "大寮區": "高雄市",
        "苓雅區": "高雄市",
        "竹北市": "新竹縣",
        "西屯區": "台中市",
        "清水區": "台中市",
        "東區": "新竹市",
        "南港區": "台北市",
    }
)


def normalize(value: str, *, mode: NormalizationMode = "safe") -> str:
    """Normalize a Taiwan address without calling a geocoder.

    ``safe`` avoids guessing missing administrative areas or discarding extra
    destinations. ``aggressive`` mirrors a logistics-import workflow and may
    infer areas or keep only the first house number in a compound destination.
    """

    if mode not in ("safe", "aggressive"):
        raise ValueError("mode must be 'safe' or 'aggressive'")

    text = unicodedata.normalize("NFKC", value or "")
    text = text.replace("\u8914", "\u798f")
    text = text.strip()
    if not text:
        return ""

    text = text.replace("臺", "台").replace("巿", "市")
    text = _normalize_common_city_shorthand(text)
    text = re.sub(r"[\u3000\s]+", "", text)
    text = re.sub(r"^\d{3,5}-\d{1,3}(?=[\u4e00-\u9fff]{2,3}[市縣])", "", text)
    text = re.sub(r"^\d{3,5}(?=[\u4e00-\u9fff]{2,3}[市縣])", "", text)
    text = _strip_leading_postal_before_known_area(text)
    if mode == "aggressive":
        text = _normalize_multi_house_numbers(text)
    text = re.sub(r"(?<=\d)[,，](?=\d)", "、", text)
    text = re.sub(r"(?<!\d)[,，]|[,，](?!\d)", "", text)

    for source, target in county_aliases().items():
        text = text.replace(source, target)
    text = text.replace("桃園市桃園市", "桃園市桃園區")
    for source, target in city_aliases().items():
        text = text.replace(source, target)
    for source, target in district_aliases().items():
        text = text.replace(source, target)

    if mode == "aggressive":
        text = _normalize_known_business_area_districts(text)
        text = _restore_omitted_district_marker(text)
        text = _prefix_city_for_known_leading_district(text)
        text = _normalize_city_name_before_known_district(text)
        text = _restore_omitted_district_after_city(text)
        text = _restore_county_district_with_extra_road_marker(text)
        text = _normalize_city_district_conflicts(text)
        text = _normalize_district_extra_city_marker(text)
    text = _strip_embedded_postal_codes(text)
    if mode == "aggressive":
        text = _strip_non_admin_area_markers_before_road(text)
    text = _normalize_road_aliases(text)
    if mode == "aggressive":
        text = _strip_village_between_district_and_road(text)
        text = _strip_village_after_city_when_district_omitted(text)
    text = _normalize_redundant_road_section_marker(text)
    if mode == "aggressive":
        text = _normalize_basement_house_suffix(text)
    text = _normalize_sections(text)
    text = _normalize_chinese_house_numbers(text)
    text = _normalize_floor(text)
    if mode == "aggressive":
        text = _normalize_number_suffix(text)
        text = _normalize_missing_house_number_marker(text)
    return text


def normalize_many(values: Iterable[str], *, mode: NormalizationMode = "safe") -> list[str]:
    return [normalize(value, mode=mode) for value in values]


def area_tokens(value: str, *, mode: NormalizationMode = "safe") -> list[str]:
    normalized = normalize(value, mode=mode)
    tokens: list[str] = []
    city_token = ""
    for city in TW_CITY_TOKENS:
        if city in normalized:
            city_token = city
            tokens.append(city)
            break
    district_source = normalized.replace(city_token, "", 1) if city_token else normalized
    known_district = _leading_known_district(district_source)
    if known_district:
        tokens.append(known_district)
    else:
        district = re.search(r"([\u4e00-\u9fff]{1,5}[\u5340\u9109\u93ae\u5e02])", district_source)
        if district and not _is_non_admin_area_marker(district.group(1)):
            tokens.append(district.group(1))
    road = _road_token(normalized)
    if road:
        tokens.append(road)
    return tokens


def address_house_number(value: str, *, mode: NormalizationMode = "safe") -> int | None:
    normalized = normalize(value, mode=mode)
    compound = re.search(r"(\d+)(?:之\d+)?(?=\s*[/／、~～]\s*\d+)", normalized)
    if compound:
        return int(compound.group(1))
    matches = list(re.finditer(r"(\d+)(?:\u4e4b\d+)?\u865f", normalized))
    if not matches:
        return None
    return int(matches[0].group(1))


def address_key(value: str, *, mode: NormalizationMode = "safe") -> str:
    normalized = normalize(value, mode=mode)
    normalized = re.sub(r"([市縣])\d{3}(?=[\u4e00-\u9fff]{1,5}[區鄉鎮市])", r"\1", normalized)
    normalized = re.sub(r"\d+(?:[.．、,，]\d+)*(?:之\d+)?號.*$", "", normalized)
    normalized = re.sub(r"(?:地下)?(?:\d+(?:[-~]\d+)?F|[一二三四五六七八九十]+樓).*$", "", normalized)
    return normalized


def normalize_with_report(value: str, *, mode: NormalizationMode = "safe") -> AddressResult:
    """Normalize and return format warnings suitable for import previews."""

    original = value or ""
    normalized = normalize(original, mode=mode)
    tokens = tuple(area_tokens(normalized, mode="safe"))
    house_number = address_house_number(normalized, mode="safe")
    warnings: list[str] = []

    if not normalized:
        warnings.append("empty_address")
    elif not _contains_cjk(normalized):
        warnings.append("not_traditional_chinese_address")

    city = _city_token(normalized)
    district = _district_token(normalized, city)
    road = _road_token(normalized)
    if not city:
        warnings.append("missing_city_or_county")
    if not district:
        warnings.append("missing_district")
    if not road:
        warnings.append("missing_road_or_street")
    if house_number is None:
        warnings.append("missing_house_number")
    if re.search(r"\d+(?:之\d+)?\s*[/／、~～]\s*\d+", unicodedata.normalize("NFKC", original)):
        warnings.append("multiple_house_numbers")
    if mode == "aggressive" and normalized != normalize(original, mode="safe"):
        warnings.append("aggressive_rules_applied")

    score = sum((25 if city else 0, 25 if district else 0, 25 if road else 0, 25 if house_number is not None else 0))
    return AddressResult(
        original=original,
        normalized=normalized,
        mode=mode,
        warnings=tuple(warnings),
        area_tokens=tokens,
        house_number=house_number,
        format_score=score,
    )


def _district_token(value: str, city: str | None) -> str | None:
    source = value.replace(city, "", 1) if city else value
    known = _leading_known_district(source)
    if known:
        return known
    match = re.search(r"([\u4e00-\u9fff]{1,6}[區鄉鎮市])", source)
    if match and not _is_non_admin_area_marker(match.group(1)):
        return match.group(1)
    return None


def _road_token(value: str) -> str | None:
    city = _city_token(value)
    source = value.replace(city, "", 1) if city else value
    district = _district_token(value, city)
    if district and source.startswith(district):
        source = source[len(district) :]
    match = re.match(r"([\u4e00-\u9fff0-9]{1,16}(?:大道|路|街))", source)
    return match.group(1) if match else None


NON_ADMIN_AREA_MARKERS = {
    "\u5712\u5340",
    "\u5de5\u696d\u5340",
    "\u79d1\u5b78\u5712\u5340",
    "\u79d1\u5b78\u5de5\u696d\u5712\u5340",
    "\u5357\u6e2f\u79d1\u5b78\u5712\u5340",
}


def _is_non_admin_area_marker(value: str) -> bool:
    return value in NON_ADMIN_AREA_MARKERS or value.endswith("\u5de5\u696d\u5712\u5340")


def _normalize_known_business_area_districts(text: str) -> str:
    replacements = (
        ("\u53f0\u5317\u5e02\u5357\u6e2f\u79d1\u5b78\u5712\u5340", "\u53f0\u5317\u5e02\u5357\u6e2f\u5340"),
        ("\u53f0\u5317\u5e02\u5712\u5340\u8857", "\u53f0\u5317\u5e02\u5357\u6e2f\u5340\u5712\u5340\u8857"),
        ("\u65b0\u7af9\u5e02\u79d1\u5b78\u5de5\u696d\u5712\u5340", "\u65b0\u7af9\u5e02\u6771\u5340"),
    )
    for source, target in replacements:
        if text.startswith(source):
            return f"{target}{text[len(source) :]}"
    taichung = "\u53f0\u4e2d\u5e02"
    if re.match(
        r"^\u53f0\u4e2d\u5e02\u5de5\u696d\u5340[\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\d]+\u8def",
        text,
    ):
        return f"\u53f0\u4e2d\u5e02\u897f\u5c6f\u5340{text[len(taichung) :]}"
    return text


def _leading_known_district(value: str) -> str | None:
    for district in sorted(DISTRICT_CITY_PREFIXES, key=len, reverse=True):
        if value.startswith(district):
            return district
    return None


def _city_token(value: str) -> str | None:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = normalized.replace("\u81fa", "\u53f0")
    for city in TAIWAN_CITY_NAMES:
        city_normalized = unicodedata.normalize("NFKC", city).replace("\u81fa", "\u53f0")
        if city_normalized in normalized:
            return city_normalized
    return None


def _normalize_sections(text: str) -> str:
    for source, target in SECTION_ALIASES.items():
        text = re.sub(rf"{source}段", f"{target}段", text)
    return text


def _normalize_common_city_shorthand(text: str) -> str:
    text = re.sub(
        r"^\u5317\u5e02(?=[\u4e00-\u9fff0-9]{2,12}[\u8def\u8857\u5927\u9053\u5340])", "\u53f0\u5317\u5e02", text
    )
    text = re.sub(r"^\u53f0\u5317(?!\u5e02)(?=[\u4e00-\u9fff]{1,6}\u5340)", "\u53f0\u5317\u5e02", text)
    text = re.sub(r"^\u81fa\u5317(?!\u5e02)(?=[\u4e00-\u9fff]{1,6}\u5340)", "\u53f0\u5317\u5e02", text)
    return text


def _strip_leading_postal_before_known_area(text: str) -> str:
    return re.sub(
        r"^\d{3}(?=[\u4e00-\u9fff]{1,8}[\u5340\u9109\u93ae\u5e02])",
        "",
        text,
    )


def _normalize_city_name_before_known_district(text: str) -> str:
    if any(city in text for city in TAIWAN_CITY_NAMES):
        return text
    for district, city in DISTRICT_CITY_PREFIXES.items():
        if city.endswith("\u5e02") and text.startswith(f"{city[:-1]}{district}"):
            return f"{city}{text[len(city) - 1 :]}"
    return text


AMBIGUOUS_CITY_DISTRICT_NAMES = {
    "\u5927\u5b89\u5340",
    "\u6771\u5340",
    "\u897f\u5340",
    "\u5357\u5340",
    "\u5317\u5340",
    "\u4e2d\u5340",
    "\u4e2d\u5c71\u5340",
    "\u4e2d\u6b63\u5340",
    "\u4fe1\u7fa9\u5340",
}


def _normalize_city_district_conflicts(text: str) -> str:
    for district, city in DISTRICT_CITY_PREFIXES.items():
        if district in AMBIGUOUS_CITY_DISTRICT_NAMES:
            continue
        match = re.match(rf"^([\u4e00-\u9fff]{{2,3}}[\u5e02\u7e23]){re.escape(district)}", text)
        if match and match.group(1) != city:
            return f"{city}{text[len(match.group(1)) :]}"
    return text


def _restore_omitted_district_after_city(text: str) -> str:
    for district, city in sorted(DISTRICT_CITY_PREFIXES.items(), key=lambda item: len(item[0]), reverse=True):
        if not district.endswith(("\u5340", "\u9109", "\u93ae", "\u5e02")):
            continue
        stem = district[:-1]
        if len(stem) < 2:
            continue
        pattern = rf"^{re.escape(city + stem)}(?![\u5340\u9109\u93ae\u5e02\u8def\u8857\u5df7\u5f04\u6771\u897f\u5357\u5317])(?=[\u4e00-\u9fff0-9]{{1,12}}(?:\u5927\u9053|\u8def|\u8857|\u5df7|\u5f04))"
        text = re.sub(pattern, f"{city}{district}", text, count=1)
    return text


def _restore_county_district_with_extra_road_marker(text: str) -> str:
    for district, city in sorted(DISTRICT_CITY_PREFIXES.items(), key=lambda item: len(item[0]), reverse=True):
        if not city.endswith("\u7e23") or not district.endswith(("\u5e02", "\u93ae", "\u9109", "\u5340")):
            continue
        stem = district[:-1]
        if len(stem) < 2:
            continue
        pattern = rf"^{re.escape(city + stem)}[\u8def\u8857](?=[\u4e00-\u9fff0-9]{{1,12}}(?:\u5927\u9053|\u8def|\u8857|\u5df7|\u5f04))"
        text = re.sub(pattern, f"{city}{district}", text, count=1)
    return text


def _normalize_district_extra_city_marker(text: str) -> str:
    return re.sub(
        r"([\u4e00-\u9fff]{1,8}\u5340)\u5e02(?![\u6c11\u653f\u5e9c])(?=[\u4e00-\u9fff0-9]{1,12}(?:\u5927\u9053|\u8def|\u8857|\u5df7|\u5f04))",
        r"\1",
        text,
    )


NON_ADMIN_AREA_MARKERS_BEFORE_ROAD = (
    "\u79d1\u5b78\u5de5\u696d\u5712\u5340",
    "\u79d1\u5b78\u5712\u5340",
    "\u4e94\u80a1\u5de5\u696d\u5340",
    "\u5927\u767c\u5de5\u696d\u5340",
    "\u81e8\u6d77\u5de5\u696d\u5340",
    "\u65b0\u7af9\u5de5\u696d\u5340",
    "\u53f0\u4e2d\u52a0\u5de5\u51fa\u53e3\u5340",
    "\u4e2d\u6e2f\u52a0\u5de5\u51fa\u53e3\u5340",
    "\u9ad8\u96c4\u52a0\u5de5\u51fa\u53e3\u5340",
    "\u52a0\u5de5\u51fa\u53e3\u5340",
)


def _strip_non_admin_area_markers_before_road(text: str) -> str:
    for marker in sorted(NON_ADMIN_AREA_MARKERS_BEFORE_ROAD, key=len, reverse=True):
        text = re.sub(
            rf"([\u4e00-\u9fff]{{2,3}}[\u5e02\u7e23][\u4e00-\u9fff]{{1,8}}[\u5340\u9109\u93ae\u5e02]){re.escape(marker)}(?=[\u4e00-\u9fff0-9]{{1,12}}(?:\u5927\u9053|\u8def|\u8857|\u5df7|\u5f04))",
            r"\1",
            text,
        )
    return text


def _strip_embedded_postal_codes(text: str) -> str:
    text = re.sub(
        r"([\u4e00-\u9fff]{2,3}[\u5e02\u7e23])\d{3}(?=[\u4e00-\u9fff]{1,6}[\u5340\u9109\u93ae\u5e02])",
        r"\1",
        text,
    )
    return re.sub(
        r"([\u4e00-\u9fff]{1,6}[\u5340\u9109\u93ae\u5e02])\d{3}(?=[\u4e00-\u9fff0-9]{1,12}(?:\u5927\u9053|\u8def|\u8857|\u5df7|\u5f04))",
        r"\1",
        text,
    )


def _normalize_road_aliases(text: str) -> str:
    for source, target in ROAD_ALIASES.items():
        text = text.replace(source, target)
    text = re.sub(r"^台中市中港路", "台中市台灣大道", text)
    return text


def _restore_omitted_district_marker(text: str) -> str:
    for source, target in OMITTED_DISTRICT_MARKERS.items():
        text = re.sub(rf"^{re.escape(source)}(?!區)(?=[\u4e00-\u9fff0-9]{{1,12}}[路街大道])", target, text)
    return text


def _normalize_floor(text: str) -> str:
    text = re.sub(r"(\d+)[-~](\d+)樓", r"\1-\2F", text)
    return re.sub(r"(\d+)樓", r"\1F", text)


def _strip_village_between_district_and_road(text: str) -> str:
    text = re.sub(
        r"([縣市][\u4e00-\u9fff]{1,6}[區鄉鎮市])[\u4e00-\u9fff]{1,8}[村里]\d{1,3}鄰(?=[\u4e00-\u9fff0-9]{2,12}[路街大道])",
        r"\1",
        text,
    )
    text = re.sub(
        r"([縣市][\u4e00-\u9fff]{1,6}[區鄉鎮市])\d{1,3}鄰(?=[\u4e00-\u9fff0-9]{2,12}[路街大道])",
        r"\1",
        text,
    )
    return re.sub(
        r"([縣市][\u4e00-\u9fff]{1,6}[區鄉鎮市])[\u4e00-\u9fff]{1,8}[村里](?=[\u4e00-\u9fff0-9]{2,12}[路街大道])",
        r"\1",
        text,
    )


def _strip_village_after_city_when_district_omitted(text: str) -> str:
    return re.sub(
        r"^([\u4e00-\u9fff]{2,3}[市縣])[\u4e00-\u9fff]{1,8}[村里](?![區鄉鎮市])(?=[\u4e00-\u9fff0-9]{2,12}[路街大道])",
        r"\1",
        text,
    )


def _normalize_redundant_road_section_marker(text: str) -> str:
    return re.sub(r"([路街大道])段([一二三四五六七八九十\d]+段)", r"\1\2", text)


def _normalize_basement_house_suffix(text: str) -> str:
    text = re.sub(r"(\d+)地下之(\d+)號", r"\1之\2號", text)
    return re.sub(r"(\d+)地下室之(\d+)號", r"\1之\2號", text)


def _prefix_city_for_known_leading_district(text: str) -> str:
    if any(city.replace("臺", "台") in text for city in TAIWAN_CITY_NAMES):
        return text
    for district, city in DISTRICT_CITY_PREFIXES.items():
        if district in AMBIGUOUS_CITY_DISTRICT_NAMES:
            continue
        if re.match(rf"^{re.escape(district)}[\u4e00-\u9fff0-9]{{1,12}}[路街大道]", text):
            return f"{city}{text}"
    return text


def _normalize_multi_house_numbers(text: str) -> str:
    house = r"\d+(?:\s*(?:\u4e4b|-)\s*\d+)?"

    def first_house(match: re.Match[str]) -> str:
        value = re.sub(r"\s+", "", match.group(1))
        return f"{value}\u865f"

    text = re.sub(
        rf"({house})(?:(?:\s*[/\uff0f,\uff0c\u3001~\uff5e]\s*{house})|(?:\s*\u53ca\s*(?:{house}|-?\d+|\u4e4b?\d+)))+\s*\u865f",
        first_house,
        text,
    )
    text = re.sub(
        r"(\d+)\s*[/\uff0f,\uff0c\u3001]\s*\d+(?:\s*[/\uff0f,\uff0c\u3001]\s*\d+)*\s*\u865f",
        lambda match: f"{match.group(1)}\u865f",
        text,
    )
    return re.sub(
        r"(\d+)\s*[/\uff0f,\uff0c\u3001]\s*\d+(?:\s*[/\uff0f,\uff0c\u3001]\s*\d+)*$",
        lambda match: f"{match.group(1)}\u865f",
        text,
    )


def _normalize_number_suffix(text: str) -> str:
    text = re.sub(r"(\d+)[\-‐‑‒–—―─－](\d+)號", r"\1之\2號", text)
    text = re.sub(r"(\d+)號之(\d+)", r"\1之\2號", text)
    return text


def _normalize_chinese_house_numbers(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        prefix = match.group(1)
        number = _chinese_house_number_to_int(match.group(2))
        if number is None:
            return match.group(0)
        return f"{prefix}{number}號"

    return re.sub(r"([路街大道巷弄段])([零〇一二三四五六七八九十百千]{1,8})號", replace, text)


def _normalize_missing_house_number_marker(text: str) -> str:
    text = re.sub(r"([路街大道巷弄]\d+(?:段)?)(\d+)-(\d+)$", r"\1\2之\3號", text)
    text = re.sub(
        r"([路街大道巷弄]\d+(?:段)?)(\d+)之([零〇一二三四五六七八九十百]+)$",
        lambda match: _replace_chinese_sub_house(match),
        text,
    )
    return re.sub(r"([路街大道巷弄]\d+(?:段)?)(\d+)$", r"\1\2號", text)


def _replace_chinese_sub_house(match: re.Match[str]) -> str:
    sub_number = _chinese_house_number_to_int(match.group(3))
    if sub_number is None:
        return match.group(0)
    return f"{match.group(1)}{match.group(2)}之{sub_number}號"


def _chinese_house_number_to_int(value: str) -> int | None:
    if not value:
        return None
    if all(char in CHINESE_DIGITS for char in value):
        return int("".join(str(CHINESE_DIGITS[char]) for char in value))
    units = {"十": 10, "百": 100, "千": 1000}
    total = 0
    current = 0
    for char in value:
        if char in CHINESE_DIGITS:
            current = CHINESE_DIGITS[char]
            continue
        unit = units.get(char)
        if unit is None:
            return None
        total += (current or 1) * unit
        current = 0
    return total + current


def _contains_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


@lru_cache
def county_aliases() -> dict[str, str]:
    return _load_aliases("taiwan_county_aliases.csv")


@lru_cache
def city_aliases() -> dict[str, str]:
    return _load_aliases("taiwan_city_aliases.csv")


@lru_cache
def district_aliases() -> dict[str, str]:
    return _load_aliases("taiwan_district_aliases.csv")


def _load_aliases(file_name: str) -> dict[str, str]:
    path = ADDRESS_DATA / file_name
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {
            row["source"].strip(): row["target"].strip()
            for row in csv.DictReader(handle)
            if row.get("source") and row.get("target")
        }
