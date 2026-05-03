# ADS/SciX API Reference

## Authentication

Use bearer-token auth:

```bash
curl -H "Authorization: Bearer $ADS_API_KEY" \
  "https://api.adsabs.harvard.edu/v1/search/query?q=star&rows=1"
```

Local convention: prefer `ADS_API_KEY`, fallback to `SCIX_API_KEY`.

## Search

- Endpoint: `GET https://api.adsabs.harvard.edu/v1/search/query`
- Core params: `q`, `fq`, `fl`, `start`, `rows`, `sort`
- Useful fields: `bibcode,title,author,year,identifier,doi,citation_count,read_count,property,abstract,arxiv_class,reference,citation`
- Common sorts: `date desc`, `citation_count desc`, `read_count desc`

Example:

```bash
curl -G -H "Authorization: Bearer $ADS_API_KEY" \
  --data-urlencode 'q=author:"Planck Collaboration" year:2018' \
  --data-urlencode 'fl=bibcode,title,author,year,identifier,citation_count' \
  --data-urlencode 'rows=10' \
  'https://api.adsabs.harvard.edu/v1/search/query'
```

## Identifier Lookup Examples

Bibcode lookup:

```bash
curl -G -H "Authorization: Bearer $ADS_API_KEY" \
  --data-urlencode 'q=bibcode:<bibcode>' \
  --data-urlencode 'fl=bibcode,identifier,doi,title,author,year' \
  'https://api.adsabs.harvard.edu/v1/search/query'
```

arXiv ID lookup:

```bash
curl -G -H "Authorization: Bearer $ADS_API_KEY" \
  --data-urlencode 'q=identifier:"arXiv:<id>"' \
  --data-urlencode 'fl=bibcode,identifier,doi,title,author,year' \
  'https://api.adsabs.harvard.edu/v1/search/query'
```

DOI lookup:

```bash
curl -G -H "Authorization: Bearer $ADS_API_KEY" \
  --data-urlencode 'q=doi:<doi>' \
  --data-urlencode 'fl=bibcode,identifier,doi,title,author,year' \
  'https://api.adsabs.harvard.edu/v1/search/query'
```

For identifier export, preserve `bibcode`, arXiv ID entries from `identifier`, DOI, ADS URL, and the citation export format used (`bibtex`, `ris`, etc.).

## Export

- Single bibcode: `GET /v1/export/{format}/{bibcode}`
- Multiple bibcodes: `POST /v1/export/{format}`
- Common formats: `bibtex`, `bibtexabs`, `ris`, `endnote`, `aastex`, `mnras`, `icarus`, `ieee`, `csl`, `votable`, `rss`

## Metrics

- One bibcode: `GET /v1/metrics/{bibcode}`
- Multiple bibcodes: `POST /v1/metrics`
- Detail: `POST /v1/metrics/detail`
- Types include `basic`, `citations`, `indicators`, `histograms`, `timeseries`.

## Libraries

Library mutations require explicit user approval.

Read-only library operations:

- List libraries: `GET /v1/biblib/libraries`
- Read library: `GET /v1/biblib/libraries/{library_id}`
- Query library: `GET|POST /v1/biblib/query/{library_id}`

Mutating library operations:

- Create library: `POST /v1/biblib/libraries`
- Add documents: `POST /v1/biblib/documents/{library_id}`

For add-document operations, send bibcodes only for the approved target library. Before the request, restate the target library identifier or name, the exact bibcodes being added, and the fact that explicit user approval was obtained.

## Author-Affiliation

- Search: `POST /v1/author-affiliation/search`
- Export: `POST /v1/author-affiliation/export`

Expected use cases include author information lookup, affiliation analysis, collaboration or network exploration, and exporting affiliation results for downstream analysis. Preserve the request body, endpoint used, returned identifiers, and returned fields that are actually present. If the verified docs or response do not provide a field, note that uncertainty instead of inventing schema details.

## SciX Compatibility

Treat SciX behavior as ADS-compatible by default. Do not claim a SciX-only endpoint, response shape, or workflow unless it is verified by official SciX-specific documentation. If you are using a SciX-specific host, preserve the actual base URL or endpoint and note whether the behavior is assumed ADS-compatible or officially verified.

## Bibcode and arXiv Identifier Handling

- ADS canonical paper identifier is `bibcode`.
- arXiv IDs usually appear in `identifier` as `arXiv:1204.4485` or versioned `arXiv:1204.4485v3`.
- Preserve version when exact reproducibility matters; strip version when “latest source” is desired.

## arXiv Source Retrieval

Official route:

```bash
curl -L -o source.tar.gz "https://arxiv.org/src/1204.4485"
mkdir -p paper-src
tar -xvf source.tar.gz -C paper-src
```

The response may be a gzipped single TeX file or an archive. Detect file type before extraction. Always extract into a clean directory.

## Sources

- ADS API docs: https://ui.adsabs.harvard.edu/help/api/api-docs.html#servers
- ADS developer API: https://github.com/adsabs/adsabs-dev-api#access-settings
- ADS OpenAPI: https://github.com/adsabs/adsabs-dev-api/tree/master/openapi
- arXiv source unpacking: https://info.arxiv.org/help/unpack.html
