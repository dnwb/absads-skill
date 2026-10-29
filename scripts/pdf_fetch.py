#!/usr/bin/env python3
"""Lightweight OA PDF downloader for ADS/SciX-resolved papers."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ARXIV_RE = re.compile(r"(?:arXiv:)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)", re.I)
DOI_RE = re.compile(r"(10\.\d{4,9}/[^\s\"<>]+)", re.I)
USER_AGENT = "absads-pdf-fetch/1.0 (OA PDF downloader)"
STRATEGIES = {"legal_only", "grey_last", "third_party_only"}
LEGAL_PROVIDER_ORDER = [
    "PublisherDirect",
    "Crossref",
    "LandingPage",
    "OpenAlex",
    "Unpaywall",
    "DOAJ",
    "CrossrefPage",
    "EuropePMC",
    "CORE",
    "PMC",
]
THIRD_PARTY_PROVIDER_ORDER = ["LibGen", "Sci-Hub"]
PUBLISHER_DIRECT_TEMPLATES = [
    ("PublisherDirect(Nature)", "10.1038/", "https://www.nature.com/articles/{suffix}.pdf"),
    ("PublisherDirect(MDPI)", "10.3390/", "https://www.mdpi.com/{suffix}/pdf"),
    ("PublisherDirect(PLOS)", "10.1371/", "https://journals.plos.org/plosone/article/file?id={doi}&type=printable"),
]


def request(url: str, *, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_json(url: str) -> dict[str, Any]:
    raw = request(url)
    return json.loads(raw.decode("utf-8"))


def normalize_arxiv_id(identifier: str) -> str | None:
    match = ARXIV_RE.search(identifier.strip())
    if not match:
        return None
    return match.group(1)


def normalize_doi(identifier: str) -> str | None:
    text = identifier.strip()
    if text.lower().startswith("doi:"):
        text = text[4:].strip()
    text = text.replace("https://doi.org/", "").replace("http://doi.org/", "")
    match = DOI_RE.search(text)
    if not match:
        return None
    return match.group(1).rstrip(".,);]")


def arxiv_pdf_url(arxiv_id: str) -> str:
    clean = arxiv_id.replace("arXiv:", "")
    return f"https://arxiv.org/pdf/{clean}.pdf"


def publisher_direct_candidates(doi: str) -> list[dict[str, str]]:
    candidates = []
    lower = doi.lower()
    suffix = doi.split("/", 1)[1] if "/" in doi else doi
    for source, prefix, template in PUBLISHER_DIRECT_TEMPLATES:
        if lower.startswith(prefix):
            candidates.append({"source": source, "url": template.format(doi=doi, suffix=suffix), "identifier": doi})
    return candidates


def extract_pdf_links(html: str, base_url: str) -> list[str]:
    urls = []
    patterns = [
        r'''citation_pdf_url["'\s]+content=["']([^"']+)["']''',
        r'''content=["']([^"']+)["'][^>]+citation_pdf_url''',
        r'''href=["']([^"']+\.pdf(?:\?[^"']*)?)["']''',
        r'''href=["']([^"']*(?:/pdf|type=printable)[^"']*)["']''',
        r'''embed[^>]+src=["']([^"']+)["']''',
        r'''iframe[^>]+src=["']([^"']+)["']''',
        r'''object[^>]+data=["']([^"']+)["']''',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, html, re.I):
            url = urllib.parse.urljoin(base_url, match.group(1).replace("&amp;", "&"))
            if url not in urls:
                urls.append(url)
    return urls


def dedupe_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        result.append(url)
    return result


def landing_page_candidates(doi: str) -> list[dict[str, str]]:
    candidates = []
    landing_url = f"https://doi.org/{doi}"
    try:
        req = urllib.request.Request(landing_url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as resp:
            final_url = resp.geturl()
            html = resp.read(512_000).decode("utf-8", "replace")
        for url in extract_pdf_links(html, final_url):
            candidates.append({"source": "LandingPage", "url": url, "identifier": doi})
    except (OSError, urllib.error.URLError, urllib.error.HTTPError):
        pass
    return candidates


def crossref_candidates(doi: str) -> list[dict[str, str]]:
    candidates = []
    encoded_doi = urllib.parse.quote(doi, safe="")
    try:
        data = fetch_json(f"https://api.crossref.org/works/{encoded_doi}")
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return candidates
    message = data.get("message", {})
    for link in message.get("link") or []:
        if not isinstance(link, dict):
            continue
        url = link.get("URL") or link.get("url")
        content_type = str(link.get("content-type") or link.get("content_type") or "").lower()
        intended = str(link.get("intended-application") or "").lower()
        if isinstance(url, str) and ("pdf" in content_type or "pdf" in intended or url.lower().endswith(".pdf")):
            candidates.append({"source": "Crossref", "url": url, "identifier": doi})
    return candidates


def extract_doaj_pdf_candidates(payload: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for item in payload.get("results", []):
        if not isinstance(item, dict):
            continue
        bibjson = item.get("bibjson", {})
        if not isinstance(bibjson, dict):
            continue
        for link in bibjson.get("link", []):
            if not isinstance(link, dict):
                continue
            link_url = link.get("url", "")
            link_type = str(link.get("type", "")).lower()
            if link_type == "fulltext" and isinstance(link_url, str) and link_url.startswith("http"):
                candidates.append(link_url)
    return dedupe_urls(candidates)


def openalex_candidates(doi: str) -> list[dict[str, str]]:
    candidates = []
    encoded_doi = urllib.parse.quote(doi, safe="")
    try:
        work = fetch_json(f"https://api.openalex.org/works/doi:{encoded_doi}")
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return candidates
    add_openalex_candidates(candidates, work, doi)
    return candidates


def unpaywall_candidates(doi: str, *, unpaywall_email: str | None = None) -> list[dict[str, str]]:
    candidates = []
    email = unpaywall_email or os.environ.get("UNPAYWALL_EMAIL")
    if not email:
        return candidates
    encoded_doi = urllib.parse.quote(doi, safe="")
    try:
        encoded_email = urllib.parse.quote(email, safe="")
        record = fetch_json(f"https://api.unpaywall.org/v2/{encoded_doi}?email={encoded_email}")
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return candidates
    add_unpaywall_candidates(candidates, record, doi)
    return candidates


def doaj_candidates(doi: str) -> list[dict[str, str]]:
    encoded_doi = urllib.parse.quote(doi, safe="")
    try:
        payload = fetch_json(f"https://doaj.org/api/v2/search/articles/doi:{encoded_doi}")
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return []
    return [{"source": "DOAJ", "url": url, "identifier": doi} for url in extract_doaj_pdf_candidates(payload)]


def crossref_page_candidates(doi: str) -> list[dict[str, str]]:
    return [{"source": "CrossrefPage", "url": item["url"], "identifier": doi} for item in landing_page_candidates(doi)]


def extract_europepmc_pdf_candidates(payload: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    results = payload.get("resultList", {}).get("result", [])
    if isinstance(results, dict):
        results = [results]
    if not isinstance(results, list):
        return []
    for result in results:
        if not isinstance(result, dict):
            continue
        fulltext = result.get("fullTextUrlList", {})
        urls = fulltext.get("fullTextUrl", []) if isinstance(fulltext, dict) else []
        if isinstance(urls, dict):
            urls = [urls]
        for entry in urls:
            if not isinstance(entry, dict):
                continue
            url = entry.get("url", "")
            style = str(entry.get("documentStyle", "")).lower()
            if isinstance(url, str) and url.startswith("http") and (style == "pdf" or ".pdf" in url.lower()):
                candidates.append(url)
    return dedupe_urls(candidates)


def europepmc_candidates(doi: str) -> list[dict[str, str]]:
    query = urllib.parse.quote(f"DOI:{doi}")
    try:
        payload = fetch_json(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&format=json&pageSize=5")
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return []
    return [{"source": "EuropePMC", "url": url, "identifier": doi} for url in extract_europepmc_pdf_candidates(payload)]


def walk_urls(value: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(value, dict):
        for inner in value.values():
            urls.extend(walk_urls(inner))
    elif isinstance(value, list):
        for inner in value:
            urls.extend(walk_urls(inner))
    elif isinstance(value, str) and value.startswith("http"):
        urls.append(value)
    return urls


def is_core_pdf_candidate(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.lower()
    if "core.ac.uk" in host and "/data-providers/" in path:
        return False
    return ".pdf" in url.lower()


def extract_core_pdf_candidates(payload: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for url in walk_urls(payload):
        if url in seen or not is_core_pdf_candidate(url):
            continue
        seen.add(url)
        urls.append(url)
    return urls


def core_candidates(doi: str) -> list[dict[str, str]]:
    query = urllib.parse.quote(f'doi:"{doi}"')
    try:
        payload = fetch_json(f"https://api.core.ac.uk/v3/search/works?q={query}&limit=5")
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return []
    return [{"source": "CORE", "url": url, "identifier": doi} for url in extract_core_pdf_candidates(payload)]


def extract_pmc_pdf_candidates(payload: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    for record in payload.get("records", []):
        if not isinstance(record, dict):
            continue
        pmcid = record.get("pmcid")
        if isinstance(pmcid, str) and pmcid:
            candidates.append(f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/")
    return candidates


def pmc_candidates(doi: str) -> list[dict[str, str]]:
    try:
        payload = fetch_json(f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={urllib.parse.quote(doi, safe='')}&format=json")
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return []
    return [{"source": "PMC", "url": url, "identifier": doi} for url in extract_pmc_pdf_candidates(payload)]


def grey_fallback_message(identifier: str) -> str:
    return (
        "No legal/OA candidates were found for "
        f"{identifier}. This skill stops here and leaves manual follow-up outside the bundled downloader."
    )


def provider_order(strategy: str) -> list[str]:
    if strategy not in STRATEGIES:
        raise ValueError(f"Unsupported strategy: {strategy}")
    if strategy == "third_party_only":
        return list(THIRD_PARTY_PROVIDER_ORDER)
    if strategy == "grey_last":
        return [*LEGAL_PROVIDER_ORDER, *THIRD_PARTY_PROVIDER_ORDER]
    return list(LEGAL_PROVIDER_ORDER)


def load_sibling_module(module_name: str) -> Any | None:
    path = Path(__file__).resolve().with_name(f"{module_name}.py")
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"absads_{module_name}", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return None
    return module


def source_result_to_candidate(source: str, result: dict[str, Any] | None, identifier: str) -> dict[str, str] | None:
    if not isinstance(result, dict):
        return None
    url = result.get("url")
    if not isinstance(url, str) or not url:
        return None
    return {"source": source, "url": url, "identifier": str(result.get("identifier") or identifier)}


def third_party_candidates(identifier: str, provider: str) -> list[dict[str, str]]:
    doi = normalize_doi(identifier)
    if not doi:
        return []
    module_name = {"LibGen": "libgen", "Sci-Hub": "scihub"}.get(provider)
    if not module_name:
        return []
    module = load_sibling_module(module_name)
    if module is None:
        return []
    candidate_fn = getattr(module, "candidate_urls", None)
    if callable(candidate_fn):
        try:
            return [{"source": provider, "url": url, "identifier": doi} for url in candidate_fn(doi)]
        except Exception:
            return []
    try_fn = getattr(module, {"LibGen": "try_libgen", "Sci-Hub": "try_scihub"}[provider], None)
    if not callable(try_fn):
        return []
    try:
        result = try_fn(doi, Path(os.devnull), {"scihub_enabled": True})
    except Exception:
        return []
    candidate = source_result_to_candidate(provider, result, doi)
    return [candidate] if candidate else []


def provider_candidates(
    name: str,
    *,
    doi: str | None,
    arxiv_id: str | None,
    unpaywall_email: str | None,
) -> list[dict[str, str]]:
    if name in THIRD_PARTY_PROVIDER_ORDER:
        return third_party_candidates(doi or "", name)
    if name == "arXiv" and arxiv_id:
        return [{"source": "arXiv", "url": arxiv_pdf_url(arxiv_id), "identifier": arxiv_id}]
    if not doi:
        return []
    if name == "PublisherDirect":
        return publisher_direct_candidates(doi)
    if name == "Crossref":
        return crossref_candidates(doi)
    if name == "LandingPage":
        return landing_page_candidates(doi)
    if name == "OpenAlex":
        return openalex_candidates(doi)
    if name == "Unpaywall":
        return unpaywall_candidates(doi, unpaywall_email=unpaywall_email)
    if name == "DOAJ":
        return doaj_candidates(doi)
    if name == "CrossrefPage":
        return crossref_page_candidates(doi)
    if name == "EuropePMC":
        return europepmc_candidates(doi)
    if name == "CORE":
        return core_candidates(doi)
    if name == "PMC":
        return pmc_candidates(doi)
    return []


def provider_plan(
    identifier: str,
    *,
    strategy: str = "legal_only",
    unpaywall_email: str | None = None,
    resolve_third_party: bool = False,
) -> list[dict[str, Any]]:
    arxiv_id = normalize_arxiv_id(identifier)
    doi = normalize_doi(identifier)
    providers: list[dict[str, Any]] = []

    if arxiv_id:
        providers.append({
            "name": "arXiv",
            "wired": True,
            "candidates": provider_candidates("arXiv", doi=doi, arxiv_id=arxiv_id, unpaywall_email=unpaywall_email),
        })

    for name in provider_order(strategy):
        candidates = []
        if resolve_third_party or name not in THIRD_PARTY_PROVIDER_ORDER:
            candidates = provider_candidates(name, doi=doi, arxiv_id=arxiv_id, unpaywall_email=unpaywall_email)
        providers.append({
            "name": name,
            "wired": True,
            "candidates": candidates,
        })
    return providers


def candidate_urls(
    identifier: str,
    *,
    unpaywall_email: str | None = None,
    strategy: str = "legal_only",
) -> list[dict[str, str]]:
    if strategy not in STRATEGIES:
        raise ValueError(f"Unsupported strategy: {strategy}")
    candidates: list[dict[str, str]] = []
    for provider in provider_plan(
        identifier,
        strategy=strategy,
        unpaywall_email=unpaywall_email,
        resolve_third_party=True,
    ):
        candidates.extend(provider["candidates"])
    return dedupe_candidates(candidates)

def add_openalex_candidates(candidates: list[dict[str, str]], work: dict[str, Any], doi: str) -> None:
    locations = []
    primary = work.get("primary_location")
    if isinstance(primary, dict):
        locations.append(primary)
    for location in work.get("locations") or []:
        if isinstance(location, dict):
            locations.append(location)

    for location in locations:
        pdf_url = location.get("pdf_url")
        if isinstance(pdf_url, str) and pdf_url:
            candidates.append({"source": "OpenAlex", "url": pdf_url, "identifier": doi})

    open_access = work.get("open_access")
    if isinstance(open_access, dict):
        oa_url = open_access.get("oa_url")
        if isinstance(oa_url, str) and oa_url.lower().endswith(".pdf"):
            candidates.append({"source": "OpenAlex", "url": oa_url, "identifier": doi})


def add_unpaywall_candidates(candidates: list[dict[str, str]], record: dict[str, Any], doi: str) -> None:
    locations = []
    best = record.get("best_oa_location")
    if isinstance(best, dict):
        locations.append(best)
    for location in record.get("oa_locations") or []:
        if isinstance(location, dict):
            locations.append(location)

    for location in locations:
        pdf_url = location.get("url_for_pdf")
        if isinstance(pdf_url, str) and pdf_url:
            candidates.append({"source": "Unpaywall", "url": pdf_url, "identifier": doi})


def dedupe_candidates(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    result = []
    for candidate in candidates:
        url = candidate["url"]
        if url in seen:
            continue
        seen.add(url)
        result.append(candidate)
    return result


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("_") or "paper"


def output_path(args: argparse.Namespace, identifier: str) -> Path:
    out = Path(args.out).expanduser()
    if out.suffix.lower() == ".pdf":
        return out
    return out / f"{safe_name(identifier)}.pdf"


def has_pdf_magic(prefix: bytes) -> bool:
    return prefix.startswith(b"%PDF-")


def download_pdf(url: str, destination: Path) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".part")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as fh:
            first = resp.read(8192)
            if not has_pdf_magic(first):
                tmp.unlink(missing_ok=True)
                return False
            fh.write(first)
            shutil.copyfileobj(resp, fh)
        tmp.replace(destination)
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        tmp.unlink(missing_ok=True)
        return False


def source_failure_message(strategy: str) -> str:
    if strategy == "legal_only":
        return "No legal/OA PDF candidates found from the bundled providers."
    if strategy == "third_party_only":
        return "No LibGen/Sci-Hub PDF candidates found from the bundled third-party providers."
    return "No legal/OA or third-party PDF candidates found from the bundled providers."


def command_download(args: argparse.Namespace) -> None:
    candidates = candidate_urls(args.identifier, unpaywall_email=args.unpaywall_email, strategy=args.strategy)
    if args.print_candidates:
        print(json.dumps({"identifier": args.identifier, "strategy": args.strategy, "candidates": candidates}, indent=2))
        return
    if not candidates and args.strategy == "grey_last":
        raise SystemExit(grey_fallback_message(args.identifier))
    if not candidates:
        raise SystemExit(source_failure_message(args.strategy))

    failures = []
    for candidate in candidates:
        dest = output_path(args, candidate["identifier"])
        if download_pdf(candidate["url"], dest):
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "identifier": candidate["identifier"],
                        "source": candidate["source"],
                        "url": candidate["url"],
                        "output": str(dest.resolve()),
                    },
                    indent=2,
                )
            )
            return
        failures.append(candidate)

    print(json.dumps({"status": "failed", "identifier": args.identifier, "tried": failures}, indent=2), file=sys.stderr)
    raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download PDFs using bundled legal/OA providers and optional third-party sources")
    sub = parser.add_subparsers(required=True)

    download = sub.add_parser("download", help="Download a PDF for an arXiv ID or DOI using bundled source strategies")
    download.add_argument("identifier", help="arXiv ID, DOI, doi:<doi>, or https://doi.org/<doi>")
    download.add_argument("--out", required=True, help="Output directory or .pdf path")
    download.add_argument(
        "--strategy",
        choices=sorted(STRATEGIES),
        default="legal_only",
        help="legal_only uses OA sources; grey_last tries OA then LibGen/Sci-Hub; third_party_only skips OA sources",
    )
    download.add_argument("--unpaywall-email", help="Email for Unpaywall API; fallback: UNPAYWALL_EMAIL")
    download.add_argument("--print-candidates", action="store_true", help="Print candidate URLs without downloading")
    download.set_defaults(func=command_download)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
