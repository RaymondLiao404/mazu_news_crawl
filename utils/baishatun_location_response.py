from fastapi.responses import Response


def create_baishatun_location_text_response(content: str) -> Response:
    return Response(content=content, media_type="text/plain; charset=utf-8")


def build_baishatun_mazu_location_text(location_fields: dict) -> str:
    latitude = location_fields.get("latitude", "NAN")
    longitude = location_fields.get("longitude", "NAN")
    address = location_fields.get("relative_address", "NAN")
    return f"白沙屯媽祖目前位置，GPS：{latitude}, {longitude}，地址：{address}"
