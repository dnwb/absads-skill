import argparse
import importlib.util
import io
import tarfile
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ads_scix.py"
SPEC = importlib.util.spec_from_file_location("ads_scix", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
ads_scix = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ads_scix)


class AdsScixCliTest(unittest.TestCase):
    def test_arxiv_user_agent_default_and_override(self):
        for value, expected in [(None, "absads/1.0"), ("absads-test/1.0 (mailto:user@example.org)", "absads-test/1.0 (mailto:user@example.org)")]:
            with self.subTest(value=value), mock.patch.dict(ads_scix.os.environ):
                ads_scix.os.environ.pop("ARXIV_USER_AGENT", None)
                if value is not None:
                    ads_scix.os.environ["ARXIV_USER_AGENT"] = value
                assert SPEC is not None and SPEC.loader is not None
                module = importlib.util.module_from_spec(SPEC)
                SPEC.loader.exec_module(module)
                self.assertEqual(module.ARXIV_USER_AGENT, expected)

    def test_arxiv_valid_cli_dispatches_target(self):
        cases = [
            (["--id-list", "2401.01234v2"], "id_list", "2401.01234v2", "search_query"),
            (["all:galaxy"], "search_query", "all:galaxy", "id_list"),
        ]
        for argv, present_key, expected_val, absent_key in cases:
            with self.subTest(argv=argv), mock.patch("sys.argv", ["ads_scix.py", "arxiv", "search", *argv]), mock.patch.object(ads_scix, "arxiv_request", return_value=b'<feed xmlns="http://www.w3.org/2005/Atom"/>') as request, mock.patch("sys.stdout", new=io.StringIO()):
                ads_scix.main()
            self.assertEqual(request.call_args.args[0][present_key], expected_val)
            self.assertNotIn(absent_key, request.call_args.args[0])

    def test_arxiv_invalid_cli_never_requests_network(self):
        for argv in [
            [],
            ["   "],
            ["all:galaxy", "--id-list", "2401.01234"],
            ["", "--id-list", "2401.01234"],
            ["   ", "--id-list", "2401.01234"],
            ["--id-list", ""],
            ["--id-list", "   "],
            ["--id-list", "2401.01234", ""],
        ]:
            with self.subTest(argv=argv):
                with mock.patch("sys.argv", ["ads_scix.py", "arxiv", "search", *argv]), mock.patch.object(ads_scix, "arxiv_request") as request, mock.patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit) as error:
                    ads_scix.main()
                self.assertEqual(error.exception.code, 2)
                request.assert_not_called()

    def test_arxiv_request_sends_configured_user_agent(self):
        for agent in [ads_scix.ARXIV_USER_AGENT, "custom-agent/2.0 (mailto:test@example.org)"]:
            with self.subTest(agent=agent), mock.patch.object(ads_scix, "ARXIV_USER_AGENT", agent):
                response = mock.MagicMock()
                response.__enter__.return_value.read.return_value = b"<feed/>"
                with mock.patch.object(ads_scix.urllib.request, "urlopen", return_value=response) as urlopen:
                    ads_scix.arxiv_request({"search_query": "all:galaxy"})
                request = urlopen.call_args.args[0]
                self.assertEqual(request.full_url, "https://export.arxiv.org/api/query?search_query=all%3Agalaxy")
                self.assertEqual(request.get_header("User-agent"), agent)
                self.assertEqual(request.get_header("Accept"), "application/atom+xml")

    def test_parse_arxiv_feed_normalizes_metadata_and_provenance(self):
        raw = b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
          <opensearch:totalResults>1</opensearch:totalResults>
          <opensearch:startIndex>0</opensearch:startIndex><opensearch:itemsPerPage>5</opensearch:itemsPerPage>
          <entry><id>http://arxiv.org/abs/2401.01234v2</id><title> A title\n here </title><summary> Abstract text. </summary>
          <published>2024-01-01T00:00:00Z</published><updated>2024-02-01T00:00:00Z</updated>
          <author><name>A. Author</name></author><category term="astro-ph.GA"/><arxiv:doi>10.1234/example</arxiv:doi>
          <link href="http://arxiv.org/pdf/2401.01234v2" type="application/pdf"/></entry></feed>'''
        params = {"search_query": "all:galaxy AND cat:astro-ph.GA", "start": "0"}
        parsed = ads_scix.parse_arxiv_feed(raw, params=params)

        self.assertEqual(parsed["source"], "arXiv API")
        self.assertEqual(parsed["query"], params)
        self.assertEqual(parsed["source_url"], "https://export.arxiv.org/api/query?search_query=all%3Agalaxy+AND+cat%3Aastro-ph.GA&start=0")
        self.assertEqual(parsed["total_results"], "1")
        self.assertEqual(parsed["start_index"], "0")
        self.assertEqual(parsed["items_per_page"], "5")
        self.assertEqual(parsed["entries"][0]["arxiv_id"], "2401.01234v2")
        self.assertEqual(parsed["entries"][0]["title"], "A title here")
        self.assertEqual(parsed["entries"][0]["doi"], "10.1234/example")

    def test_arxiv_search_builds_expected_params(self):
        cases = [
            (
                argparse.Namespace(query="all:galaxy", id_list=None, start=0, max_results=5, sort_by="submittedDate", sort_order="descending"),
                {"search_query": "all:galaxy", "start": "0", "max_results": "5", "sortBy": "submittedDate", "sortOrder": "descending"},
            ),
            (
                argparse.Namespace(query="  all:galaxy  ", id_list=[], start=0, max_results=5, sort_by="submittedDate", sort_order="descending"),
                {"search_query": "all:galaxy", "start": "0", "max_results": "5", "sortBy": "submittedDate", "sortOrder": "descending"},
            ),
            (
                argparse.Namespace(query=None, id_list=[" 2401.01234v2 ", " 2401.05678 "], start=0, max_results=10, sort_by="relevance", sort_order="descending"),
                {"id_list": "2401.01234v2,2401.05678", "start": "0", "max_results": "10", "sortBy": "relevance", "sortOrder": "descending"},
            ),
        ]
        for args, expected in cases:
            with self.subTest(args=args), mock.patch.object(ads_scix, "arxiv_request", return_value=b'<feed xmlns="http://www.w3.org/2005/Atom"/>') as request, mock.patch("sys.stdout", new=io.StringIO()):
                ads_scix.command_arxiv_search(args)
            request.assert_called_once_with(expected)

    def test_command_arxiv_search_rejects_invalid_programmatic_args(self):
        invalid_args = [
            argparse.Namespace(query="all:galaxy", id_list=["2401.01234"]),
            argparse.Namespace(query="", id_list=None),
            argparse.Namespace(query="   ", id_list=None),
            argparse.Namespace(query=None, id_list=[]),
            argparse.Namespace(query=None, id_list=[""]),
            argparse.Namespace(query=None, id_list=["   "]),
        ]
        for args in invalid_args:
            with self.subTest(args=args), mock.patch.object(ads_scix, "arxiv_request") as request, mock.patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit) as error:
                ads_scix.command_arxiv_search(args)
            self.assertEqual(error.exception.code, 2)
            request.assert_not_called()

    def test_search_builds_expected_query_params(self):
        args = argparse.Namespace(
            query='author:"Hubble" year:1929',
            fields=["bibcode", "title", "author"],
            rows=5,
            start=0,
            sort="citation_count desc",
            filter=["property:refereed"],
        )

        with mock.patch.object(ads_scix, "request", return_value=b"{}") as request, mock.patch.object(
            ads_scix, "print_json"
        ):
            ads_scix.command_search(args)

        request.assert_called_once_with(
            "GET",
            "/v1/search/query",
            params={
                "q": 'author:"Hubble" year:1929',
                "fl": "bibcode,title,author",
                "rows": "5",
                "start": "0",
                "sort": "citation_count desc",
                "fq": ["property:refereed"],
            },
        )

    def test_export_one_bibcode_uses_get(self):
        args = argparse.Namespace(format="bibtex", bibcodes=["1929PNAS...15..168H"])

        with mock.patch.object(ads_scix, "request", return_value=b"@article{}") as request, mock.patch("sys.stdout", new=io.StringIO()):
            ads_scix.command_export(args)

        request.assert_called_once_with("GET", "/v1/export/bibtex/1929PNAS...15..168H")

    def test_export_multiple_bibcodes_uses_post(self):
        args = argparse.Namespace(format="ris", bibcodes=["A", "B"])

        with mock.patch.object(ads_scix, "request", return_value=b"TY  - JOUR") as request, mock.patch("sys.stdout", new=io.StringIO()):
            ads_scix.command_export(args)

        request.assert_called_once_with("POST", "/v1/export/ris", data={"bibcode": ["A", "B"]})

    def test_metrics_one_bibcode_uses_get(self):
        args = argparse.Namespace(bibcodes=["1929PNAS...15..168H"], types=["basic", "citations"])

        with mock.patch.object(ads_scix, "request", return_value=b"{}") as request, mock.patch.object(
            ads_scix, "print_json"
        ):
            ads_scix.command_metrics(args)

        request.assert_called_once_with("GET", "/v1/metrics/1929PNAS...15..168H")

    def test_metrics_multiple_bibcodes_uses_post(self):
        args = argparse.Namespace(bibcodes=["A", "B"], types=["basic", "citations"])

        with mock.patch.object(ads_scix, "request", return_value=b"{}") as request, mock.patch.object(
            ads_scix, "print_json"
        ):
            ads_scix.command_metrics(args)

        request.assert_called_once_with(
            "POST", "/v1/metrics", data={"bibcodes": ["A", "B"], "types": ["basic", "citations"]}
        )

    def test_find_arxiv_id_preserves_version(self):
        self.assertEqual(ads_scix.find_arxiv_id(["doi:10.0/x", "arXiv:1204.4485v3"]), "1204.4485v3")

    def test_source_with_explicit_arxiv_id_skips_ads_lookup(self):
        args = argparse.Namespace(bibcode="ignored", arxiv_id="1204.4485", out="unused")

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(ads_scix, "metadata_for_bibcode") as metadata, mock.patch.object(
            ads_scix, "download"
        ) as download, mock.patch.object(ads_scix, "extract_archive") as extract, mock.patch("sys.stdout", new=io.StringIO()):
            args.out = tmp
            ads_scix.command_source(args)

        metadata.assert_not_called()
        self.assertEqual(download.call_args.args[0], "https://arxiv.org/src/1204.4485")
        self.assertEqual(extract.call_args.args[1], Path(tmp).resolve())

    def test_extract_archive_extracts_safe_tar_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "safe.tar"
            source = root / "paper.tex"
            source.write_text("content")
            with tarfile.open(archive, "w") as tar:
                tar.add(source, arcname="paper.tex")

            out = root / "out"
            ads_scix.extract_archive(archive, out)

            self.assertEqual((out / "paper.tex").read_text(), "content")

    def test_extract_archive_rejects_parent_traversal_tar_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "evil.tar"
            source = root / "evil.tex"
            source.write_text("bad")
            with tarfile.open(archive, "w") as tar:
                tar.add(source, arcname="../evil.tex")

            out = root / "out"
            with self.assertRaises((SystemExit, ValueError)):
                ads_scix.extract_archive(archive, out)

            self.assertFalse((root / "evil.tex.outside").exists())
            self.assertFalse((root.parent / "evil.tex").exists())

    def test_extract_archive_rejects_absolute_tar_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "absolute.tar"
            with tarfile.open(archive, "w") as tar:
                payload = b"bad"
                info = tarfile.TarInfo("/tmp/evil.tex")
                info.size = len(payload)
                tar.addfile(info, BytesIO(payload))

            with self.assertRaises((SystemExit, ValueError)):
                ads_scix.extract_archive(archive, root / "out")


if __name__ == "__main__":
    unittest.main()
