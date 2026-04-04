import json
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - optional dependency
    sync_playwright = None


class ArticleService:
    REQUEST_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
    }

    # 抓正文前先移除常見雜訊節點，降低廣告與推薦區誤抓機率
    DEFAULT_REMOVE_SELECTORS = [
        "script",
        "style",
        "noscript",
        "aside",
        "nav",
        "footer",
        "figure",
        "figcaption",
        ".ad",
        ".ads",
        ".advertisement",
        ".article-ad",
        ".related",
        ".related-news",
        ".keyword",
        ".keywords",
        ".share",
        ".social",
        ".recommend",
        '[class*="ad-"]',
        '[class*="recommend"]',
        '[class*="related"]',
    ]

    def __init__(self) -> None:
        # 重用 HTTP 連線可減少反覆握手成本，對大量文章抓取比較有感
        self.session = requests.Session()
        self.session.headers.update(self.REQUEST_HEADERS)

    # 將 Google News 跳轉連結解析成實際新聞網址
    def decode_google_news_url(self, google_url: str) -> str:
        try:
            response = self.session.get(google_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            data = soup.select_one("c-wiz[data-p]")
            if data is None:
                return google_url

            data_p = data.get("data-p")
            if not data_p:
                return google_url

            obj = json.loads(data_p.replace("%.@.", '["garturlreq",', 1))
            payload = {
                "f.req": json.dumps([[["Fbv4je", json.dumps(obj[:-6] + obj[-2:]), "null", "generic"]]])
            }
            decode_response = self.session.post(
                "https://news.google.com/_/DotsSplashUi/data/batchexecute?rpcids=Fbv4je",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    **self.REQUEST_HEADERS,
                },
                data=payload,
                timeout=10,
            )
            decode_response.raise_for_status()
            decoded = json.loads(decode_response.text.replace(")]}'", ""))[0][2]
            return json.loads(decoded)[1]
        except (requests.RequestException, json.JSONDecodeError, IndexError, TypeError, KeyError):
            return google_url

    # 先用 requests 抓正文頁，若遇到反爬再退回 Playwright
    def fetch_article_content(self, url: str, fallback_text: str = "") -> str:
        final_url = url
        html = ""

        try:
            response = self.session.get(
                url,
                headers={**self.REQUEST_HEADERS, "Referer": "https://news.google.com/"},
                timeout=15,
                allow_redirects=True,
            )
        except requests.RequestException:
            response = None

        if response is not None:
            final_url = response.url
            html = self._decode_response_text(response)

            if response.status_code >= 400 or self._looks_blocked(html):
                browser_html = self._fetch_html_via_playwright(url)
                if browser_html:
                    html = browser_html
                    final_url = url
        else:
            html = self._fetch_html_via_playwright(url)

        if not html or self._looks_blocked(html):
            return fallback_text

        soup = BeautifulSoup(html, "html.parser")
        domain = urlparse(final_url).netloc.lower() or urlparse(url).netloc.lower()

        extractor = self._get_extractor(domain)
        lines = extractor(soup)
        if not lines:
            lines = self._extract_generic(soup)

        content = self._join_lines(lines)
        return content or fallback_text

    def _decode_response_text(self, response: requests.Response) -> str:
        domain = urlparse(response.url).netloc.lower()

        if "yahoo.com" in domain:
            text = response.content.decode("utf-8", errors="replace")
        else:
            if response.apparent_encoding:
                response.encoding = response.apparent_encoding
            text = response.text

        return self._fix_mojibake(text)

    # 被反爬擋住時，用真瀏覽器渲染頁面再取 HTML
    def _fetch_html_via_playwright(self, url: str) -> str:
        if sync_playwright is None:
            return ""

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self.REQUEST_HEADERS["User-Agent"],
                    locale="zh-TW",
                )
                page = context.new_page()
                page.set_extra_http_headers({"Referer": "https://news.google.com/"})
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)
                html = page.content()
                context.close()
                browser.close()
                return html
        except Exception:
            return ""

    # 判斷目前拿到的是不是反爬或挑戰頁
    def _looks_blocked(self, html: str) -> bool:
        blocked_markers = [
            "Just a moment...",
            "Enable JavaScript and cookies to continue",
            "Checking your browser before accessing",
            "Cloudflare WAF",
            "連線錯誤頁面",
        ]
        return any(marker in html for marker in blocked_markers)

    # 依站台網域分派對應的正文抽取器
    def _get_extractor(self, domain: str):
        extractors = {
            "www.cna.com.tw": self._extract_cna,
            "news.ltn.com.tw": self._extract_ltn,
            "ent.ltn.com.tw": self._extract_ltn,
            "www.setn.com": self._extract_setn,
            "udn.com": self._extract_udn,
            "tw.news.yahoo.com": self._extract_yahoo,
            "sunmedia.tw": self._extract_sunmedia,
            "www.ctee.com.tw": self._extract_ctee,
            "ctee.com.tw": self._extract_ctee,
            "www.ftvnews.com.tw": self._extract_ftv,
        }
        return extractors.get(domain, self._extract_generic)

    def _extract_cna(self, soup: BeautifulSoup) -> list[str]:
        return self._extract_from_container(
            soup,
            container_selectors=["article", ".news_content"],
            paragraph_selectors=["p"],
            stop_keywords=["選擇與事實站在一起", "下載中央社", "本網站之文字"],
        )

    def _extract_ltn(self, soup: BeautifulSoup) -> list[str]:
        return self._extract_from_container(
            soup,
            container_selectors=[".text"],
            paragraph_selectors=["p"],
            skip_keywords=["請繼續往下閱讀"],
            stop_keywords=["自由時報版權所有", "熱門推播", "不用抽"],
        )

    def _extract_setn(self, soup: BeautifulSoup) -> list[str]:
        return self._extract_from_container(
            soup,
            container_selectors=["#Content1", ".page-text article"],
            paragraph_selectors=["p"],
            stop_keywords=["延伸閱讀", "更多新聞", "相關新聞"],
        )

    def _extract_udn(self, soup: BeautifulSoup) -> list[str]:
        return self._extract_from_container(
            soup,
            container_selectors=[".article-content__editor"],
            paragraph_selectors=["p"],
        )

    def _extract_chinatimes(self, soup: BeautifulSoup) -> list[str]:
        return self._extract_from_container(
            soup,
            container_selectors=[".article-body", "article"],
            paragraph_selectors=["p"],
            stop_keywords=["時報資訊", "延伸閱讀", "版權所有"],
        )

    def _extract_yahoo(self, soup: BeautifulSoup) -> list[str]:
        return self._extract_from_container(
            soup,
            container_selectors=["article .atoms", "article"],
            paragraph_selectors=["p"],
            remove_selectors=self.DEFAULT_REMOVE_SELECTORS
            + ["header", "section", "[data-testid]", "[data-test-locator]"],
            skip_keywords=["加入為 Google 偏好來源", "將 Yahoo 設為首選來源"],
            stop_keywords=["更多報導", "相關報導", "延伸閱讀", "原始連結", "閱讀原文", "訂閱!!"],
        )

    def _extract_sunmedia(self, soup: BeautifulSoup) -> list[str]:
        return self._extract_from_container(
            soup,
            container_selectors=[".entry-content", "article"],
            paragraph_selectors=["p"],
            stop_keywords=["閱讀原文", "更多報導", "相關新聞"],
        )

    def _extract_ctee(self, soup: BeautifulSoup) -> list[str]:
        json_ld_lines = self._extract_json_ld_article_body(soup)
        if json_ld_lines:
            return json_ld_lines

        return self._extract_from_container(
            soup,
            container_selectors=[
                ".content__body .article-wrap article",
                ".article-wrap article",
                "main article",
                "article",
            ],
            paragraph_selectors=["p"],
            skip_keywords=["相關新聞", "編輯精選", "您可能感興趣的話題"],
            stop_keywords=["更多報導", "延伸閱讀", "版權所有", "相關新聞", "編輯精選"],
        )

    def _extract_ftv(self, soup: BeautifulSoup) -> list[str]:
        return self._extract_from_container(
            soup,
            container_selectors=[
                "#contentarea",
                "#newscontent",
                ".article-body",
                "article[itemprop='articleBody']",
            ],
            paragraph_selectors=["p"],
            remove_selectors=self.DEFAULT_REMOVE_SELECTORS
            + [
                ".exread-list",
                ".news-tag",
                ".share-box",
                ".news-status",
                ".article-cover",
                ".article-function",
            ],
            skip_keywords=["更多新聞：", "延伸閱讀", "熱門新聞"],
            stop_keywords=["延伸閱讀", "熱門新聞", "相關新聞", "版權所有"],
        )

    def _extract_generic(self, soup: BeautifulSoup) -> list[str]:
        return self._extract_from_container(
            soup,
            container_selectors=["article", "main", "body"],
            paragraph_selectors=["p"],
            stop_keywords=["更多報導", "延伸閱讀", "版權所有", "All Rights Reserved"],
        )

    # 先鎖定正文容器，移除雜訊後再取段落
    def _extract_from_container(
        self,
        soup: BeautifulSoup,
        container_selectors: list[str],
        paragraph_selectors: list[str],
        remove_selectors: list[str] | None = None,
        skip_keywords: list[str] | None = None,
        stop_keywords: list[str] | None = None,
    ) -> list[str]:
        remove_selectors = remove_selectors or self.DEFAULT_REMOVE_SELECTORS
        skip_keywords = skip_keywords or []
        stop_keywords = stop_keywords or []

        for selector in container_selectors:
            container = soup.select_one(selector)
            if container is None:
                continue

            container_soup = BeautifulSoup(str(container), "html.parser")
            container_root = container_soup.select_one(selector) or container_soup

            for remove_selector in remove_selectors:
                for node in container_root.select(remove_selector):
                    node.decompose()

            lines: list[str] = []
            for paragraph_selector in paragraph_selectors:
                lines.extend(
                    element.get_text(" ", strip=True)
                    for element in container_root.select(paragraph_selector)
                    if element.get_text(" ", strip=True)
                )

            lines = self._clean_lines(lines, skip_keywords, stop_keywords)
            if lines:
                return lines

        return []

    # 工商時報這類站台常把正文放在 JSON-LD 裡，優先使用會最乾淨
    def _extract_json_ld_article_body(self, soup: BeautifulSoup) -> list[str]:
        for script in soup.select('script[type="application/ld+json"]'):
            raw_content = script.string or script.get_text(strip=True)
            if not raw_content:
                continue

            try:
                data = json.loads(raw_content)
            except json.JSONDecodeError:
                continue

            article_body = self._find_article_body_in_json_ld(data)
            if not article_body:
                continue

            normalized_body = re.sub(r"\s+", " ", article_body).strip()
            if normalized_body:
                return [normalized_body]

        return []

    # 遞迴搜尋 JSON-LD 裡的 NewsArticle 節點
    def _find_article_body_in_json_ld(self, data) -> str:
        if isinstance(data, dict):
            node_type = data.get("@type")
            if self._is_news_article_type(node_type) and isinstance(data.get("articleBody"), str):
                return data["articleBody"]

            for value in data.values():
                article_body = self._find_article_body_in_json_ld(value)
                if article_body:
                    return article_body

        if isinstance(data, list):
            for item in data:
                article_body = self._find_article_body_in_json_ld(item)
                if article_body:
                    return article_body

        return ""

    def _is_news_article_type(self, node_type) -> bool:
        if isinstance(node_type, str):
            return node_type in {"NewsArticle", "Article"}

        if isinstance(node_type, list):
            return any(item in {"NewsArticle", "Article"} for item in node_type if isinstance(item, str))

        return False

    # 統一清理段落內容，去掉重複與尾端提示文字
    def _clean_lines(self, lines: list[str], skip_keywords: list[str], stop_keywords: list[str]) -> list[str]:
        result: list[str] = []
        seen = set()

        for raw_line in lines:
            line = re.sub(r"\s+", " ", raw_line).strip()
            if not line or len(line) <= 1:
                continue

            if any(keyword in line for keyword in skip_keywords):
                continue

            if any(keyword in line for keyword in stop_keywords):
                break

            if line in seen:
                continue

            seen.add(line)
            result.append(line)

        return result

    def _join_lines(self, lines: list[str]) -> str:
        return "\n".join(lines)

    def _fix_mojibake(self, text: str) -> str:
        mojibake_markers = ("å", "ä", "é", "è", "ï", "ç", "æ")
        if not text or not any(marker in text for marker in mojibake_markers):
            return text

        try:
            repaired = text.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text

        if repaired.count("\ufffd") > text.count("\ufffd"):
            return text

        return repaired
