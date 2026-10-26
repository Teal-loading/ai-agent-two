"""网页抓取工具（Jsoup → httpx + BeautifulSoup）。"""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool

from app.tools.schemas import ScrapeWebPageInput

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def fetch_html(url: str, timeout: float = 30.0) -> str:
    """拉取网页并返回规范化后的 HTML。"""
    response = httpx.get(
        url,
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    response.raise_for_status()
    return str(BeautifulSoup(response.text, "html.parser"))


@tool("scrapeWebPage", args_schema=ScrapeWebPageInput, description="Scrape the content of a web page")
def scrape_web_page(url: str) -> str:
    """抓取指定网页内容。"""
    try:
        return fetch_html(url)
    except Exception as exc:  # noqa: BLE001
        return f"Error scraping web page: {exc}"
