"""
BFS web crawler for ms.sapientia.ro — Felvételi section.
Yields (url, html) pairs for each page within the allowed scope.
"""
import time
from collections import deque
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

import requests

START_URL = "https://ms.sapientia.ro/hu/felveteli"
ALLOWED_DOMAIN = "ms.sapientia.ro"
ALLOWED_PATH_PREFIXES = ("/hu/felveteli", "/hu/tartalom")
BINARY_EXTENSIONS = (".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".png", ".jpg", ".jpeg")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GoalaBot/1.0; +https://github.com/goala)"
    )
}
REQUEST_DELAY = 0.6
REQUEST_TIMEOUT = 15


def _is_pdf(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")


def _is_allowed(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc != ALLOWED_DOMAIN:
        return False
    if any(parsed.path.lower().endswith(ext) for ext in BINARY_EXTENSIONS):
        return False
    return any(parsed.path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES)


def _extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        absolute = urljoin(base_url, href)
        absolute = absolute.split("#")[0]
        if absolute:
            links.append(absolute)
    return links


def crawl() -> tuple[list[tuple[str, str]], list[str], requests.Session]:
    """
    BFS crawl starting from START_URL.
    Returns (html_pages, pdf_urls, session) — the session is passed to the
    PDF downloader so it reuses the same cookies established during crawling.
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    visited: set[str] = set()
    queue: deque[str] = deque([START_URL])
    results: list[tuple[str, str]] = []
    pdf_urls: set[str] = set()

    while queue:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        if not _is_allowed(url):
            continue

        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            html = response.text
        except requests.RequestException as e:
            print(f"[skip] {url} — {e}")
            continue

        results.append((url, html))
        print(f"[ok] ({len(results)}) {url}")

        for link in _extract_links(html, url):
            if _is_pdf(link):
                pdf_urls.add(link)
            elif link not in visited and _is_allowed(link):
                queue.append(link)

        time.sleep(REQUEST_DELAY)

    return results, list(pdf_urls), session
