#!/usr/bin/env python3
"""ADS/SciX helper for astrophysics literature workflows."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shlex
import shutil
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable


ADS_BASE_URL = os.environ.get("ADS_BASE_URL", "https://api.adsabs.harvard.edu")
ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_USER_AGENT = os.environ.get("ARXIV_USER_AGENT", "absads/1.0")
ARXIV_RE = re.compile(r"(?:arXiv:)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)", re.I)


def token() -> str:
    value = os.environ.get("ADS_API_KEY") or os.environ.get("SCIX_API_KEY")
    if value:
        return value
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    credentials = config_dir / "absads" / "credentials"
    try:
        lines = credentials.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        lines = []
    except OSError as exc:
        raise SystemExit(f"Cannot read ADS credentials file: {exc.strerror}") from exc
    for line in reversed(lines):
        if line.startswith("ADS_API_KEY="):
            try:
                parts = shlex.split(line, comments=False)
            except ValueError:
                break
            if len(parts) == 1 and parts[0].startswith("ADS_API_KEY="):
                value = parts[0].partition("=")[2]
                if value:
                    return value
            break
    raise SystemExit("ADS/SciX credentials unavailable. Set ADS_API_KEY or SCIX_API_KEY, or run python scripts/setup_ads_key.py.")


def command_auth_status(args: argparse.Namespace) -> None:
    token()
    print("ADS/SciX credentials available (not validated online).")


def request(method: str, path: str, *, params: dict[str, str] | None = None, data: object | None = None) -> bytes:
    url = ADS_BASE_URL.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token()}")
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"ADS API error {exc.code}: {detail}") from exc


def print_json(raw: bytes) -> None:
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        print(raw.decode("utf-8", "replace"))
        return
    print(json.dumps(parsed, indent=2, ensure_ascii=False))


def arxiv_request(params: dict[str, str]) -> bytes:
    url = ARXIV_API_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Accept": "application/atom+xml",
        "User-Agent": ARXIV_USER_AGENT,
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"arXiv API error {exc.code}: {detail}") from exc


def atom_text(element: ET.Element, name: str, namespace: str = "http://www.w3.org/2005/Atom") -> str | None:
    child = element.find(f"{{{namespace}}}{name}")
    return None if child is None or child.text is None else " ".join(child.text.split())


def parse_arxiv_feed(raw: bytes, *, params: dict[str, str]) -> dict[str, object]:
    atom = "http://www.w3.org/2005/Atom"
    arxiv = "http://arxiv.org/schemas/atom"
    opensearch = "http://a9.com/-/spec/opensearch/1.1/"
    root = ET.fromstring(raw)
    entries = []
    for entry in root.findall(f"{{{atom}}}entry"):
        entries.append({
            "id": atom_text(entry, "id"),
            "arxiv_id": find_arxiv_id([atom_text(entry, "id") or ""]),
            "title": atom_text(entry, "title"),
            "summary": atom_text(entry, "summary"),
            "published": atom_text(entry, "published"),
            "updated": atom_text(entry, "updated"),
            "authors": [atom_text(author, "name") for author in entry.findall(f"{{{atom}}}author")],
            "categories": [node.attrib.get("term") for node in entry.findall(f"{{{atom}}}category")],
            "doi": atom_text(entry, "doi", arxiv),
            "comment": atom_text(entry, "comment", arxiv),
            "links": [link.attrib for link in entry.findall(f"{{{atom}}}link")],
        })
    return {
        "source": "arXiv API",
        "source_url": ARXIV_API_URL + "?" + urllib.parse.urlencode(params),
        "query": params,
        "total_results": atom_text(root, "totalResults", opensearch),
        "start_index": atom_text(root, "startIndex", opensearch),
        "items_per_page": atom_text(root, "itemsPerPage", opensearch),
        "entries": entries,
    }


def command_arxiv_search(args: argparse.Namespace) -> None:
    raw_query = getattr(args, "query", None)
    raw_id_list = getattr(args, "id_list", None)
    clean_query = raw_query.strip() if isinstance(raw_query, str) else None
    clean_id_list = [i.strip() for i in raw_id_list if isinstance(i, str)] if raw_id_list is not None else None

    if clean_id_list is not None:
        if any(not i for i in clean_id_list):
            sys.stderr.write("error: --id-list identifiers must not be empty\n")
            raise SystemExit(2)

    has_query = raw_query is not None
    has_id_list = bool(clean_id_list)

    if has_query and has_id_list:
        sys.stderr.write("error: use query or --id-list, not both\n")
        raise SystemExit(2)

    if has_id_list:
        assert clean_id_list is not None
        query_params = {"id_list": ",".join(clean_id_list)}
    elif clean_query:
        query_params = {"search_query": clean_query}
    else:
        sys.stderr.write("error: provide query or --id-list\n")
        raise SystemExit(2)

    params = {
        "start": str(getattr(args, "start", 0)),
        "max_results": str(getattr(args, "max_results", 10)),
        "sortBy": getattr(args, "sort_by", "submittedDate"),
        "sortOrder": getattr(args, "sort_order", "descending"),
        **query_params,
    }
    print(json.dumps(parse_arxiv_feed(arxiv_request(params), params=params), indent=2, ensure_ascii=False))


def command_search(args: argparse.Namespace) -> None:
    params = {
        "q": args.query,
        "fl": ",".join(args.fields),
        "rows": str(args.rows),
        "start": str(args.start),
        "sort": args.sort,
    }
    if args.filter:
        params["fq"] = args.filter
    print_json(request("GET", "/v1/search/query", params=params))


def command_export(args: argparse.Namespace) -> None:
    if len(args.bibcodes) == 1:
        raw = request("GET", f"/v1/export/{urllib.parse.quote(args.format)}/{urllib.parse.quote(args.bibcodes[0])}")
    else:
        raw = request("POST", f"/v1/export/{urllib.parse.quote(args.format)}", data={"bibcode": args.bibcodes})
    print(raw.decode("utf-8", "replace"))


def command_metrics(args: argparse.Namespace) -> None:
    if len(args.bibcodes) == 1:
        raw = request("GET", f"/v1/metrics/{urllib.parse.quote(args.bibcodes[0])}")
    else:
        raw = request("POST", "/v1/metrics", data={"bibcodes": args.bibcodes, "types": args.types})
    print_json(raw)


def find_arxiv_id(values: Iterable[object]) -> str | None:
    for value in values:
        text = str(value)
        match = ARXIV_RE.search(text)
        if match:
            return match.group(1)
    return None


def metadata_for_bibcode(bibcode: str) -> dict[str, object]:
    raw = request(
        "GET",
        "/v1/search/query",
        params={"q": f"bibcode:{bibcode}", "fl": "bibcode,identifier,title", "rows": "1"},
    )
    parsed = json.loads(raw.decode("utf-8"))
    docs = parsed.get("response", {}).get("docs", [])
    if not docs:
        raise SystemExit(f"No ADS record found for bibcode: {bibcode}")
    return docs[0]


def download(url: str, destination: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "ads-scix-research-skill/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, destination.open("wb") as fh:
        shutil.copyfileobj(resp, fh)


def safe_member_path(root: Path, member_name: str) -> Path:
    root = root.resolve()
    candidate = Path(member_name)
    if candidate.is_absolute():
        raise ValueError(f"Archive member has absolute path: {member_name}")
    target = (root / candidate).resolve()
    if root != target and root not in target.parents:
        raise ValueError(f"Archive member escapes output directory: {member_name}")
    return target


def safe_tar_extract(tar: tarfile.TarFile, out: Path) -> None:
    members = tar.getmembers()
    for member in members:
        safe_member_path(out, member.name)
    tar.extractall(out, members=members)


def safe_zip_extract(zf: zipfile.ZipFile, out: Path) -> None:
    for member_name in zf.namelist():
        safe_member_path(out, member_name)
    zf.extractall(out)


def extract_archive(archive: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    if tarfile.is_tarfile(archive):
        with tarfile.open(archive) as tar:
            safe_tar_extract(tar, out)
        return
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            safe_zip_extract(zf, out)
        return
    try:
        with gzip.open(archive, "rb") as src:
            first = src.read(1024)
            src.seek(0)
            name = "source.tex" if b"\\documentclass" in first or b"\\begin" in first else "source"
            with (out / name).open("wb") as dst:
                shutil.copyfileobj(src, dst)
        return
    except OSError:
        pass
    shutil.copy2(archive, out / archive.name)


def command_source(args: argparse.Namespace) -> None:
    arxiv_id = args.arxiv_id
    if not arxiv_id:
        doc = metadata_for_bibcode(args.bibcode)
        identifiers = doc.get("identifier", [])
        if not isinstance(identifiers, list):
            identifiers = [identifiers]
        arxiv_id = find_arxiv_id(identifiers)
    if not arxiv_id:
        raise SystemExit("No arXiv identifier found. Pass --arxiv-id explicitly if known.")
    clean_id = arxiv_id.replace("arXiv:", "")
    out = Path(args.out).expanduser().resolve()
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "arxiv-source"
        download(f"https://arxiv.org/src/{clean_id}", archive)
        extract_archive(archive, out)
    print(json.dumps({"arxiv_id": clean_id, "source_url": f"https://arxiv.org/src/{clean_id}", "output": str(out)}, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ADS/SciX academic research helper")
    sub = parser.add_subparsers(required=True)

    auth_status = sub.add_parser("auth-status", help="Check for locally available credentials without displaying them")
    auth_status.set_defaults(func=command_auth_status)

    search = sub.add_parser("search", help="Search ADS/SciX literature")
    search.add_argument("query")
    search.add_argument("--fields", nargs="+", default=["bibcode", "title", "author", "year", "identifier", "citation_count"])
    search.add_argument("--rows", type=int, default=10)
    search.add_argument("--start", type=int, default=0)
    search.add_argument("--sort", default="date desc")
    search.add_argument("--filter", action="append")
    search.set_defaults(func=command_search)

    export = sub.add_parser("export", help="Export citations")
    export.add_argument("format", help="bibtex, ris, endnote, aastex, mnras, etc.")
    export.add_argument("bibcodes", nargs="+")
    export.set_defaults(func=command_export)

    metrics = sub.add_parser("metrics", help="Fetch citation metrics")
    metrics.add_argument("bibcodes", nargs="+")
    metrics.add_argument("--types", nargs="+", default=["basic", "citations", "indicators"])
    metrics.set_defaults(func=command_metrics)

    source = sub.add_parser("source", help="Download and extract arXiv source for an ADS bibcode")
    source.add_argument("bibcode")
    source.add_argument("--arxiv-id", help="Skip ADS lookup and use this arXiv ID")
    source.add_argument("--out", required=True, help="Clean output directory")
    source.set_defaults(func=command_source)

    arxiv = sub.add_parser("arxiv", help="Use the public arXiv Atom API")
    arxiv_sub = arxiv.add_subparsers(required=True)
    arxiv_search = arxiv_sub.add_parser("search", help="Search arXiv")
    arxiv_search.add_argument("query", nargs="?", default=None, help="arXiv search_query; omit when using --id-list")
    arxiv_search.add_argument("--id-list", nargs="+", help="Specific arXiv IDs")
    arxiv_search.add_argument("--start", type=int, default=0)
    arxiv_search.add_argument("--max-results", type=int, default=10)
    arxiv_search.add_argument("--sort-by", choices=["relevance", "lastUpdatedDate", "submittedDate"], default="submittedDate")
    arxiv_search.add_argument("--sort-order", choices=["ascending", "descending"], default="descending")
    arxiv_search.set_defaults(func=command_arxiv_search)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
