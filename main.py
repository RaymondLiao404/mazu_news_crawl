import asyncio
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

from config.settings import settings
from services.baishatun_location_service import BaishatunLocationService
from services.dajia_location_service import DajiaLocationService
from services.news_service import NewsService
from services.yt_snapshot_service import YtSnapshotService


app = FastAPI(title="News API", version="1.0.0")
news_service = NewsService()
baishatun_location_service = BaishatunLocationService()
dajia_location_service = DajiaLocationService()
yt_snapshot_service = YtSnapshotService()


@app.get("/")
def read_root() -> Response:
    return _json_utf8_response(
        {
            "message": "News API is running",
            "routes": [
                "/",
                f"/dajia_MAZU_news?hours={settings.default_hours}",
                f"/baishatun_MAZU_news?hours={settings.default_hours}",
                "/yt_live_snapshot?url=<youtube_url>",
            ],
        }
    )


@app.get("/dajia_MAZU_news")
async def read_dajia_news(
    hours: int = Query(
        default=settings.default_hours,
        ge=0,
        le=settings.max_hours,
    )
) -> Response:
    payload = await news_service.get_dajia_news(hours=hours)
    location_fields = dajia_location_service.fetch_location_fields()

    response_payload = {
        "topic": payload["topic"],
        "hours": payload["hours"],
        "count": payload["count"],
        **location_fields,
        "items": payload["items"],
    }
    return _json_utf8_response(response_payload)


@app.get("/baishatun_MAZU_news")
async def read_baishatun_news(
    hours: int = Query(
        default=settings.default_hours,
        ge=0,
        le=settings.max_hours,
    )
) -> Response:
    # 這支路由會在新聞資料中插入白沙屯第三方位置欄位。
    payload = await news_service.get_baishatun_news(hours=hours)
    location_fields = await asyncio.to_thread(
        baishatun_location_service.fetch_location_fields
    )

    response_payload = {
        "topic": payload["topic"],
        "hours": payload["hours"],
        "count": payload["count"],
        **location_fields,
        "items": payload["items"],
    }
    return _json_utf8_response(response_payload)


@app.get("/yt_live_snapshot")
def get_yt_live_snapshot(
    url: str = Query(..., description="YouTube 影片網址"),
) -> Response:
    try:
        image_bytes = yt_snapshot_service.capture_snapshot_bytes(url)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=image_bytes, media_type="image/jpeg")


def _json_utf8_response(payload: dict) -> Response:
    return Response(
        content=json.dumps(payload, ensure_ascii=False),
        media_type="application/json; charset=utf-8",
    )
