"""Verify the published book, links, and safe document rendering."""

import html
import json
import re
import unittest
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
from urllib.parse import unquote, urlsplit

from scripts.build_site import build


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.ids = set()
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if key in attrs:
                self.links.append(attrs[key])

    def handle_data(self, data):
        self.text.append(data)


class OriginalTextParser(HTMLParser):
    """Read only the source heading/body, excluding reader controls."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.capture = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag in {"meta", "link", "img", "input", "br", "hr"}:
            return
        selected = dict(attrs).get("id") in {"original-preface", "chapter-title", "chapter-body"}
        self.capture.append(selected or bool(self.capture and self.capture[-1]))

    def handle_endtag(self, tag):
        if self.capture:
            self.capture.pop()

    def handle_data(self, data):
        if self.capture and self.capture[-1]:
            self.text.append(data)


class PublishedSiteTests(unittest.TestCase):
    def test_original_reader_has_all_source_entries_and_independent_routes(self):
        page = DOCS / "original.html"
        self.assertTrue(page.is_file(), "The original novel needs its own reading entry")
        catalog = json.loads((DOCS / "original" / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(len(catalog["chapters"]), 158)
        self.assertEqual(catalog["chapters"][0]["title"], "1.第1章：福泽镇上的神秘来客")
        self.assertEqual(catalog["chapters"][-2]["title"], "第一百六十八回：银色琥珀")
        self.assertEqual(catalog["chapters"][-1]["title"], "致《爵迹》读者")
        self.assertEqual(catalog["author"], "郭敬明")
        urls = [chapter["url"] for chapter in catalog["chapters"]]
        self.assertEqual(len(set(urls)), 158, "Repeated source numbering must not overwrite a page")
        for url in urls:
            self.assertTrue((DOCS / url).is_file())
        self.assertIn("original.html", (DOCS / "index.html").read_text(encoding="utf-8"))

    def test_original_download_preserves_the_entire_source_text(self):
        download = DOCS / "downloads" / "jueji-original.txt"
        self.assertTrue(download.is_file(), "Provide the full original text for download")
        self.assertEqual(download.read_bytes(), (ROOT / "site" / "texts" / "jueji.txt").read_bytes())

    def test_original_pages_reconstruct_every_source_character_in_order(self):
        page = DOCS / "original.html"
        self.assertTrue(page.is_file(), "Build the original reader before checking source fidelity")
        parser = OriginalTextParser()
        parser.feed(page.read_text(encoding="utf-8"))
        pieces = parser.text[:]
        catalog = json.loads((DOCS / "original" / "catalog.json").read_text(encoding="utf-8"))
        for chapter in catalog["chapters"]:
            parser = OriginalTextParser()
            parser.feed((DOCS / chapter["url"]).read_text(encoding="utf-8"))
            pieces.extend(parser.text)
        source = (ROOT / "site" / "texts" / "jueji.txt").read_text(encoding="utf-8")
        self.assertEqual(re.sub(r"\s", "", "".join(pieces)), re.sub(r"\s", "", source),
                         "Splitting glued headings must preserve every original character in order")

    def test_writing_skill_zip_is_reproducible_across_path_sorting_semantics(self):
        with TemporaryDirectory() as windows_dir, TemporaryDirectory() as posix_dir:
            windows_output = Path(windows_dir)
            posix_output = Path(posix_dir)
            with mock.patch.object(Path, "__lt__", lambda left, right: left.as_posix().casefold() < right.as_posix().casefold()):
                build(windows_output)
            with mock.patch.object(Path, "__lt__", lambda left, right: left.as_posix() < right.as_posix()):
                build(posix_output)
            self.assertEqual(
                (windows_output / "downloads" / "writing-skill.zip").read_bytes(),
                (posix_output / "downloads" / "writing-skill.zip").read_bytes(),
                "The complete skill ZIP must be identical for Windows and POSIX path ordering",
            )

    def test_home_and_complete_catalog_exist(self):
        self.assertTrue((DOCS / "index.html").is_file(), "Build the static reading site first")
        page = (DOCS / "index.html").read_text(encoding="utf-8")
        for number in range(169, 194):
            self.assertIn(f"chapters/chapter-{number}.html", page)
        self.assertIn("80517", page.replace(",", ""))

    def test_all_twenty_five_chapters_preserve_every_paragraph(self):
        sources = {int(m.group(1)): p for p in (ROOT / "续写").glob("*.md")
                   if (m := re.match(r"第(\d+)回-", p.name))}
        sources[169] = ROOT / "续写" / "第一百六十九回-未熄之门.md"
        for number, source in sorted(sources.items()):
            with self.subTest(chapter=number):
                page = DOCS / "chapters" / f"chapter-{number}.html"
                self.assertTrue(page.is_file())
                parser = PageParser()
                parser.feed(page.read_text(encoding="utf-8"))
                rendered = re.sub(r"\s", "", "".join(parser.text))
                body = source.read_text(encoding="utf-8").split("\n## 正文\n", 1)[1]
                for paragraph in re.split(r"\n\s*\n", body):
                    expected = re.sub(r"\s", "", paragraph).strip()
                    if expected:
                        self.assertIn(expected, rendered)

    def test_local_links_and_assets_work_under_a_project_subpath(self):
        pages = list(DOCS.rglob("*.html"))
        self.assertGreaterEqual(len(pages), 28)
        for page in pages:
            parser = PageParser()
            parser.feed(page.read_text(encoding="utf-8"))
            for target in parser.links:
                url = urlsplit(target)
                if url.scheme or url.netloc or not url.path:
                    continue
                with self.subTest(page=page.name, link=target):
                    self.assertFalse(url.path.startswith("/"), "Project Pages needs relative paths")
                    resolved = (page.parent / unquote(url.path)).resolve()
                    self.assertTrue(resolved.is_relative_to(DOCS.resolve()))
                    self.assertTrue(resolved.is_file(), resolved)

    def test_documents_downloads_and_final_ending_are_present(self):
        self.assertTrue((DOCS / "outline.html").is_file())
        self.assertTrue((DOCS / "writing.html").is_file())
        self.assertTrue((DOCS / "downloads" / "aslan-complete.md").is_file())
        self.assertTrue((DOCS / "downloads" / "writing-skill.md").is_file())
        archive = DOCS / "downloads" / "writing-skill.zip"
        self.assertTrue(archive.is_file())
        with zipfile.ZipFile(archive) as package:
            self.assertIn("lyrical-epic-fantasy-writing/SKILL.md", package.namelist())
            self.assertIn("lyrical-epic-fantasy-writing/references/style-guide.md", package.namelist())
            self.assertIn("lyrical-epic-fantasy-writing/references/outline-template.md", package.namelist())
        final = (DOCS / "chapters" / "chapter-193.html").read_text(encoding="utf-8")
        self.assertIn("（终）", final)
        self.assertNotIn("{{", final)


if __name__ == "__main__":
    unittest.main()
