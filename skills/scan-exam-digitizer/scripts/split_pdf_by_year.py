#!/usr/bin/env python3
"""Split a scanned PDF into year-specific PDFs using reviewed page assignments."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from pypdf import PdfReader, PdfWriter


SAFE_LABEL = re.compile(r"[^\w.-]+", re.UNICODE)


def parse_pages(expression: str, page_count: int) -> list[int]:
    pages: list[int] = []
    for part in expression.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start, end = int(start_text), int(end_text)
            if start > end:
                raise ValueError(f"Invalid descending range: {token}")
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(token))
    if not pages:
        raise ValueError("A paper assignment must contain at least one page")
    if min(pages) < 1 or max(pages) > page_count:
        raise ValueError(f"Page assignment must stay within 1-{page_count}")
    if len(pages) != len(set(pages)):
        raise ValueError("A paper assignment contains a duplicate page")
    return pages


def parse_assignment(value: str, page_count: int) -> tuple[str, list[int]]:
    if "=" not in value:
        raise ValueError("Use LABEL=PAGES, for example 2024=1-4,6")
    label, expression = value.split("=", 1)
    label = label.strip()
    if not label:
        raise ValueError("Paper label must not be blank")
    return label, parse_pages(expression, page_count)


def safe_filename(label: str) -> str:
    value = SAFE_LABEL.sub("_", label).strip("._")
    if not value:
        raise ValueError(f"Paper label cannot form a safe filename: {label!r}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split a PDF after the agent has identified each year's source pages."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--paper",
        action="append",
        required=True,
        metavar="LABEL=PAGES",
        help="Repeat for each paper, for example --paper 2024=1-4 --paper 2023=5-8",
    )
    args = parser.parse_args()

    reader = PdfReader(args.source)
    assignments: list[tuple[str, list[int]]] = []
    used_pages: set[int] = set()
    try:
        for raw in args.paper:
            label, pages = parse_assignment(raw, len(reader.pages))
            overlap = used_pages.intersection(pages)
            if overlap:
                raise ValueError(f"Pages assigned more than once: {sorted(overlap)}")
            used_pages.update(pages)
            assignments.append((label, pages))
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for label, pages in assignments:
        writer = PdfWriter()
        for page_number in pages:
            writer.add_page(reader.pages[page_number - 1])
        output = args.output_dir / f"{safe_filename(label)}.pdf"
        with output.open("wb") as handle:
            writer.write(handle)
        print(f"{label}: pages {','.join(map(str, pages))} -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

