"""
Orchestrates crawling and extraction, saves results as .txt files into data/.
"""
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from src.scraper.crawler import crawl
from src.scraper.extractor import extract_page

DEFAULT_OUTPUT_DIR = Path(__file__).parents[2] / "data"
FILE_PREFIX = "sapientia_"


def _url_to_filename(url: str) -> str:
    path = urlparse(url).path
    slug = re.sub(r"[^a-z0-9]+", "_", path.lower()).strip("_")
    return f"{FILE_PREFIX}{slug}.txt"


def run(output_dir: Path = DEFAULT_OUTPUT_DIR, max_pages: int = 100) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {output_dir}")
    print(f"Max pages: {max_pages}\n")

    pages = crawl(max_pages=max_pages)

    print(f"\nSaving {len(pages)} pages...")
    saved = 0
    skipped = 0

    for url, html in pages:
        text = extract_page(html, url=url)

        if not text.strip():
            print(f"[empty] {url}")
            skipped += 1
            continue

        filename = _url_to_filename(url)
        filepath = output_dir / filename

        filepath.write_text(text, encoding="utf-8")
        print(f"[saved] {filename}")
        saved += 1

    print(f"\nDone. Saved: {saved}, Skipped (empty): {skipped}")
