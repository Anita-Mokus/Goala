"""
BFS web crawler for ms.sapientia.ro — Felvételi section.
Yields (url, html) pairs for each page within the allowed scope.
"""
import time
from collections import deque
from urllib.parse import urljoin, urlparse

import requests

START_URL = "https://ms.sapientia.ro/hu/felveteli"
ALLOWED_DOMAIN = "ms.sapientia.ro"
ALLOWED_PATH_PREFIXES = ("/hu/felveteli", "/hu/tartalom")
BINARY_EXTENSIONS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".png", ".jpg", ".jpeg")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GoalaBot/1.0; +https://github.com/goala)"
    )
}
REQUEST_DELAY = 0.6
REQUEST_TIMEOUT = 15


def _is_allowed(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc != ALLOWED_DOMAIN:
        return False
    if any(parsed.path.lower().endswith(ext) for ext in BINARY_EXTENSIONS):
        return False
    return any(parsed.path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES)


def _extract_links(html: str, base_url: str) -> list[str]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        absolute = urljoin(base_url, href)
        # Strip fragment
        absolute = absolute.split("#")[0]
        if absolute:
            links.append(absolute)
    return links


def crawl(max_pages: int = 100) -> list[tuple[str, str]]:
    """
    BFS crawl starting from START_URL.
    Returns a list of (url, html) tuples for all pages within scope.
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    visited: set[str] = set()
    queue: deque[str] = deque([START_URL])
    results: list[tuple[str, str]] = []

    while queue and len(results) < max_pages:
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
        print(f"[ok] ({len(results)}/{max_pages}) {url}")

        for link in _extract_links(html, url):
            if link not in visited and _is_allowed(link):
                queue.append(link)

        time.sleep(REQUEST_DELAY)

    return results
