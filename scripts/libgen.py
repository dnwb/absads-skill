"""LibGen source with multi-mirror failover."""

from __future__ import annotations

import re
import urllib.parse
from pathlib import Path
from typing import Any

try:
    from ..network import fetch, polite_delay
    from ..pdf_utils import download_pdf
except ImportError:
    import shutil
    import urllib.request

    class _Response:
        def __init__(self, url: str, timeout: int = 60):
            req = urllib.request.Request(url, headers={"User-Agent": "absads-pdf-fetch/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                self.status_code = getattr(resp, "status", 200)
                self.text = resp.read().decode("utf-8", "replace")

    def fetch(url: str, config: dict[str, Any], use_tor: bool = False) -> _Response:
        return _Response(url, int(config.get("timeout", 60)))

    def polite_delay(config: dict[str, Any]) -> None:
        return None

    def download_pdf(
        url: str,
        output_path: Path,
        config: dict[str, Any],
        source: str,
        require_pdf_like_url: bool = False,
        use_tor: bool = False,
        cookies: Any = None,
    ) -> dict[str, Any] | None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = output_path.with_suffix(output_path.suffix + ".part")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "absads-pdf-fetch/1.0"})
            with urllib.request.urlopen(req, timeout=int(config.get("timeout", 120))) as resp, tmp.open("wb") as fh:
                first = resp.read(8192)
                if not first.startswith(b"%PDF-"):
                    tmp.unlink(missing_ok=True)
                    return None
                fh.write(first)
                shutil.copyfileobj(resp, fh)
            tmp.replace(output_path)
            return {"success": True, "file": str(output_path), "source": source, "url": url}
        except Exception:
            tmp.unlink(missing_ok=True)
            return None


LIBGEN_MIRRORS = [
    "https://libgen.li",
    "https://libgen.bz",
    "https://libgen.gs",
    "https://libgen.rs",
    "https://libgen.st",
]


def candidate_urls(doi: str) -> list[str]:
    q = urllib.parse.quote(doi, safe="")
    urls: list[str] = []
    for mirror in LIBGEN_MIRRORS:
        url = f"{mirror}/ads.php?doi={q}"
        try:
            resp = fetch(url, {"timeout": 20})
            if resp.status_code >= 400:
                continue
            html = resp.text
        except Exception:
            continue
        for pattern in (r'''href=["']([^"']*get\.php[^"']+)["']''', r'''href=["']([^"']*\.pdf[^"']*)["']'''):
            for match in re.finditer(pattern, html, re.I):
                candidate = urllib.parse.urljoin(url, match.group(1))
                if candidate not in urls:
                    urls.append(candidate)
    return urls


def try_libgen(doi: str, output_path: Path, config: dict[str, Any], use_tor: bool = False) -> dict[str, Any] | None:
    q = urllib.parse.quote(doi, safe="")
    for mirror in LIBGEN_MIRRORS:
        result = _try_libgen_mirror(doi, q, mirror, output_path, config, use_tor=use_tor)
        if result:
            return result
    return None


def _try_libgen_mirror(
    doi: str, q: str, mirror: str, output_path: Path, config: dict[str, Any], use_tor: bool = False
) -> dict[str, Any] | None:
    url = f"{mirror}/ads.php?doi={q}"
    try:
        resp = fetch(url, config, use_tor=use_tor)

        # Fallback to camofox on Cloudflare/403
        if resp.status_code in (403, 503):
            from ..flaresolverr import solve_url, is_available
            if is_available(config):
                result = solve_url(url, config)
                if result:
                    solution = result.get("solution", {})
                    if solution.get("status", 0) < 400:
                        resp_content = solution.get("response", "")
                        html = resp_content
                    else:
                        return None
                else:
                    return None
            else:
                return None
        else:
            if resp.status_code >= 400:
                return None
            html = resp.text
        for match in re.finditer(r'''href=["']([^"']*get\.php[^"']+)["']''', html, re.I):
            dl_path = match.group(1)
            dl_url = urllib.parse.urljoin(url, dl_path)
            polite_delay(config)
            result = download_pdf(dl_url, output_path, config, "LibGen", require_pdf_like_url=False, use_tor=use_tor)
            if result:
                result["doi"] = doi
                result["identifier"] = doi
                return result
        for match in re.finditer(r'''href=["']([^"']*\.pdf[^"']*)["']''', html, re.I):
            dl_path = match.group(1)
            if "get.php" in dl_path or dl_path.endswith(".pdf"):
                dl_url = urllib.parse.urljoin(url, dl_path)
                polite_delay(config)
                result = download_pdf(dl_url, output_path, config, "LibGen", require_pdf_like_url=False, use_tor=use_tor)
                if result:
                    result["doi"] = doi
                    result["identifier"] = doi
                    return result
    except Exception:
        pass
    return None
