from bs4 import BeautifulSoup

REMOVE_TAGS = ["script", "style", "noscript"]
FALLBACK_REMOVE_IDS = ["navig", "pagetitle", "nleft", "bottom", "menu", "top_m", "menu_m"]

def extract_page(html: str, url: str = "") -> str:
    soup = BeautifulSoup(html, "lxml")  # lxml parser — faster and more lenient

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    for tag in REMOVE_TAGS:
        for el in soup.find_all(tag):
            el.decompose()

    content = soup.find(id="pageheader")

    left_szk = soup.find(id="left_szk")
    left_szk_lines: list[str] = []
    if left_szk:
        for block in left_szk.find_all(class_="szakrinfo"):
            left_szk_lines.append(block.get_text(separator="\n", strip=True).splitlines())
            left_szk_lines.append("")

    if not content:
        for div_id in FALLBACK_REMOVE_IDS:
            el = soup.find(id=div_id)
            if el:
                el.decompose()
        content = soup.body or soup

    raw_lines = content.get_text(separator="\n", strip=True).splitlines()
    lines, prev = [], None
    for line in raw_lines:
        line = line.strip()
        if line and line != prev:
            lines.append(line)
            prev = line

    header = []
    if url:
        header.append(f"Forrás: {url}")
    if title:
        header.append(f"Cím: {title}")
    if header:
        header.append("")

    sidebar = left_szk_lines + [""] if left_szk_lines else []
    return "\n".join(header + sidebar + lines)