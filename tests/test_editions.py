"""The two author editions and the unofficial continuation must stay distinct."""
import json
from pathlib import Path
import unittest

from test_site import PageParser


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class EditionTests(unittest.TestCase):
    maxDiff = 1000
    def test_old_edition_has_an_honest_local_import_entry(self):
        page = DOCS / "old.html"
        self.assertTrue(page.is_file(), "Old edition needs a separate entry")
        text = page.read_text(encoding="utf-8")
        self.assertIn("临界·爵迹", text)
        self.assertIn("尚未导入旧版全文", text)
        self.assertIn('type="file"', text)
        self.assertIn("书目与购阅渠道", text)
        self.assertNotIn("下载旧版全文", text)
        parser = PageParser()
        parser.feed(text)
        self.assertIn("old-file", parser.ids)
        self.assertIn("old-reader", parser.ids)
        self.assertIn("old-toc", parser.ids)
        self.assertTrue((DOCS / "assets" / "old-reader.js").is_file())

    def test_revised_label_preserves_existing_routes_and_full_text(self):
        home = (DOCS / "original.html").read_text(encoding="utf-8")
        chapter = (DOCS / "original" / "chapter-1.html").read_text(encoding="utf-8")
        for page in (home, chapter):
            self.assertIn("新版", page)
            self.assertIn("修订连载", page)
            self.assertIn('data-book="original"', page,
                          "Keep the existing revised-edition progress namespace")
        self.assertIn("并非纸书全套", home)
        catalog = json.loads((DOCS / "original" / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["edition"], "revised-serial")
        self.assertEqual(catalog["chapters"][0]["url"], "original/chapter-1.html")
        self.assertEqual((DOCS / "downloads" / "jueji-original.txt").read_bytes(),
                         (ROOT / "site" / "texts" / "jueji.txt").read_bytes())

    def test_every_page_exposes_both_editions_and_the_continuation(self):
        missing = []
        for path in DOCS.rglob("*.html"):
            parser = PageParser()
            parser.feed(path.read_text(encoding="utf-8"))
            for target in ("old.html", "original.html", "index.html"):
                if not any(href.endswith(target) for href in parser.links):
                    missing.append((str(path.relative_to(DOCS)), target))
        self.assertFalse(missing, f"Missing edition links: {missing[:5]}")


if __name__ == "__main__":
    unittest.main()
