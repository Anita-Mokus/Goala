from pathlib import Path
from urllib.parse import urlparse
import requests
import re
import time

from src.scraper.crawler import DEFAULT_HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT


DEFAULT_OUTPUT_DIR = Path(__file__).parents[2] / "data"
FILE_PREFIX = "sapientia_"

def slug_from_url(url: str) -> str:
    path = urlparse(url).path
    slug = re.sub(r"[^a-z0-9]+", "_", path.lower()).strip("_")
    return f"{FILE_PREFIX}{slug}.pdf"

def download_pdfs(
    pdf_urls: list[str],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    session: requests.Session | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if session is None:
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
    for url in pdf_urls:
        filename = slug_from_url(url)
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        (output_dir / filename).write_bytes(response.content)
        print(f"[saved] {filename}")
        time.sleep(REQUEST_DELAY)