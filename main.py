import json

from fastapi import FastAPI, Query
from fastapi.responses import Response

from config.settings import settings
from services.news_service import NewsService


app = FastAPI(title="News API", version="1.0.0")
news_service = NewsService()


@app.get("/")
def read_root() -> Response:
    return _json_utf8_response(
        {
            "message": "News API is running",
            "routes": [
                "/",
                f"/dajia_MAZU_news?hours={settings.default_hours}",
                f"/baishatun_MAZU_news?hours={settings.default_hours}",
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
    return _json_utf8_response(payload)


@app.get("/baishatun_MAZU_news")
async def read_baishatun_news(
    hours: int = Query(
        default=settings.default_hours,
        ge=0,
        le=settings.max_hours,
    )
) -> Response:
    payload = await news_service.get_baishatun_news(hours=hours)
    return _json_utf8_response(payload)


def _json_utf8_response(payload: dict) -> Response:
    return Response(
        content=json.dumps(payload, ensure_ascii=False),
        media_type="application/json; charset=utf-8",
    )
