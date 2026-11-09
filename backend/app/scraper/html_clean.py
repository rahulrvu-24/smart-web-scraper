"""Turn raw HTML into compact text an LLM can read cheaply."""

import json
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

DROP_TAGS = ["script", "style", "noscript", "svg", "iframe", "template", "canvas", "form", "nav", "footer"]
MAX_JSON_LD_CHARS = 6_000


@dataclass
class CleanPage:
    title: str
    text: str
    json_ld: str  # schema.org data many shops embed: often the most reliable source


def _collect_json_ld(soup: BeautifulSoup) -> str:
    blocks: list[str] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text()
        try:
            blocks.append(json.dumps(json.loads(raw), ensure_ascii=False, separators=(",", ":")))
        except (json.JSONDecodeError, TypeError):
            continue
    return "\n".join(blocks)[:MAX_JSON_LD_CHARS]


def clean_html(html: str) -> CleanPage:
    soup = BeautifulSoup(html, "lxml")
    json_ld = _collect_json_ld(soup)
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    meta = soup.find("meta", attrs={"name": "description"})
    description = meta.get("content", "").strip() if meta else ""

    for tag in soup(DROP_TAGS):
        tag.decompose()
    body = soup.body or soup
    text = body.get_text("\n", strip=True)
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    if description and description not in text:
        text = f"{description}\n{text}"
    return CleanPage(title=title, text=text.strip(), json_ld=json_ld)


def visible_text_length(html: str) -> int:
    return len(clean_html(html).text)
