"""Try the whole pipeline on one URL from the terminal, without the API or database.

    python -m app.extraction.cli https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html title:string price:number in_stock:boolean

Each field is name:type, where type is string, number, integer, boolean or string_list.
Needs GROQ_API_KEY in backend/.env.
"""

import asyncio
import json
import sys

from app.core.config import get_settings
from app.extraction.fields import FieldSet
from app.extraction.llm import extract
from app.scraper.fetcher import fetch_page
from app.scraper.html_clean import clean_html


async def main(url: str, specs: list[str]) -> None:
    settings = get_settings()
    fields = FieldSet(
        fields={name: {"type": kind or "string"} for name, _, kind in (s.partition(":") for s in specs)}
    ).fields
    page = await fetch_page(url, settings)
    clean = clean_html(page.html)
    print(f"Fetched {page.url} via {page.method}: {len(clean.text)} chars of text, title {clean.title!r}")
    result = await extract(fields, clean, page.url, settings)
    print(f"Model {result.model} | valid={result.is_valid} | {result.input_tokens}+{result.output_tokens} tokens | {result.latency_ms} ms")
    if result.errors:
        print("Validation errors:", *result.errors, sep="\n  ")
    print(json.dumps(result.data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2:]))
