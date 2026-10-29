import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "pdf_fetch.py"
SPEC = importlib.util.spec_from_file_location("pdf_fetch", SCRIPT)
pdf_fetch = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(pdf_fetch)


class PdfFetchTest(unittest.TestCase):
    def test_normalize_arxiv_id(self):
        self.assertEqual(pdf_fetch.normalize_arxiv_id("arXiv:2401.01234v2"), "2401.01234v2")

    def test_normalize_doi(self):
        self.assertEqual(pdf_fetch.normalize_doi("https://doi.org/10.1234/ABC.def."), "10.1234/ABC.def")

    def test_arxiv_candidate_first(self):
        candidates = pdf_fetch.candidate_urls("arXiv:2401.01234")

        self.assertEqual(candidates[0]["source"], "arXiv")
        self.assertEqual(candidates[0]["url"], "https://arxiv.org/pdf/2401.01234.pdf")

    def test_openalex_pdf_candidates(self):
        work = {
            "primary_location": {"pdf_url": "https://example.org/primary.pdf"},
            "locations": [{"pdf_url": "https://example.org/other.pdf"}],
            "open_access": {"oa_url": "https://example.org/oa.pdf"},
        }
        candidates = []

        pdf_fetch.add_openalex_candidates(candidates, work, "10.1/x")

        self.assertEqual([c["url"] for c in candidates], [
            "https://example.org/primary.pdf",
            "https://example.org/other.pdf",
            "https://example.org/oa.pdf",
        ])

    def test_unpaywall_candidates(self):
        record = {
            "best_oa_location": {"url_for_pdf": "https://example.org/best.pdf"},
            "oa_locations": [{"url_for_pdf": "https://example.org/other.pdf"}],
        }
        candidates = []

        pdf_fetch.add_unpaywall_candidates(candidates, record, "10.1/x")

        self.assertEqual([c["source"] for c in candidates], ["Unpaywall", "Unpaywall"])

    def test_doi_candidates_tolerate_api_failures(self):
        with mock.patch.object(pdf_fetch, "fetch_json", side_effect=OSError("offline")):
            candidates = pdf_fetch.candidate_urls("10.1234/test")

        self.assertEqual(candidates, [])

    def test_publisher_direct_candidates_for_known_oa_prefixes(self):
        candidates = pdf_fetch.publisher_direct_candidates("10.1038/s41586-020-2649-2")

        self.assertEqual(candidates[0]["source"], "PublisherDirect(Nature)")
        self.assertEqual(candidates[0]["url"], "https://www.nature.com/articles/s41586-020-2649-2.pdf")

    def test_extract_pdf_links_from_landing_html(self):
        html = '''
        <meta name="citation_pdf_url" content="https://example.org/paper.pdf">
        <a href="/download.pdf">PDF</a>
        '''

        urls = pdf_fetch.extract_pdf_links(html, "https://example.org/article")

        self.assertEqual(urls, ["https://example.org/paper.pdf", "https://example.org/download.pdf"])

    def test_extract_pdf_links_finds_embed_and_iframe_sources(self):
        html = '''
        <embed src="/paper/embed.pdf">
        <iframe src="https://cdn.example.org/viewer.pdf?download=1"></iframe>
        '''

        urls = pdf_fetch.extract_pdf_links(html, "https://example.org/article")

        self.assertEqual(urls, [
            "https://example.org/paper/embed.pdf",
            "https://cdn.example.org/viewer.pdf?download=1",
        ])

    def test_provider_order_for_legal_only_matches_scansci_shape(self):
        names = [provider["name"] for provider in pdf_fetch.provider_plan("10.1234/test", strategy="legal_only")]

        self.assertEqual(names, [
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
        ])

    def test_grey_last_adds_third_party_sources_after_legal_sources(self):
        names = [provider["name"] for provider in pdf_fetch.provider_plan("10.1234/test", strategy="grey_last")]

        self.assertEqual(names[-2:], ["LibGen", "Sci-Hub"])

    def test_third_party_provider_uses_sibling_candidate_function(self):
        fake_module = type("FakeModule", (), {"candidate_urls": staticmethod(lambda doi: [f"https://example.org/{doi}.pdf"])})

        with mock.patch.object(pdf_fetch, "load_sibling_module", return_value=fake_module):
            candidates = pdf_fetch.provider_candidates(
                "LibGen",
                doi="10.1234/test",
                arxiv_id=None,
                unpaywall_email=None,
            )

        self.assertEqual(candidates, [
            {"source": "LibGen", "url": "https://example.org/10.1234/test.pdf", "identifier": "10.1234/test"}
        ])

    def test_third_party_only_strategy_skips_legal_sources(self):
        with mock.patch.object(pdf_fetch, "third_party_candidates", return_value=[]):
            names = [provider["name"] for provider in pdf_fetch.provider_plan("10.1234/test", strategy="third_party_only")]

        self.assertEqual(names, ["LibGen", "Sci-Hub"])

    def test_parser_exposes_third_party_strategy(self):
        parser = pdf_fetch.build_parser()
        args = parser.parse_args(["download", "10.1234/test", "--out", "/tmp", "--strategy", "third_party_only"])

        self.assertEqual(args.strategy, "third_party_only")

    def test_scihub_module_defines_try_scihub(self):
        module = pdf_fetch.load_sibling_module("scihub")

        self.assertTrue(callable(getattr(module, "try_scihub", None)))

    def test_strategy_rejects_unsupported_value(self):
        with self.assertRaises(ValueError):
            pdf_fetch.candidate_urls("10.1234/test", strategy="fastest")

    def test_extract_doaj_candidates(self):
        payload = {
            "results": [
                {
                    "bibjson": {
                        "link": [
                            {"type": "fulltext", "url": "https://example.org/doaj.pdf"},
                            {"type": "other", "url": "https://example.org/skip"},
                        ]
                    }
                }
            ]
        }

        urls = pdf_fetch.extract_doaj_pdf_candidates(payload)

        self.assertEqual(urls, ["https://example.org/doaj.pdf"])

    def test_extract_europepmc_candidates(self):
        payload = {
            "resultList": {
                "result": [
                    {
                        "fullTextUrlList": {
                            "fullTextUrl": [
                                {"documentStyle": "pdf", "url": "https://example.org/europepmc.pdf"}
                            ]
                        }
                    }
                ]
            }
        }

        urls = pdf_fetch.extract_europepmc_pdf_candidates(payload)

        self.assertEqual(urls, ["https://example.org/europepmc.pdf"])

    def test_extract_core_candidates(self):
        payload = {
            "results": [
                {"downloadUrl": "https://repo.example.org/paper.pdf"},
                {"sourceFulltextUrls": ["https://core.ac.uk/data-providers/blocked.pdf"]},
            ]
        }

        urls = pdf_fetch.extract_core_pdf_candidates(payload)

        self.assertEqual(urls, ["https://repo.example.org/paper.pdf"])

    def test_extract_pmc_candidates(self):
        payload = {"records": [{"pmcid": "PMC123456"}]}

        urls = pdf_fetch.extract_pmc_pdf_candidates(payload)

        self.assertEqual(urls, ["https://www.ncbi.nlm.nih.gov/pmc/articles/PMC123456/pdf/"])

    def test_download_pdf_rejects_non_pdf_before_final_save(self):
        class FakeResponse:
            def __init__(self):
                self._fh = io.BytesIO(b"<html>not pdf</html>")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self, size=-1):
                return self._fh.read(size)

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "paper.pdf"
            with mock.patch("urllib.request.urlopen", return_value=FakeResponse()):
                ok = pdf_fetch.download_pdf("https://example.org/paper", dest)

        self.assertFalse(ok)
        self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
