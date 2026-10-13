"""Verify the published book, links, and safe document rendering."""

import html
import re
import unittest
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


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


class PublishedSiteTests(unittest.TestCase):
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
