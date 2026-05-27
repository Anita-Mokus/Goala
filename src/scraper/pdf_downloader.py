from pathlib import Path
from urllib.parse import urlparse
import requests
import re
import time

from src.scraper.crawler import DEFAULT_HEADERS, REQUEST_DELAY, REQUEST_TIMEOUT, START_URL


DEFAULT_OUTPUT_DIR = Path(__file__).parents[2] / "shared" / "sapientia"
FILE_PREFIX = "sapientia_"

def slug_from_url(url: str) -> str:
    path = urlparse(url).path
    slug = re.sub(r"[^a-z0-9]+", "_", path.lower()).strip("_")
    return f"{FILE_PREFIX}{slug}.pdf"

def download_pdfs(
    pdf_urls: list[str] | list[tuple[str, str]],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    session: requests.Session | None = None,
    max_pdfs: int | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if max_pdfs is not None:
        max_pdfs = max(0, max_pdfs)
        pdf_urls = pdf_urls[:max_pdfs]
    if session is None:
        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)
    session.headers.setdefault(
        "Accept",
        "application/pdf,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8",
    )
    failed_dir = output_dir / "_pdf_failed"
    for item in pdf_urls:
        if isinstance(item, tuple):
            url, referrer = item
        else:
            url, referrer = item, START_URL

        safe_url = requests.utils.requote_uri(url)
        filename = slug_from_url(url)
        try:
            response = session.get(
                safe_url,
                timeout=REQUEST_TIMEOUT,
                headers={"Referer": referrer} if referrer else None,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[skip] {url} — {exc}")
            time.sleep(REQUEST_DELAY)
            continue

        content_type = response.headers.get("content-type", "").lower()
        content = response.content
        is_pdf = "pdf" in content_type or content.startswith(b"%PDF")

        if not is_pdf and referrer and referrer != START_URL:
            try:
                response = session.get(
                    safe_url,
                    timeout=REQUEST_TIMEOUT,
                    headers={"Referer": START_URL},
                )
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                content = response.content
                is_pdf = "pdf" in content_type or content.startswith(b"%PDF")
            except requests.RequestException:
                pass

        if not is_pdf:
            failed_dir.mkdir(parents=True, exist_ok=True)
            error_path = failed_dir / Path(filename).with_suffix(
                ".html" if "html" in content_type else ".bin"
            ).name
            error_path.write_bytes(content)
            print(
                f"[skip] {filename} — non-PDF content-type={content_type or 'unknown'} saved to {error_path.name}"
            )
            time.sleep(REQUEST_DELAY)
            continue

        (output_dir / filename).write_bytes(content)
        print(f"[saved] {filename}")
        time.sleep(REQUEST_DELAY)