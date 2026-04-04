import asyncio
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlparse

from bs4 import BeautifulSoup
import feedparser

from config.settings import settings
from services.article_service import ArticleService


class NewsService:
    # 提供新聞查詢服務，使用 Google News RSS 作為來源
    def __init__(self) -> None:
        self.article_service = ArticleService()

    # 取得大甲媽新聞
    async def get_dajia_news(self, hours: int) -> dict:
        return await self._get_news(
            topic="dajia",
            terms=settings.dajia_terms,
            hours=hours,
        )

    # 先用搜尋詞抓 Google News RSS，再用同一組詞做二次篩選
    async def _get_news(self, topic: str, terms: list[str], hours: int) -> dict:
        limit = datetime.now(timezone.utc) - timedelta(hours=hours)
        seen_titles: set[str] = set()
        candidates: list[dict] = []

        feeds = await self._fetch_feeds(terms)

        for term, feed in zip(terms, feeds):
            if feed is None:
                continue

            for entry in feed.entries:
                if not getattr(entry, "published_parsed", None):
                    continue

                published_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                if published_time < limit:
                    continue

                title = entry.title.strip()
                if title in seen_titles:
                    continue

                fallback_text = self._extract_summary_text(entry)

                # 先用標題與摘要做二次篩選，避免無關新聞混入
                if not self._matches_terms(title=title, summary=fallback_text, terms=terms):
                    continue

                source_domain = self._get_entry_source_domain(entry)
                if source_domain and source_domain in settings.excluded_domains:
                    continue

                seen_titles.add(title)
                candidates.append(
                    {
                        "title": title,
                        "link": entry.link,
                        "published_at": published_time.astimezone().isoformat(),
                        "fallback_text": fallback_text,
                    }
                )

        items = await self._resolve_candidates(candidates)
        items.sort(key=lambda item: item["published_at"], reverse=True)
        return {"topic": topic, "hours": hours, "count": len(items), "items": items}

    # RSS 來源先並行抓，避免多組關鍵字逐一等待
    async def _fetch_feeds(self, terms: list[str]) -> list:
        tasks = [
            asyncio.to_thread(feedparser.parse, self._build_rss_url(term))
            for term in terms
        ]
        return await asyncio.gather(*tasks, return_exceptions=False)

    # 將候選文章並行處理，避免單篇延遲拖慢整體
    async def _resolve_candidates(self, candidates: list[dict]) -> list[dict]:
        semaphore = asyncio.Semaphore(settings.fetch_concurrency)
        tasks = [
            self._resolve_candidate(candidate=candidate, semaphore=semaphore)
            for candidate in candidates
        ]
        results = await asyncio.gather(*tasks)
        return [item for item in results if item is not None]

    # 單篇文章解析流程：解 Google 連結、排除站台、抓正文
    async def _resolve_candidate(self, candidate: dict, semaphore: asyncio.Semaphore) -> dict | None:
        async with semaphore:
            source_url = await asyncio.to_thread(
                self.article_service.decode_google_news_url,
                candidate["link"],
            )
            source_domain = urlparse(source_url).netloc.lower()
            if source_domain in settings.excluded_domains:
                return None
            if "/shortvideo/" in source_url:
                return None

            content = await asyncio.to_thread(
                self.article_service.fetch_article_content,
                source_url,
                candidate["fallback_text"],
            )
            return {
                "title": candidate["title"],
                "link": candidate["link"],
                "source_url": source_url,
                "published_at": candidate["published_at"],
                "content": content,
            }

    # 從 RSS entry 取來源網域（若能取得，先用它做排除）
    def _get_entry_source_domain(self, entry) -> str:
        source = getattr(entry, "source", None) or entry.get("source")
        if isinstance(source, dict):
            href = source.get("href") or source.get("url") or ""
        else:
            href = getattr(source, "href", "") or getattr(source, "url", "")
        return urlparse(href).netloc.lower() if href else ""

    # 建立 Google News RSS 查詢網址
    def _build_rss_url(self, query: str) -> str:
        encoded_query = quote(query)
        return (
            f"https://news.google.com/rss/search?q={encoded_query}"
            "&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        )

    # 從 RSS 摘要欄位取出純文字，作為二次篩選與備援內文
    def _extract_summary_text(self, entry) -> str:
        candidates: list[str] = []

        summary_html = getattr(entry, "summary", "")
        if summary_html:
            candidates.append(summary_html)

        summary_detail = getattr(entry, "summary_detail", None)
        if summary_detail:
            summary_value = getattr(summary_detail, "value", "")
            if summary_value:
                candidates.append(summary_value)

        description_html = getattr(entry, "description", "")
        if description_html:
            candidates.append(description_html)

        content_list = entry.get("content") or []
        for item in content_list:
            if isinstance(item, dict):
                value = item.get("value", "")
            else:
                value = getattr(item, "value", "")
            if value:
                candidates.append(value)

        best_text = ""
        for html in candidates:
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(" ", strip=True)
            if len(text) > len(best_text):
                best_text = text

        if best_text:
            return best_text

        title = getattr(entry, "title", "")
        return title.strip() if title else ""

    # 使用同一組搜尋詞驗證標題或摘要，避免混入無關新聞
    def _matches_terms(self, title: str, summary: str, terms: list[str]) -> bool:
        target = f"{title}\n{summary}"
        return any(term in target for term in terms)
