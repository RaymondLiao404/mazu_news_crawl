import re

import requests
from bs4 import BeautifulSoup

from services.article_service import ArticleService


TEST_URLS = [
    "https://www.ctee.com.tw/news/20260403700763-431207",
    "https://www.ftvnews.com.tw/news/detail/2026403C07M1",
]


def preview_text(text: str, length: int = 300) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    return normalized[:length]


def debug_fetch(url: str) -> None:
    service = ArticleService()

    print("=" * 80)
    print(f"URL: {url}")

    try:
        response = requests.get(
            url,
            headers={**service.REQUEST_HEADERS, "Referer": "https://news.google.com/"},
            timeout=15,
            allow_redirects=True,
        )
        print(f"status_code: {response.status_code}")
        print(f"final_url: {response.url}")
        print(f"content_type: {response.headers.get('Content-Type', '')}")
    except requests.RequestException as exc:
        print(f"request_error: {exc}")
        print()
        return

    if response.apparent_encoding:
        response.encoding = response.apparent_encoding

    html_preview = preview_text(response.text, 500)
    print(f"html_preview: {html_preview}")

    cloudflare_markers = [
        "Just a moment...",
        "Enable JavaScript and cookies to continue",
        "Checking your browser before accessing",
    ]
    blocked = any(marker in response.text for marker in cloudflare_markers)
    print(f"blocked_like_cloudflare: {blocked}")

    soup = BeautifulSoup(response.text, "html.parser")
    domain = requests.utils.urlparse(response.url).netloc.lower()
    extractor = service._get_extractor(domain)
    print(f"extractor: {extractor.__name__}")

    lines = extractor(soup)
    content = service._join_lines(lines)
    print(f"extracted_length: {len(content)}")
    print(f"extracted_preview: {preview_text(content, 500)}")

    fallback = "這是 fallback 測試文字"
    final_content = service.fetch_article_content(url, fallback_text=fallback)
    used_fallback = final_content == fallback
    print(f"fetch_article_content_used_fallback: {used_fallback}")
    print(f"fetch_article_content_preview: {preview_text(final_content, 500)}")
    print()


if __name__ == "__main__":
    for test_url in TEST_URLS:
        debug_fetch(test_url)
