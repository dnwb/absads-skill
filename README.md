# absads

`absads` is an ADS/SciX research skill for astrophysics and astronomy literature work.

It helps an agent use ADS/SciX as the primary source for paper metadata, citations, metrics, and identifiers, with arXiv used for source-package retrieval when needed.

## What it does

- search astrophysics literature with ADS query syntax
- search arXiv directly through its public Atom API (no API key required)
- look up papers by bibcode, DOI, or arXiv ID
- export citations in ADS-supported formats such as BibTeX and RIS
- fetch citation metrics
- retrieve and unpack arXiv source packages
- download PDFs with legal/OA sources by default and optional LibGen/Sci-Hub strategies
- document ADS library workflows
- document author-affiliation workflows
- document SciX compatibility assumptions

## What you need to configure

No ADS/SciX key is needed for direct arXiv searches, work with existing files, or PDF downloads using a DOI or arXiv ID. arXiv search covers arXiv records, not the full ADS database.

For ADS/SciX API operations—including ADS search, citation exports, metrics, and personal libraries—the helper checks these environment variables in order:

- `ADS_API_KEY`
- `SCIX_API_KEY`

If neither variable is set, the helper automatically reads the key saved by `python scripts/setup_ads_key.py` at `${XDG_CONFIG_HOME:-~/.config}/absads/credentials`. The wizard skips setup when a key is already available. Run `python scripts/ads_scix.py auth-status` to check availability without displaying the key; this does not verify the key with ADS. On Windows, Python's file permissions depend on the user's Windows account and directory access controls.

For the direct arXiv API client, optionally set `ARXIV_USER_AGENT`, preferably with a contact email. The client already sends an identifiable default User-Agent.

## Main files

- `SKILL.md` — skill instructions and workflows
- `references/api.md` — ADS/SciX API reference used by the skill
- `references/pdf-download.md` — PDF download strategy reference
- `scripts/ads_scix.py` — helper CLI for common workflows
- `scripts/pdf_fetch.py` — PDF download helper CLI
- `scripts/libgen.py` — LibGen source adapter for `pdf_fetch.py`
- `scripts/scihub.py` — Sci-Hub source adapter for `pdf_fetch.py`

## Quick examples

```bash
python ads_scix.py search 'author:"Hubble" year:1929' --rows 5
python ads_scix.py arxiv search 'all:galaxy AND cat:astro-ph.GA' --max-results 5
python ads_scix.py export bibtex 1929PNAS...15..168H
python ads_scix.py metrics 1929PNAS...15..168H
python ads_scix.py source 2012A%26A...542A..16R --out ./paper-src
python pdf_fetch.py download '10.3847/1538-4357/ac1234' --out ./pdfs --strategy legal_only
python pdf_fetch.py download '10.3847/1538-4357/ac1234' --out ./pdfs --strategy grey_last
```
