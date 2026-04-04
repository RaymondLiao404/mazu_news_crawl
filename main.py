from fastapi import FastAPI, Query

from config.settings import settings
from services.news_service import NewsService


app = FastAPI(title="News API", version="1.0.0")
news_service = NewsService()


@app.get("/")
def read_root() -> dict:
    return {
        "message": "News API is running",
        "routes": [
            "/",
            f"/dajia_MAZU_news?hours={settings.default_hours}",
        ],
    }

@app.get("/dajia_MAZU_news")
async def read_dajia_news(
    hours: int = Query(
        default=settings.default_hours,
        ge=0,
        le=settings.max_hours,
    )
) -> dict:
    return await news_service.get_dajia_news(hours=hours)
