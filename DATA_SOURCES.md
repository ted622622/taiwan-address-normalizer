# Data Sources and Provenance

## Included data

This repository includes three small, manually maintained CSV tables:

- historical county aliases
- common city glyph/name aliases
- historical township/city names that became districts after municipal reorganization

They contain administrative names only. They do not contain addresses, house numbers, coordinates, customer records, provider responses, or a geocoding baseline.

Current administrative names can be checked against Taiwan's Ministry of the Interior / National Land Surveying and Mapping Center code services:

- [Township and district list (land administration)](https://data.gov.tw/dataset/102013)
- [Township and district list (household registration)](https://data.gov.tw/dataset/102011)
- [Administrative-region place-name data](https://data.gov.tw/dataset/40281)

The linked government datasets are references, not vendored files. This package does not redistribute those datasets.

## Code provenance

The normalization implementation was extracted and generalized from Shunluwang's Taiwan delivery-import workflow. It uses Python's standard library only.

Other open-source projects were reviewed during design research, but their code and data are not bundled in this repository. Any future contribution derived from another project must document the source and compatible license in the pull request.

