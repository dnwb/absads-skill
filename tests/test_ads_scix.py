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
ads_scix = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ads_scix)


class AdsScixCliTest(unittest.TestCase):
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
