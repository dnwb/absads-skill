# PDF Download Reference

Use this file when the paper is identified and the user explicitly wants a PDF or downloaded full-text file.

## Boundary

- Use ADS/SciX for discovery when available; otherwise use an appropriate public source or the user's identifier. Preserve available identifiers, metadata, source URL, and query. A DOI or arXiv ID is sufficient input for the downloader; it does not require an ADS key.
- Keep source-first behavior. If the task is to inspect source, figures, tables, TeX, or reproducibility artifacts, use the arXiv source workflow instead of PDF download.
- Use PDF download only when the user asks for a PDF, says to download papers, or gives DOI/arXiv IDs for download.
- Use the bundled script first. Do not install or configure external PDF downloader MCP servers for ordinary OA PDF requests.
- The default downloader strategy is legal/OA-only: arXiv PDF, known OA publisher direct URLs, Crossref PDF links, DOI landing-page PDF metadata, OpenAlex PDF URLs, Unpaywall OA PDF URLs, DOAJ, Crossref-style landing-page extraction, EuropePMC, CORE, and PMC.
- The script also intentionally keeps LibGen and Sci-Hub as third-party fallback sources for explicit strategy use.
- The script exposes `legal_only`, `grey_last`, and `third_party_only`.
- `grey_last` tries legal/OA providers first, then LibGen and Sci-Hub. Use it only when the user explicitly wants third-party fallback after OA sources fail.
- Ask before batch downloading many papers.
- Landing-page extraction checks `meta citation_pdf_url`, `href`, `embed src`, `iframe src`, and `object data`.
- The downloader verifies the first bytes start with `%PDF-` before committing the file.

## Bundled Script

Script:

```bash
python ~/.agents/skills/absads/scripts/pdf_fetch.py download <identifier> --out ./pdfs
```

Accepted identifiers:

- `arXiv:2401.01234` or `2401.01234`
- `doi:10.xxxx/...`
- `https://doi.org/10.xxxx/...`

For DOI downloads, `legal_only` tries bundled legal/OA sources in order: known OA publisher direct templates, Crossref PDF links, DOI landing-page PDF metadata/links, OpenAlex, Unpaywall, DOAJ, Crossref-style landing-page extraction, EuropePMC, CORE, and PMC.

```bash
python ~/.agents/skills/absads/scripts/pdf_fetch.py download '10.3847/1538-4357/ac1234' --out ./pdfs --unpaywall-email you@example.edu
```

Use `grey_last` when the user wants legal/OA sources first and LibGen/Sci-Hub fallback if those sources fail:

```bash
python ~/.agents/skills/absads/scripts/pdf_fetch.py download '10.3847/1538-4357/ac1234' --out ./pdfs --strategy grey_last
```

Use `third_party_only` only when the user explicitly wants to skip OA discovery and try LibGen/Sci-Hub directly:

```bash
python ~/.agents/skills/absads/scripts/pdf_fetch.py download '10.3847/1538-4357/ac1234' --out ./pdfs --strategy third_party_only
```

Preview candidate URLs without downloading:

```bash
python ~/.agents/skills/absads/scripts/pdf_fetch.py download 'arXiv:2401.01234' --out ./pdfs --print-candidates
```

## Workflow

1. Identify the paper using available metadata and collect its DOI or arXiv ID; preserve the discovery source and available identifiers.
2. Prefer arXiv ID when available because it is direct and source-adjacent.
3. Otherwise use DOI. With `legal_only`, source order is publisher direct -> Crossref -> DOI landing page -> OpenAlex -> Unpaywall if email is available -> DOAJ -> CrossrefPage -> EuropePMC -> CORE -> PMC. With `grey_last`, continue to LibGen -> Sci-Hub after legal/OA sources.
4. Run the bundled script.
5. Report the saved file path, source used, URL used, and discovery provenance.

## Failure Handling

If no PDF is found:

1. Report the identifiers tried and say whether the failed strategy was legal/OA-only or included third-party sources.
2. Return the available provenance and DOI/arXiv ID for manual follow-up.
3. If using `grey_last`, preserve the script's explicit terminal message when no OA or third-party candidates are found.

If the downloaded response is not a PDF, the script rejects it and tries the next candidate. Treat final failure as an availability problem for the selected strategy, not as proof that the paper has no PDF anywhere.

## Batch Download

1. Build the candidate list from available sources.
2. Show bibcodes and DOI/arXiv IDs and ask for confirmation before downloading.
3. Run the bundled script once per confirmed identifier.
4. Return a concise success/failure table with file paths and failed identifiers.

## Provenance Checklist

Each PDF download note should include:

- ADS `bibcode`, if available
- DOI or arXiv ID used for download
- title, authors, year
- Discovery source URL or query, if available
- PDF source: arXiv, PublisherDirect, Crossref, LandingPage, OpenAlex, Unpaywall, DOAJ, CrossrefPage, EuropePMC, CORE, PMC, LibGen, or Sci-Hub
- downloaded URL
- returned file path
