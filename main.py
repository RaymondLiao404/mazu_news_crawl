import asyncio
import json
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

from config.settings import settings
from services.baishatun_location_service import BaishatunLocationService
from services.dajia_location_service import DajiaLocationService
from services.news_service import NewsService
from services.yt_snapshot_service import YtSnapshotService
from utils.baishatun_location_response import (
    build_dajia_mazu_location_text,
    build_baishatun_mazu_location_text,
    create_location_text_response,
)


app = FastAPI(title="News API", version="1.0.0")
news_service = NewsService()
baishatun_location_service = BaishatunLocationService()
dajia_location_service = DajiaLocationService()
yt_snapshot_service = YtSnapshotService()
taiwan_timezone = timezone(timedelta(hours=8))


@app.get("/")
def read_root() -> Response:
    return _create_json_response(
        {
            "message": "News API is running",
            "routes": [
                "/",
                f"/dajia_MAZU_news?hours={settings.default_hours}",
                "/dajia_MAZU_location",
                f"/baishatun_MAZU_news?hours={settings.default_hours}",
                "/baishatun_MAZU_location",
                "/yt_live_snapshot?url=<youtube_url>",
            ],
        }
    )


@app.get("/favicon.ico")
def favicon() -> Response:
    return Response(status_code=204)


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
    now = datetime.now(taiwan_timezone)

    response_payload = {
        "topic": payload["topic"],
        "hours": payload["hours"],
        "count": payload["count"],
        "system_time": f"UTC+8 {now.strftime('%Y-%m-%d %H:%M:%S')}",
        **location_fields,
        "items": payload["items"],
    }
    return _create_json_response(response_payload)


@app.get("/dajia_MAZU_location")
def read_dajia_location(payload: str | None = None) -> Response:
    location_fields = dajia_location_service.fetch_location_fields()
    if payload is not None:
        return _create_json_response(location_fields)

    location_text = build_dajia_mazu_location_text(location_fields)
    return create_location_text_response(location_text)


@app.get("/baishatun_MAZU_news")
async def read_baishatun_news(
    hours: int = Query(
        default=settings.default_hours,
        ge=0,
        le=settings.max_hours,
    )
) -> Response:
    payload = await news_service.get_baishatun_news(hours=hours)
    location_fields = await asyncio.to_thread(
        baishatun_location_service.fetch_location_fields
    )
    now = datetime.now(taiwan_timezone)

    response_payload = {
        "topic": payload["topic"],
        "hours": payload["hours"],
        "count": payload["count"],
        "system_time": f"UTC+8 {now.strftime('%Y-%m-%d %H:%M:%S')}",
        **location_fields,
        "items": payload["items"],
    }
    return _create_json_response(response_payload)


@app.get("/baishatun_MAZU_location")
def read_baishatun_location(payload: str | None = None) -> Response:
    location_fields = baishatun_location_service.fetch_location_fields()
    if payload is not None:
        return _create_json_response(location_fields)

    location_text = build_baishatun_mazu_location_text(location_fields)
    return create_location_text_response(location_text)


@app.get("/yt_live_snapshot")
def get_yt_live_snapshot(
    url: str = Query(..., description="YouTube 直播網址"),
) -> Response:
    try:
        image_bytes = yt_snapshot_service.capture_snapshot_bytes(url)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=image_bytes, media_type="image/jpeg")


def _create_json_response(payload: dict) -> Response:
    return Response(
        content=json.dumps(payload, ensure_ascii=False),
        media_type="application/json; charset=utf-8",
    )
