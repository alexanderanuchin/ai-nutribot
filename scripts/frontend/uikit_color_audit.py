#!/usr/bin/env python3
"""Scan a directory for hard-coded color literals.

The script reports hex, RGB(A), and HSL(A) color literals across supported source
files. Results are emitted in Markdown format to stdout.
"""
from __future__ import annotations

import argparse
import dataclasses
import pathlib
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Tuple

COLOR_PATTERN = re.compile(
    r"(?P<color>"
    r"#(?:[0-9a-fA-F]{3,8})"
    r"|rgba?\\(\\s*\\d{1,3}\\s*,\\s*\\d{1,3}\\s*,\\s*\\d{1,3}(?:\\s*,\\s*(?:0?\\.\\d+|1|0))?\\s*\\)"
    r"|hsla?\\(\\s*\\d{1,3}\\s*,\\s*\\d{1,3}%\\s*,\\s*\\d{1,3}%(?:\\s*,\\s*(?:0?\\.\\d+|1|0))?\\s*\\)"
    r")"
)

SUPPORTED_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".json",
    ".mdx",
    ".html",
}


@dataclasses.dataclass
class Occurrence:
    path: pathlib.Path
    line_number: int
    line_text: str


def iter_source_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in SUPPORTED_EXTENSIONS:
            yield path


def find_color_literals(path: pathlib.Path) -> List[Tuple[str, Occurrence]]:
    occurrences: List[Tuple[str, Occurrence]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return occurrences

    for idx, line in enumerate(text.splitlines(), start=1):
        for match in COLOR_PATTERN.finditer(line):
            color = match.group("color")
            occurrences.append((color, Occurrence(path, idx, line.strip())))
    return occurrences


def render_markdown(report: Dict[str, List[Occurrence]], root: pathlib.Path) -> str:
    lines: List[str] = []
    lines.append("# UIKit Color Audit")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Scanned path: `{root}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Color | Occurrences | Example files |")
    lines.append("| --- | ---: | --- |")
    for color, occurrences in sorted(report.items(), key=lambda item: (-len(item[1]), item[0])):
        example_paths = sorted({occ.path.relative_to(root) for occ in occurrences})
        sample = ", ".join(str(path) for path in example_paths[:3])
        if len(example_paths) > 3:
            sample += ", …"
        lines.append(f"| `{color}` | {len(occurrences)} | {sample} |")

    lines.append("")
    lines.append("## Detailed occurrences")
    lines.append("")
    for color, occurrences in sorted(report.items(), key=lambda item: item[0]):
        lines.append(f"### `{color}`")
        lines.append("")
        for occ in occurrences:
            rel_path = occ.path.relative_to(root)
            snippet = occ.line_text.replace("|", "\\|")
            lines.append(f"- `{rel_path}`:{occ.line_number}: `{snippet}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Audit color literals in a directory")
    parser.add_argument("root", type=pathlib.Path, help="Path to the directory to scan")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.exists() or not root.is_dir():
        parser.error(f"Path '{root}' is not a directory")

    report: Dict[str, List[Occurrence]] = defaultdict(list)
    for file_path in iter_source_files(root):
        for color, occurrence in find_color_literals(file_path):
            report[color].append(occurrence)

    if not report:
        print("No color literals found.")
        return 0

    markdown = render_markdown(report, root)
    sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))