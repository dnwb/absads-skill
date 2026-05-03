---
name: absads
description: Use when doing astrophysics or astronomy academic research with ADS, SciX, arXiv source packages, bibcodes, bibcode lookup, arXiv ID lookup, DOI lookup, identifier export, citation export, citation metrics, saved libraries, author-affiliation data, literature search, paper investigation, or bibliography workflows.
---

# ADS/SciX Academic Research

Use ADS/SciX as the primary source for astrophysics literature metadata. Use arXiv only for preprint/source retrieval or when ADS points to an arXiv identifier.

## Core Rules

- Read credentials from `ADS_API_KEY`, falling back to `SCIX_API_KEY`; send as `Authorization: Bearer <token>`.
- Never print, write, commit, or paste API keys.
- Preserve provenance in outputs: `bibcode`, arXiv ID, DOI, title, authors, year, source URL, and query used.
- Prefer official ADS API endpoints. Treat SciX as ADS-compatible unless official SciX-specific docs are verified.
- Ask before mutating ADS/SciX libraries or downloading many full source packages.

## Quick Commands

Helper script: `scripts/ads_scix.py`.

```bash
# Search literature
python ~/.agents/skills/absads/scripts/ads_scix.py search 'author:"Hubble" year:1929' --rows 5

# Export BibTeX
python ~/.agents/skills/absads/scripts/ads_scix.py export bibtex 1929PNAS...15..168H

# Metrics for papers
python ~/.agents/skills/absads/scripts/ads_scix.py metrics 1929PNAS...15..168H

# Download and unpack arXiv source for the first arXiv identifier found in ADS metadata
python ~/.agents/skills/absads/scripts/ads_scix.py source 2012A%26A...542A..16R --out ./paper-src
```

Read `references/api.md` when you need endpoint details, field names, library workflows, author-affiliation workflows, or arXiv source extraction details.

## Literature Search Workflow

1. Translate the research question into ADS query params: query (`q`), optional filters (`fq`), and field list (`fl`).
2. Request only useful fields in `fl` first: `bibcode,title,author,year,identifier,doi,citation_count,read_count,property,abstract,arxiv_class`.
3. Sort intentionally, usually `date desc`, `citation_count desc`, or `read_count desc`.
4. Return results with bibcodes and identifiers; do not summarize papers without preserving identifiers.
5. For a survey, chain outward with references/citations after identifying seed papers.

## Paper Investigation Workflow

For each paper, collect:

| Need | ADS fields / workflow |
|------|------------------------|
| Canonical ID | `bibcode` |
| Preprint/source | `identifier` entries like `arXiv:2401.01234` |
| Citation impact | `citation_count`, `/v1/metrics` |
| Bibliography | `/v1/export/{format}` |
| Source files | arXiv ID → `https://arxiv.org/src/<id>` |

When asked to “read/investigate” a paper, first fetch metadata and identifiers, then decide whether abstract, citations, references, or arXiv source are needed. Do not download source if metadata answers the question.

## Citation and Export Workflow

- Use `export bibtex` for BibTeX; use `ris` for reference managers.
- For multiple bibcodes, use POST export or the helper script with multiple bibcodes.
- Keep the exported citation plus the ADS bibcode in notes.

## Identifier Lookup and Export Workflow

1. Find by bibcode: query `bibcode:<bibcode>` and request `fl=bibcode,identifier,doi,title,author,year`.
2. Find by arXiv ID: query `identifier:"arXiv:<id>"` or `arXiv:<id>` when supported by ADS query syntax, then preserve returned `bibcode` and `identifier` list.
3. Find by DOI: query `doi:<doi>` or `identifier:"<doi>"`, then preserve returned `bibcode`, DOI, and arXiv identifiers.
4. Export identifiers: include bibcode, arXiv ID, DOI, ADS URL, and the query used alongside BibTeX/RIS citation exports.
5. When converting between identifiers, state the direction explicitly: arXiv ID → ADS bibcode, bibcode → DOI/arXiv IDs, or DOI → ADS bibcode.

## arXiv Source Workflow

1. Search ADS with `fl=bibcode,identifier,title`.
2. Extract `arXiv:...` from `identifier`; preserve version if present and version-specific source is needed.
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
| Searching web first for astrophysics papers | Search ADS/SciX first. |
| Losing bibcodes in summaries | Include bibcode/arXiv/DOI in every paper note. |
| Printing tokens in debug output | Never display env var values. |
| Treating all arXiv source downloads as tar | Detect gzip/tar/zip and extract safely. |
| Mutating libraries silently | Ask first and state exactly which bibcodes will change. |

## Official References

- ADS API docs: https://ui.adsabs.harvard.edu/help/api/api-docs.html#servers
- ADS developer API: https://github.com/adsabs/adsabs-dev-api#access-settings
- arXiv source unpacking: https://info.arxiv.org/help/unpack.html
