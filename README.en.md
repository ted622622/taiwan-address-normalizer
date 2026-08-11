# Taiwan Address Normalizer

A zero-runtime-dependency Python library for normalizing Taiwan addresses in logistics, CRM, e-commerce, and data-import workflows.

This project normalizes address text. It is **not** a geocoder, does not bundle coordinates, and does not claim that an address exists.

## Highlights

- Traditional Chinese glyph, Unicode width, and whitespace normalization
- Historical county/city/district aliases
- Taiwan postal-code removal
- Section, floor, basement, and house-number normalization
- Safe and explicit aggressive modes
- Format completeness report with stable warning codes
- UTF-8 CSV batch CLI

## Install

Before the first PyPI release:

```bash
pip install git+https://github.com/ted622622/taiwan-address-normalizer.git
```

After the package is published on PyPI:

```bash
pip install taiwan-address-normalizer
```

```python
from taiwan_address_normalizer import normalize, normalize_with_report

normalize(" 臺北市 大同區 延平北路二段57號 3樓 ")
# '台北市大同區延平北路2段57號3F'

normalize_with_report("忠孝東路四段").warnings
# ('missing_city_or_county', 'missing_district', 'missing_house_number')
```

## CLI

```bash
tw-address normalize "臺北市 大安區 忠孝東路四段285號2樓"
tw-address batch orders.csv --column 地址 --output orders.normalized.csv
```

The CSV command emits UTF-8 with BOM and escapes spreadsheet-formula prefixes by default. Use `--allow-formulas` only for trusted input.

See the [Traditional Chinese README](README.md) for full usage and limitations.

## License

MIT. The package contains no customer records, coordinates, TGOS data, or paid-provider responses.

Built from address-import experience in [Shunluwang](https://route.runly-ai.com/), a Taiwan delivery route-planning SaaS.
