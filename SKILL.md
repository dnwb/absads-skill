---
name: absads
description: Use when doing astrophysics or astronomy academic research with ADS, SciX, arXiv source packages, PDF download requests, bibcodes, bibcode lookup, arXiv ID lookup, DOI lookup, identifier export, citation export, citation metrics, saved libraries, author-affiliation data, literature search, paper investigation, or bibliography workflows.
---

# ADS/SciX Academic Research

Use ADS/SciX as the primary source for astrophysics literature metadata when its API credentials are available. Otherwise, use the public arXiv API for suitable searches and known arXiv IDs, or other available public sources for broader coverage. Keep the workflow source-first: use arXiv source packages for paper source/content artifacts when available, and download PDFs only when the user explicitly asks for PDFs or full-text PDF files.

## Core Rules

- ADS/SciX API operations require a key. The helper uses `ADS_API_KEY`, then `SCIX_API_KEY`, then the key saved by the setup wizard. Before choosing a fallback for missing credentials, run `python ~/.agents/skills/absads/scripts/ads_scix.py auth-status` to check availability without showing the key; this does not validate it online. For direct API operations such as library access, use the helper's `request()` so the same credential lookup applies.
- Only when an ADS API operation is needed and no key is available, offer `python ~/.agents/skills/absads/scripts/setup_ads_key.py`; the user runs it locally and chooses whether to save the key. Public arXiv search, reading existing files, and PDF downloads by DOI or arXiv ID do not require an ADS/SciX key; explain coverage limitations when using an alternative.
- Never print, commit, or paste API keys. Only the user's setup wizard may save a key locally, with the user's consent.
- Preserve available bibcodes, arXiv IDs, DOI, title, year, source URL, and exact query. Retrieve authors when needed; do not print long author lists by default. Never invent missing identifiers.
- Prefer official ADS API endpoints. Treat SciX as ADS-compatible unless official SciX-specific docs are verified.
- Ask before mutating ADS/SciX libraries or downloading many full source packages.
- For PDF download requests, identify the paper and preserve available identifiers; use ADS/SciX when available or another public source as appropriate. Use the built-in PDF download reference when a DOI or arXiv ID is available. Default to legal/OA PDF sources unless the user explicitly selects the documented LibGen/Sci-Hub strategy.
- In claim-checking mode, bind every retrieval request to a claim/subclaim and a verification question. Compare source applicability, not ultimate scientific truth; return non-binding next actions, not automatic manuscript edits.

## Quick Commands

Helper script: `scripts/ads_scix.py`.

```bash
# Search literature
python ~/.agents/skills/absads/scripts/ads_scix.py search 'author:"Hubble" year:1929' --rows 5 --fields bibcode title year identifier doi

# Export BibTeX
python ~/.agents/skills/absads/scripts/ads_scix.py export bibtex 1929PNAS...15..168H

# Metrics for papers
python ~/.agents/skills/absads/scripts/ads_scix.py metrics 1929PNAS...15..168H

# Search arXiv directly through its public Atom API (no API key required)
python ~/.agents/skills/absads/scripts/ads_scix.py arxiv search 'all:galaxy AND cat:astro-ph.GA' --max-results 5

# Retrieve metadata for specific arXiv IDs
python ~/.agents/skills/absads/scripts/ads_scix.py arxiv search --id-list 2401.01234 2401.05678

# Download and unpack arXiv source via an ADS bibcode (requires an ADS/SciX key)
python ~/.agents/skills/absads/scripts/ads_scix.py source 2012A%26A...542A..16R --out ./paper-src

# Download a PDF only when explicitly requested; see references/pdf-download.md for legal/OA and LibGen/Sci-Hub strategies
python ~/.agents/skills/absads/scripts/pdf_fetch.py download 'arXiv:2401.01234' --out ./pdfs
```

Read `references/api.md` when you need endpoint details, field names, library workflows, author-affiliation workflows, or arXiv source extraction details.

Read `references/pdf-download.md` only when the user explicitly wants a PDF/full-text file, asks to download papers, or provides a DOI/arXiv ID for download.

