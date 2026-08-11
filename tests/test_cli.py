from __future__ import annotations

import csv
import json
from pathlib import Path

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
