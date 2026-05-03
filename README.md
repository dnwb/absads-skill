# absads

`absads` is an ADS/SciX research skill for astrophysics and astronomy literature work.

It helps an agent use ADS/SciX as the primary source for paper metadata, citations, metrics, and identifiers, with arXiv used for source-package retrieval when needed.

## What it does

- search astrophysics literature with ADS query syntax
- look up papers by bibcode, DOI, or arXiv ID
- export citations in ADS-supported formats such as BibTeX and RIS
- fetch citation metrics
- retrieve and unpack arXiv source packages
- document ADS library workflows
- document author-affiliation workflows
- document SciX compatibility assumptions

## What you need to configure

Set one of these environment variables:

- `ADS_API_KEY`
- `SCIX_API_KEY`

Optional:

- `ADS_BASE_URL` if you need a non-default ADS API host

## Main files

- `SKILL.md` — skill instructions and workflows
- `references/api.md` — ADS/SciX API reference used by the skill
- `scripts/ads_scix.py` — helper CLI for common workflows

## Quick examples

```bash
python ~/.agents/skills/absads/scripts/ads_scix.py search 'author:"Hubble" year:1929' --rows 5
python ~/.agents/skills/absads/scripts/ads_scix.py export bibtex 1929PNAS...15..168H
python ~/.agents/skills/absads/scripts/ads_scix.py metrics 1929PNAS...15..168H
python ~/.agents/skills/absads/scripts/ads_scix.py source 2012A%26A...542A..16R --out ./paper-src
```

## Notes

- keep API keys in environment variables, not in files
- treat SciX as ADS-compatible unless official SciX-specific docs are verified
- ask before mutating ADS/SciX libraries