Read `references/claim-retrieval.md` before checking manuscript assertions, precise numbers, upper limits, or model interpretations. It defines the claim ledger, applicability statuses, evidence roles/relations, excerpts, budgets, and stopping rules. Use `GLOSSARY.md` for domain terminology.

## Direct arXiv API Workflow

Use the public arXiv Atom API when ADS credentials are unavailable, when searching arXiv-native fields/categories, or when the user explicitly requests arXiv metadata. Its coverage is limited to arXiv records. The helper returns normalized JSON containing titles, abstracts, authors, categories, dates, DOI/comment fields, links, arXiv IDs, the exact API parameters, and the source URL. It does not require an API key. It sends an identifiable User-Agent; override it with `ARXIV_USER_AGENT` and preferably include a contact email, for example `absads/1.0 (mailto:you@example.org)`. Do not impersonate a browser User-Agent to bypass rate limits.

- Use arXiv `search_query` syntax such as `all:galaxy`, `au:Einstein`, `cat:astro-ph.GA`, and date ranges.
- Use `--id-list` for known identifiers; preserve versions such as `2401.01234v2` when supplied.
- Provide either a nonempty query or `--id-list`, not both. Empty or conflicting inputs fail before a network request. The neutral default User-Agent is `absads/1.0`; configure only a caller-owned contact address.
- Respect arXiv rate limits and terms; keep requests small and avoid polling or bulk harvesting.
- Treat arXiv metadata as arXiv-sourced, not ADS-canonical. For citation metrics, canonical bibcodes, and exports, continue to use ADS/SciX.
- Preserve `source`, `source_url`, and `query` in downstream notes.

## Literature Search Workflow

1. Select topic discovery for a survey, or claim checking for a specific assertion. In claim mode, split compound claims and state the question, required coverage, and budget before querying.
2. Use known identifiers directly; otherwise locate candidates by title keywords, object, and quantity. Start with `bibcode,title,year,identifier,doi` and `--rows 5`; request abstracts, authors, or metrics only as needed.
3. Sort intentionally using the selected source's supported fields.
4. Return results with available identifiers, including bibcodes when supplied by ADS.
5. For a survey, chain outward with references/citations after identifying seed papers.

## Claim Retrieval Workflow

Follow `references/claim-retrieval.md`. Compare precise numbers, limits, and model interpretations using quantity, sample, energy band, model assumptions, and statistical definitions. Metadata can confirm identity; scientific results need a pinpointed body, table, figure, or equation location and a brief evidence excerpt.

Record applicability (`direct_match`, `conditional_match`, `partial_match`, `unresolved`, `no_result`) separately from evidence direction (`supports`, `limits`, `contradicts`, `not_directly_relevant`). A directly comparable source can contradict a claim. Preserve conflicting evidence.

Default discovery budget: two targeted query variants per subclaim, five candidates per variant, plus separately declared targeted reading. Stop at required coverage, budget exhaustion, two variants without new qualifying sources, or no actionable lead. Record stop reason and gaps; increase a finite budget only with a recorded reason. `no_result` is not disproof.

Return a Markdown claim ledger with YAML-shaped examples when recording claim verification results. Do not automatically create a manifest. Link next actions to evidence locations or explicit gaps; record final editorial decisions only when externally supplied. Local manuscript compilation is outside source verification.

## Paper Investigation Workflow

For each paper, collect:

| Need | ADS fields / workflow |
|------|------------------------|
| Canonical ID | `bibcode` |
| Preprint/source | `identifier` entries like `arXiv:2401.01234` |
| PDF download | DOI or arXiv ID -> `references/pdf-download.md` |
| Citation impact | `citation_count`, `/v1/metrics` |
| Bibliography | `/v1/export/{format}` |
| Source files | arXiv ID → `https://arxiv.org/src/<id>` |

When asked to “read/investigate” a paper, first fetch metadata and identifiers, then decide whether abstract, citations, references, arXiv source, or PDF download are needed. Do not download source or PDF files if metadata answers the question.

