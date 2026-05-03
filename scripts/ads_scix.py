#!/usr/bin/env python3
"""ADS/SciX helper for astrophysics literature workflows."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable


ADS_BASE_URL = os.environ.get("ADS_BASE_URL", "https://api.adsabs.harvard.edu")
ARXIV_RE = re.compile(r"(?:arXiv:)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)", re.I)


def token() -> str:
    value = os.environ.get("ADS_API_KEY") or os.environ.get("SCIX_API_KEY")
    if not value:
        raise SystemExit("Set ADS_API_KEY or SCIX_API_KEY in the environment.")
    return value


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

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
