import requests


class BaishatunLocationService:
    # 第三方來源：白沙屯即時位置資料 API。
    API_URL = "http://60.199.132.186/s.php"

    def fetch_location_fields(self) -> dict:
        # 從第三方 API 取得白沙屯位置，只整理出目前路由需要的欄位。
        try:
            response = requests.get(self.API_URL, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            return {}

        first_line = next(
            (line.strip() for line in response.text.splitlines() if line.strip()),
            "",
        )
        if not first_line:
            return {}

        # 原始格式例如：
        # 1.20260406184917,24.077958,120.538538,163,彰化縣彰化市永樂街218號,衛星訊號確認中
        parts = [part.strip() for part in first_line.split(",")]
        if len(parts) < 5:
            return {}

        try:
            # GPS 小數位縮短，避免回傳太長。
            latitude = round(float(parts[1]), 4)
            longitude = round(float(parts[2]), 4)
        except ValueError:
            return {}

        return {
            "latitude": latitude,
            "longitude": longitude,
            "relative_address": parts[4],
        }
