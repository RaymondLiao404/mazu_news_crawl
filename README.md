# mazu_news_crawl

使用 FastAPI 搭配 Google News RSS 抓取媽祖相關新聞，並針對指定新聞網站擷取正文內容。

## 功能

- 提供大甲媽新聞 API：`/dajia_MAZU_news`
- 提供白沙屯媽祖新聞 API：`/baishatun_MAZU_news`
- 提供 YouTube 直播 / 影片截圖 API：`/yt_live_snapshot`
- 支援 `hours` 參數控制查詢區間
- 依來源網站套用不同正文擷取規則
- 排除不需要或不穩定的新聞來源

## API

- 首頁：`/`
- 大甲媽新聞：`/dajia_MAZU_news?hours=12`
- 白沙屯媽祖新聞：`/baishatun_MAZU_news?hours=12`
- YouTube 截圖：`/yt_live_snapshot?url=<youtube_url>`

說明：

- `hours` 預設為 `12`
- `hours` 最大值為 `48`

## 啟動方式

安裝套件：

```bash
pip install -r requirements.txt
```

啟動服務：

```bash
uvicorn main:app --reload
```

本機測試後可直接開：

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/dajia_MAZU_news?hours=12
http://127.0.0.1:8000/baishatun_MAZU_news?hours=12
http://127.0.0.1:8000/yt_live_snapshot?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

## 備註

- 部分網站可能有反爬機制，因此會依情況退回摘要內容
- 回應會明確使用 UTF-8 JSON，避免手機或 LINE 內建瀏覽器出現亂碼
