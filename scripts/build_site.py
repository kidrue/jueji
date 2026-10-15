"""Build a self-contained static book from the project's UTF-8 chapter files."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
STAGES = (
    ("intro", "序幕 · 未熄之门", 169, 169),
    ("rescue", "一 · 突围与保命", 170, 177),
    ("truth", "二 · 真相与选择", 178, 185),
    ("ending", "三 · 破阵与归来", 186, 193),
)
DESCRIPTION = "《爵迹》亚斯蓝终篇非官方续作：二十五回完整阅读，章节目录、续读、夜间模式与写作指南。"


@dataclass(frozen=True)
class Chapter:
    number: int
    title: str
    full_title: str
    body: str
    words: int
    stage: str


@dataclass(frozen=True)
class OriginalEntry:
    number: int
    full_title: str
    body: str
    words: int
    source_number: int | None


def source_number(numeral: str) -> int:
    if numeral.isdecimal():
        return int(numeral)
    if numeral == "一六十":
        return 160  # The local file's heading omits 百; its displayed text stays unchanged.
    digits = dict(zip("零〇一二三四五六七八九两", (0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 2)))
    units = {"十": 10, "百": 100, "千": 1000}
    total = value = 0
    for char in numeral:
        if char in units:
            total += (value or 1) * units[char]
            value = 0
        else:
            value = digits[char]
    return total + value


def load_original() -> tuple[str, list[OriginalEntry]]:
    text = (SITE / "texts" / "jueji.txt").read_bytes().decode("utf-8")
    matches = list(re.finditer(r"(?:\d+\.)?第([零〇一二三四五六七八九十百千两\d]+)[章回][^\r\n]+", text))
    if not matches:
        raise ValueError("The original text has no chapter headings")
    appendix = text.rfind("致《爵迹》读者")
    has_appendix = appendix > matches[-1].end()
    end = appendix if has_appendix else len(text)
    entries = []
    for index, match in enumerate(matches):
        following = matches[index + 1].start() if index + 1 < len(matches) else end
        body = text[match.end():following]
        entries.append(OriginalEntry(index + 1, match.group(), body,
                                     len(re.sub(r"\s", "", body)), source_number(match.group(1))))
    if has_appendix:
        title = "致《爵迹》读者"
        body = text[appendix + len(title):]
        entries.append(OriginalEntry(len(entries) + 1, title, body, len(re.sub(r"\s", "", body)), None))
    return text[:matches[0].start()], entries


def plain_text_html(text: str) -> str:
    return "\n".join(
        (f'<h3 class="scene-heading">{html.escape(line.strip())}</h3>'
         if line.strip().startswith("【") and line.strip().endswith("】")
         else f"<p>{html.escape(line.strip())}</p>")
        for line in text.splitlines() if line.strip()
    )


def original_toc(entries: list[OriginalEntry], rel: str, current: int | None = None) -> str:
    links = []
    for entry in entries:
        selected = ' aria-current="page"' if current == entry.number else ""
        links.append(f'<a class="toc-link" data-number="{entry.number}" href="{rel}chapter-{entry.number}.html"{selected}><span>{entry.number:03d}</span> {html.escape(entry.full_title)}</a>')
    return '<section class="toc-group"><h3>新版 · 按文本顺序</h3>' + "".join(links) + "</section>"


def load_chapters() -> list[Chapter]:
    sources = {}
    for path in (ROOT / "续写").glob("*.md"):
        match = re.match(r"第(\d+)回-", path.name)
        if match:
            sources[int(match.group(1))] = path
    sources[169] = ROOT / "续写" / "第一百六十九回-未熄之门.md"
    chapters = []
    for number in range(169, 194):
        if number not in sources or not sources[number].is_file():
            raise ValueError(f"Missing chapter {number}")
        text = sources[number].read_text(encoding="utf-8")
        if "\n## 正文\n" not in text:
            raise ValueError(f"Missing body for chapter {number}")
        body = text.split("\n## 正文\n", 1)[1].strip()
        words = len(re.sub(r"\s", "", body))
        if not 3000 <= words <= 4000:
            raise ValueError(f"Invalid chapter {number} length: {words}")
        full_title = text.splitlines()[0].lstrip("# ")
        title = re.split(r"[：:]", full_title, maxsplit=1)[-1]
        stage = next(key for key, _, first, last in STAGES if first <= number <= last)
        chapters.append(Chapter(number, title, full_title, body, words, stage))
    return chapters


def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    def link(match):
        label, target = match.groups()
        target = html.unescape(target)
        target = {
            "references/style-guide.md": "writing.html#style-guide",
            "references/outline-template.md": "writing.html#outline-template",
        }.get(target, target)
        parsed = urlsplit(target)
        if parsed.scheme and parsed.scheme not in {"https", "http"}:
            return label
        if target.startswith("//"):
            return label
        return f'<a href="{html.escape(target, quote=True)}">{label}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)


def markdown_document(text: str) -> str:
    text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, flags=re.S)
    lines = text.splitlines()
    result = []
    index = 0
    heading_index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("```"):
            index += 1
            code = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            result.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
            index += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)", line)
        if heading:
            heading_index += 1
            level = min(6, max(2, len(heading.group(1))))
            result.append(f'<h{level} id="section-{heading_index}">{inline(heading.group(2))}</h{level}>')
            index += 1
            continue
        if line.startswith("|") and index + 1 < len(lines) and re.match(r"^\s*\|[\s:|\-]+\|\s*$", lines[index + 1]):
            headers = [value.strip() for value in line.strip("|").split("|")]
            result.append('<div class="table-wrap"><table><thead><tr>' + "".join(f"<th>{inline(h)}</th>" for h in headers) + "</tr></thead><tbody>")
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [value.strip() for value in lines[index].strip().strip("|").split("|")]
                result.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
                index += 1
            result.append("</tbody></table></div>")
            continue
        list_match = re.match(r"^(?:([-*])|(\d+)\.)\s+(.*)", line)
        if list_match:
            tag = "ol" if list_match.group(2) else "ul"
            result.append(f"<{tag}>")
            while index < len(lines):
                match = re.match(r"^(?:([-*])|(\d+)\.)\s+(.*)", lines[index].strip())
                if not match or ("ol" if match.group(2) else "ul") != tag:
                    break
                result.append("<li>" + inline(match.group(3)) + "</li>")
                index += 1
            result.append(f"</{tag}>")
            continue
        if line.startswith(">"):
            result.append("<blockquote><p>" + inline(line.lstrip("> ")) + "</p></blockquote>")
        else:
            result.append("<p>" + inline(line) + "</p>")
        index += 1
    return "\n".join(result)


def chapter_html(body: str) -> str:
    parts = []
    for paragraph in re.split(r"\n\s*\n", body):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if paragraph.startswith("【") and paragraph.endswith("】"):
            parts.append('<h3 class="scene-heading">' + html.escape(paragraph) + "</h3>")
        else:
            parts.append("<p>" + html.escape(paragraph) + "</p>")
    return "\n".join(parts)


def toc(chapters: list[Chapter], rel: str, current: int | None = None) -> str:
    groups = []
    for stage, name, first, last in STAGES:
        links = []
        for chapter in chapters:
            if chapter.stage != stage:
                continue
            selected = ' aria-current="page"' if current == chapter.number else ""
            links.append(f'<a class="toc-link" data-number="{chapter.number}" href="{rel}chapters/chapter-{chapter.number}.html"{selected}><span>{chapter.number}</span> {html.escape(chapter.title)}</a>')
        groups.append(f'<section class="toc-group"><h3>{html.escape(name)}</h3>' + "".join(links) + "</section>")
    return "\n".join(groups)


def template(name: str, values: dict[str, str]) -> str:
    source = (SITE / "templates" / f"{name}.html").read_text(encoding="utf-8")
    for key, value in values.items():
        source = source.replace("{{" + key + "}}", value)
    if re.search(r"\{\{[A-Z_]+\}\}", source):
        raise ValueError(f"Unfilled template placeholder in {name}")
    return source


def write_page(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build(output: Path) -> dict:
    chapters = load_chapters()
    output.mkdir(parents=True, exist_ok=True)
    assets = output / "assets"
    assets.mkdir(exist_ok=True)
    for filename in ("styles.css", "app.js", "cover.svg", "old-reader.js", "old-reader.css"):
        shutil.copyfile(SITE / filename, assets / filename)
    cards = []
    for chapter in chapters:
        prose = next(p.strip() for p in re.split(r"\n\s*\n", chapter.body) if p.strip() and not p.strip().startswith("【"))
        teaser = prose[:54] + ("…" if len(prose) > 54 else "")
        cards.append(f'<a class="chapter-card" data-number="{chapter.number}" data-title="{html.escape(chapter.title, quote=True)}" data-stage="{chapter.stage}" href="chapters/chapter-{chapter.number}.html"><span class="chapter-number">{chapter.number}</span><span class="chapter-card-copy"><strong class="chapter-title">{html.escape(chapter.title)}</strong><span class="chapter-teaser">{html.escape(teaser)}</span><span class="chapter-meta">{chapter.words:,} 字 · 约 {math.ceil(chapter.words / 500)} 分钟</span></span><span class="chapter-card-arrow" aria-hidden="true">↗</span></a>')
    total = sum(c.words for c in chapters)
    common = {"DESCRIPTION": html.escape(DESCRIPTION, quote=True), "BOOK_ID": "continuation",
              "MIN_CHAPTER": "169", "MAX_CHAPTER": "193", "CHAPTER_COUNT": "25",
              "BOOK_HOME": "index.html", "BOOK_CAPTION": "亚斯蓝终篇",
              "BOOK_TITLE": "爵迹 · 亚斯蓝终篇", "BOOK_NOTE": "非官方续篇",
              "EDITION": "ASLAN / 亚斯蓝终篇", "ORIGINAL_CURRENT": "", "EDITION_LINKS": ""}
    write_page(output / "old.html", template("old", {"REL": "./"}))
    write_page(output / "index.html", template("home", common | {"REL": "./", "PAGE_TITLE": "爵迹 · 亚斯蓝终篇", "TOC": toc(chapters, "./"), "WORD_COUNT": f"{total:,}", "CHAPTER_CARDS": "\n".join(cards)}))
    for index, chapter in enumerate(chapters):
        previous = chapters[index - 1] if index else None
        following = chapters[index + 1] if index + 1 < len(chapters) else None
        values = common | {"REL": "../", "PAGE_TITLE": html.escape(chapter.full_title + " · 爵迹"), "NUMBER": str(chapter.number), "CHAPTER_LABEL": f"第 {chapter.number} 回", "TITLE": html.escape(chapter.title), "WORDS": f"{chapter.words:,}", "READ_TIME": str(math.ceil(chapter.words / 500)), "BODY": chapter_html(chapter.body), "TOC": toc(chapters, "../", chapter.number), "PREV_URL": f"chapter-{previous.number}.html" if previous else "../index.html", "NEXT_URL": f"chapter-{following.number}.html" if following else "../index.html", "PREV_LABEL": html.escape(previous.full_title) if previous else "返回书目", "NEXT_LABEL": html.escape(following.full_title) if following else "读完全篇 · 返回书目"}
        write_page(output / "chapters" / f"chapter-{chapter.number}.html", template("chapter", values))
    skill = ROOT / "skills" / "lyrical-epic-fantasy-writing"
    writing = '<section id="writing-workflow">' + markdown_document((skill / "SKILL.md").read_text(encoding="utf-8")) + "</section>"
    writing += '<section id="style-guide">' + markdown_document((skill / "references" / "style-guide.md").read_text(encoding="utf-8")) + "</section>"
    writing += '<section id="outline-template">' + markdown_document((skill / "references" / "outline-template.md").read_text(encoding="utf-8")) + "</section>"
    outline = (ROOT / "续写" / "终篇大纲.md").read_text(encoding="utf-8").split("\n## 阶段交接契约", 1)[0]
    actual = (ROOT / "续写" / "终篇大纲.md").read_text(encoding="utf-8").split("\n## 实际分场大纲", 1)[1]
    outline += "\n## 实际分场大纲" + actual
    for filename, title, kind, content in (("outline.html", "终篇大纲", "剧情安排 · 含剧透", markdown_document(outline)), ("writing.html", "写作技能与风格指南", "先纲后文 · 写作笔记", writing)):
        values = common | {"REL": "./", "PAGE_TITLE": title + " · 爵迹", "TITLE": title, "DOC_KIND": kind, "BODY": content, "TOC": toc(chapters, "./")}
        write_page(output / filename, template("document", values))
    downloads = output / "downloads"
    downloads.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "续写" / "爵迹-亚斯蓝终篇.md", downloads / "aslan-complete.md")
    shutil.copyfile(skill / "SKILL.md", downloads / "writing-skill.md")
    with zipfile.ZipFile(downloads / "writing-skill.zip", "w", compression=zipfile.ZIP_STORED) as package:
        for path in sorted(skill.rglob("*"), key=lambda path: path.relative_to(skill).as_posix().casefold()):
            if path.is_file():
                entry = zipfile.ZipInfo("lyrical-epic-fantasy-writing/" + path.relative_to(skill).as_posix(), (1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = 0o644 << 16
                package.writestr(entry, path.read_bytes())
    (output / ".nojekyll").write_text("", encoding="utf-8")
    metadata = {"chapters": [{"number": c.number, "title": c.title, "words": c.words, "stage": c.stage, "url": f"chapters/chapter-{c.number}.html"} for c in chapters], "total_words": total}
    write_page(output / "catalog.json", json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    original = build_original(output, common)
    return {"pages": 29 + original["pages"], "chapters": len(chapters), "body_characters": total,
            "original_entries": original["entries"], "output": str(output)}


def build_original(output: Path, common: dict[str, str]) -> dict:
    preface, entries = load_original()
    count = len(entries)
    values = common | {"BOOK_ID": "original", "MIN_CHAPTER": "1", "MAX_CHAPTER": str(count),
                       "CHAPTER_COUNT": str(count), "BOOK_HOME": "original.html",
                       "BOOK_CAPTION": "新版 · 修订连载", "BOOK_TITLE": "爵迹 · 新版",
                       "BOOK_NOTE": "郭敬明 · 本地修订连载文本", "EDITION": "REVISED / 新版 · 修订连载",
                       "ORIGINAL_CURRENT": ' aria-current="page"',
                       "DESCRIPTION": "郭敬明《爵迹》新版修订连载阅读，使用本地文本，收录至《银色琥珀》及读者附记，与《临界·爵迹》旧版分开阅读。"}
    cards = []
    for entry in entries:
        prose = next((line.strip() for line in entry.body.splitlines() if line.strip() and not line.strip().startswith("【")), "")
        teaser = prose[:54] + ("…" if len(prose) > 54 else "")
        searchable = (f"第{entry.source_number}回 第{entry.source_number}章 {entry.full_title}"
                      if entry.source_number else entry.full_title)
        cards.append(f'<a class="chapter-card" data-number="{entry.number}" data-title="{html.escape(entry.full_title, quote=True)}" data-search="{html.escape(searchable, quote=True)}" data-stage="original" href="original/chapter-{entry.number}.html"><span class="chapter-number">{entry.number:03d}</span><span class="chapter-card-copy"><strong class="chapter-title">{html.escape(entry.full_title)}</strong><span class="chapter-teaser">{html.escape(teaser)}</span><span class="chapter-meta">{entry.words:,} 字 · 约 {math.ceil(entry.words / 500)} 分钟</span></span><span class="chapter-card-arrow" aria-hidden="true">↗</span></a>')
    full_source = (SITE / "texts" / "jueji.txt").read_bytes()
    words = len(re.sub(r"\s", "", full_source.decode("utf-8")))
    write_page(output / "original.html", template("original", values | {
        "REL": "./", "PAGE_TITLE": "爵迹 · 新版修订连载", "WORD_COUNT": f"{words:,}",
        "CHAPTER_CARDS": "\n".join(cards), "TOC": original_toc(entries, "original/"),
        "PREFACE": plain_text_html(preface)}))
    for index, entry in enumerate(entries):
        previous = entries[index - 1] if index else None
        following = entries[index + 1] if index + 1 < count else None
        page = values | {"REL": "../", "PAGE_TITLE": html.escape(entry.full_title + " · 爵迹新版"),
                         "EDITION_LINKS": '<nav class="edition-switch" aria-label="原著版本"><a href="../old.html">旧版 · 临界 ↗</a><a href="../original.html" aria-current="page">新版 · 修订连载</a></nav>',
                         "NUMBER": str(entry.number), "CHAPTER_LABEL": "新版阅读" if entry.source_number else "作者附记",
                         "TITLE": html.escape(entry.full_title), "WORDS": f"{entry.words:,}",
                         "READ_TIME": str(math.ceil(entry.words / 500)), "BODY": plain_text_html(entry.body),
                         "TOC": original_toc(entries, "", entry.number),
                         "PREV_URL": f"chapter-{previous.number}.html" if previous else "../original.html",
                         "NEXT_URL": f"chapter-{following.number}.html" if following else "../original.html",
                         "PREV_LABEL": html.escape(previous.full_title) if previous else "返回原文目录",
                         "NEXT_LABEL": html.escape(following.full_title) if following else "读完本地原文 · 返回目录"}
        write_page(output / "original" / f"chapter-{entry.number}.html", template("chapter", page))
    shutil.copyfile(SITE / "texts" / "jueji.txt", output / "downloads" / "jueji-original.txt")
    catalog = {"book": "original", "edition": "revised-serial", "author": "郭敬明", "total_words": words,
               "chapters": [{"number": e.number, "title": e.full_title, "source_number": e.source_number,
                             "words": e.words, "url": f"original/chapter-{e.number}.html"} for e in entries]}
    write_page(output / "original" / "catalog.json", json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    return {"entries": count, "pages": count + 1}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs")
    args = parser.parse_args()
    print(json.dumps(build(args.output.resolve()), ensure_ascii=False))
