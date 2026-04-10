from fastapi.responses import Response


def create_baishatun_location_text_response(content: str) -> Response:
    # 建立白沙屯媽祖位置專用的純文字回應。
    # 這支 API 主要是給瀏覽器、LINE 機器人或其他訊息服務直接顯示文字使用。
    return Response(content=content, media_type="text/plain; charset=utf-8")


def build_baishatun_mazu_location_text(location_fields: dict) -> str:
    # 把白沙屯媽祖位置資料組成固定的三行文字格式。
    # 若資料缺漏，統一以 NAN 補位，避免 API 回傳格式不一致。
    latitude = location_fields.get("latitude", "NAN")
    longitude = location_fields.get("longitude", "NAN")
    address = location_fields.get("relative_address", "NAN")
    return (
        "白沙屯媽祖目前位置:\n"
        f"GPS：{latitude}, {longitude}\n"
        f"地址：{address}"
    )
