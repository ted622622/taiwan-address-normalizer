from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from taiwan_address_normalizer.cli import main


def test_normalize_json_cli(capsys: object) -> None:
    assert main(["normalize", "臺北市 大安區 忠孝東路四段285號2樓", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert payload["normalized"] == "台北市大安區忠孝東路4段285號2F"
    assert payload["format_score"] == 100


def test_batch_cli_preserves_source_and_adds_result(tmp_path: Path) -> None:
    source = tmp_path / "orders.csv"
    target = tmp_path / "orders.normalized.csv"
    with source.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["姓名", "地址"])
        writer.writeheader()
        writer.writerow({"姓名": '=HYPERLINK("https://example.invalid")', "地址": "桃園縣八德市介壽路一段991號"})
        writer.writerow({"姓名": "待確認", "地址": "忠孝東路四段"})

    assert main(["batch", str(source), "--column", "地址", "--output", str(target)]) == 0

    with target.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["地址"] == "桃園縣八德市介壽路一段991號"
    assert rows[0]["姓名"].startswith("'=")
    assert rows[0]["normalized_address"] == "桃園市八德區介壽路1段991號"
    assert "missing_city_or_county" in rows[1]["address_warnings"]


def test_batch_cli_rejects_extra_columns_without_partial_output(tmp_path: Path) -> None:
    source = tmp_path / "ragged.csv"
    target = tmp_path / "ragged.normalized.csv"
    source.write_text("地址,姓名\n台北市大安區忠孝東路1號,甲,多餘\n", encoding="utf-8-sig")

    with pytest.raises(SystemExit, match="Row 2 has more columns than the header"):
        main(["batch", str(source), "--column", "地址", "--output", str(target)])

    assert not target.exists()


def test_batch_cli_rejects_reserved_output_columns(tmp_path: Path) -> None:
    source = tmp_path / "conflict.csv"
    target = tmp_path / "conflict.normalized.csv"
    source.write_text("地址,normalized_address\n台北市大安區忠孝東路1號,舊值\n", encoding="utf-8-sig")

    with pytest.raises(SystemExit, match="Output column already exists: normalized_address"):
        main(["batch", str(source), "--column", "地址", "--output", str(target)])

    assert not target.exists()


def test_batch_cli_rejects_duplicate_columns(tmp_path: Path) -> None:
    source = tmp_path / "duplicate.csv"
    target = tmp_path / "duplicate.normalized.csv"
    source.write_text("地址,地址\n台北市大安區忠孝東路1號,錯誤覆蓋值\n", encoding="utf-8-sig")

    with pytest.raises(SystemExit, match="Duplicate CSV columns are not allowed: 地址"):
        main(["batch", str(source), "--column", "地址", "--output", str(target)])

    assert not target.exists()