For claim checks, metadata alone cannot establish a numerical result, upper limit, sample conclusion, or model interpretation. If targeted text is unavailable, record the gap rather than promoting abstract relevance to a direct match.

## Citation and Export Workflow

- Use `export bibtex` for BibTeX; use `ris` for reference managers.
- For multiple bibcodes, use POST export or the helper script with multiple bibcodes.
- Keep the exported citation plus the ADS bibcode in notes.
- Official BibTeX does not guarantee local build compatibility. Undefined journal macros (for example `\prd`) and stale `.bbl` files belong to manuscript build checks, not source-identity or scientific-evidence checks.

## Identifier Lookup and Export Workflow

1. Find by bibcode: query `bibcode:<bibcode>` and request `fl=bibcode,identifier,doi,title,author,year`.
2. Find by arXiv ID: query `identifier:"arXiv:<id>"` or `arXiv:<id>` when supported by ADS query syntax, then preserve returned `bibcode` and `identifier` list.
3. Find by DOI: query `doi:<doi>` or `identifier:"<doi>"`, then preserve returned `bibcode`, DOI, and arXiv identifiers.
4. Export identifiers: include bibcode, arXiv ID, DOI, ADS URL, and the query used alongside BibTeX/RIS citation exports.
5. When converting between identifiers, state the direction explicitly: arXiv ID → ADS bibcode, bibcode → DOI/arXiv IDs, or DOI → ADS bibcode.

## arXiv Source Workflow

1. Use a known arXiv ID, or find one through ADS or the public arXiv API; preserve the version if needed.
2. If using ADS, extract `arXiv:...` from `identifier`.
3. Download `https://arxiv.org/src/<arxiv-id>`.
4. Extract into a clean directory named for the bibcode or arXiv ID.
5. Inspect `.tex`, `.bib`, figures, tables, and data files as needed.

## Library Workflow

Split library actions into read-only and mutating operations.

Read-only operations:

- List libraries: `GET /v1/biblib/libraries`
- Read library details: `GET /v1/biblib/libraries/{library_id}`
- Query a saved collection: `GET|POST /v1/biblib/query/{library_id}`

Mutating operations:

- Add documents to a library: `POST /v1/biblib/documents/{library_id}`

Before any mutating library request, get explicit user approval. The approval text should include the target library identifier or name, the exact bibcodes to add, and the operation being performed. Preserve the library identifier, query used, returned bibcodes, and ADS/SciX base URL in your notes.

## Author-Affiliation Workflow

- Search: `POST /v1/author-affiliation/search`
- Export: `POST /v1/author-affiliation/export`

Use this workflow for author information, affiliation retrieval, and collaboration or network-oriented analysis. Preserve the request body, endpoint used, returned author or affiliation identifiers, and any returned fields that matter to the task. If a field or relationship is not present in the verified response, say it is unavailable instead of inventing author-affiliation details.

## SciX Compatibility Workflow

Assume ADS-compatible behavior by default. If you are using SciX and do not have official SciX-specific documentation for a host, endpoint, or behavior, say that ADS-compatible behavior is assumed and preserve the actual endpoint or base URL used in your output. Do not claim a SciX-only endpoint or SciX-specific behavior unless it is verified by official SciX-specific documentation.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Treating arXiv as a complete ADS replacement | State its coverage limits; use ADS/SciX when its specific records or features are needed. |
| Losing identifiers in summaries | Include available bibcode, arXiv ID, or DOI in each paper note. |
| Printing tokens in debug output | Never display env var values. |
| Treating all arXiv source downloads as tar | Detect gzip/tar/zip and extract safely. |
| Mutating libraries silently | Ask first and state exactly which bibcodes will change. |
| Downloading PDFs during ordinary metadata lookup | Download PDFs only when explicitly requested. |

## Official References

- ADS API docs: https://ui.adsabs.harvard.edu/help/api/api-docs.html#servers
- ADS developer API: https://github.com/adsabs/adsabs-dev-api#access-settings
- arXiv source unpacking: https://info.arxiv.org/help/unpack.html
