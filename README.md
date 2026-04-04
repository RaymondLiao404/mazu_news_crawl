# mazu_news_crawl

使用 FastAPI 搭配 Google News RSS 抓取新聞，並針對指定新聞網站擷取正文內容。

## 功能

- `/dajia-news`：抓取大甲媽相關新聞
- `/dui-news`：抓取酒駕相關新聞
- 依來源網站使用不同 HTML 規則抓正文
- 排除無法穩定抓取或不需要的新聞網站

## 啟動方式

```bash
uvicorn main:app --reload
```

## 測試

```bash
python test_article_service.py
```
