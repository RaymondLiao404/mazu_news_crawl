class DajiaLocationService:
    # 先預留大甲媽位置欄位；未來若有 API，再改成實際抓取。
    def fetch_location_fields(self) -> dict:
        return {
            "latitude": "NAN",
            "longitude": "NAN",
            "relative_address": "NAN",
        }
