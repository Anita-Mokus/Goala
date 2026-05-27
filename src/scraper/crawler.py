"""
BFS web crawler for ms.sapientia.ro.
Yields (url, html) pairs for each page within the allowed scope.
"""
import time
from collections import deque
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

import requests

START_URL = "https://ms.sapientia.ro/hu/felveteli"
ALLOWED_DOMAIN = "ms.sapientia.ro"
ALLOWED_PATH_PREFIXES: tuple[str, ...] = (
    "/hu/felveteli",
    "/hu/tartalom",
    "/hu/hallgatoknak/bentlakas_",
)
BINARY_EXTENSIONS = (".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".png", ".jpg", ".jpeg")
ASSET_PATH_MARKERS = ("/content/docs/", "/data/dokumentumok/", "/data/")
BLOCKED_PATH_TOKENS = ("galeria", "munkatarsak", "tanszeke")

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
    path_lower = parsed.path.lower()
    if any(token in path_lower for token in BLOCKED_PATH_TOKENS):
        return False
    if any(path_lower.endswith(ext) for ext in BINARY_EXTENSIONS):
        return False
    if not ALLOWED_PATH_PREFIXES:
        return True
    return any(parsed.path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES)


def _extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        absolute = urljoin(base_url, href)
        absolute = absolute.split("#")[0]
        absolute = _normalize_asset_url(absolute)
        if absolute:
            links.append(absolute)
    return links


def _normalize_asset_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc != ALLOWED_DOMAIN:
        return url

    for marker in ASSET_PATH_MARKERS:
        index = parsed.path.find(marker)
        if index > 0:
            normalized = parsed._replace(path=parsed.path[index:])
            return normalized.geturl()

    return url


def crawl(
    max_pages: int | None = None,
    max_pdfs: int | None = None,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], requests.Session]:
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
    pdf_links: dict[str, str] = {}

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
            print(f"  [skip] {url} — {e}")
            continue

        results.append((url, html))
        print(f"  [ok] ({len(results)}) {url}")

        reached_page_limit = max_pages is not None and len(results) >= max_pages
        for link in _extract_links(html, url):
            if _is_pdf(link):
                if max_pdfs is None or len(pdf_links) < max_pdfs:
                    pdf_links.setdefault(link, url)
            elif not reached_page_limit and link not in visited and _is_allowed(link):
                queue.append(link)

        time.sleep(REQUEST_DELAY)

        if reached_page_limit:
            break

    return results, list(pdf_links.items()), session
