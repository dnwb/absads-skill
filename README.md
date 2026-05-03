# absads

`absads` is an agent skill for astrophysics and astronomy literature research using ADS/SciX as the primary metadata source and arXiv as the source-package fallback.

It includes:

- a reusable skill definition in `SKILL.md`
- an API reference in `references/api.md`
- a helper CLI in `scripts/ads_scix.py`
- offline tests in `tests/test_ads_scix.py`

## What it supports

- literature search with ADS query syntax
- bibcode, DOI, and arXiv ID lookup
- citation export
- citation metrics
- arXiv source download and extraction
- ADS library workflows
- author-affiliation workflows
- SciX compatibility guidance

## Requirements

- Python 3
- `ADS_API_KEY` or `SCIX_API_KEY` set in the environment

Optional:

- `ADS_BASE_URL` if you need to override the default ADS API host

## Security rules

- Never write API keys into files
- Never print tokens into logs or terminal output
- Prefer `ADS_API_KEY`, with `SCIX_API_KEY` as fallback
- Treat SciX as ADS-compatible unless official SciX-specific docs are verified

## Quick start

### Search literature

```bash
python ~/.agents/skills/absads/scripts/ads_scix.py search 'author:"Hubble" year:1929' --rows 5
```

### Export BibTeX

```bash
python ~/.agents/skills/absads/scripts/ads_scix.py export bibtex 1929PNAS...15..168H
```

### Fetch metrics

```bash
python ~/.agents/skills/absads/scripts/ads_scix.py metrics 1929PNAS...15..168H
```

### Download arXiv source

```bash
python ~/.agents/skills/absads/scripts/ads_scix.py source 2012A%26A...542A..16R --out ./paper-src
```

## File layout

```text
absads/
├── README.md
├── SKILL.md
├── references/
│   └── api.md
├── scripts/
│   └── ads_scix.py
└── tests/
    └── test_ads_scix.py
```

## Verification

Run the local checks with:

```bash
python3 -m py_compile ~/.agents/skills/absads/scripts/ads_scix.py
python3 ~/.agents/skills/absads/tests/test_ads_scix.py
python3 ~/.agents/skills/absads/scripts/ads_scix.py --help
python3 ~/.agents/skills/absads/scripts/ads_scix.py search --help
python3 ~/.agents/skills/absads/scripts/ads_scix.py export --help
python3 ~/.agents/skills/absads/scripts/ads_scix.py metrics --help
python3 ~/.agents/skills/absads/scripts/ads_scix.py source --help
```

## References

- ADS API docs: https://ui.adsabs.harvard.edu/help/api/api-docs.html#servers
- ADS developer API: https://github.com/adsabs/adsabs-dev-api#access-settings
- ADS OpenAPI: https://github.com/adsabs/adsabs-dev-api/tree/master/openapi
- arXiv source unpacking: https://info.arxiv.org/help/unpack.html
