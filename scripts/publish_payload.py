"""Export an explicitly scoped Git tree, without credentials or local caches."""

import argparse
import base64
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".work" / "github-manifest.json"
DIRECTORIES = (".github", "scripts", "tests", "site", "docs", "skills", "续写")
ROOT_FILES = ("README.md", "AGENTS.md", ".gitignore")


def manifest():
    files = [ROOT / name for name in ROOT_FILES]
    for name in DIRECTORIES:
        files.extend(path for path in (ROOT / name).rglob("*") if path.is_file()
                     and not {"__pycache__", "node_modules", ".git"}.intersection(path.parts))
    entries = []
    for path in sorted(set(files)):
        data = path.read_bytes()
        try:
            data.decode("utf-8")
            encoding = "utf-8"
        except UnicodeDecodeError:
            encoding = "base64"
        if path.suffix == ".zip":
            encoding = "base64"
        digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        entries.append({"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha": digest, "encoding": encoding})
    MANIFEST.parent.mkdir(exist_ok=True)
    MANIFEST.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    return entries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read", type=int)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--size", type=int, default=12000)
    args = parser.parse_args()
    if args.read is None:
        print(json.dumps(manifest(), ensure_ascii=False))
    else:
        entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
        path = (ROOT / entries[args.read]["path"]).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError("Path escapes workspace")
        with path.open("rb") as stream:
            stream.seek(args.offset)
            print(base64.b64encode(stream.read(args.size)).decode("ascii"))
