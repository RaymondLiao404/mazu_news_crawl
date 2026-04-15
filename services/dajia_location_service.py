import math

import requests


class DajiaLocationService:
    API_URL = "https://mazu.skyeyes.tw/map.aspx/GetMazuLocation"
    HEADERS = {
        "Content-Type": "application/json",
    }
    PAYLOAD = {}

    def fetch_location_fields(self) -> dict:
        try:
            response = requests.post(
                self.API_URL,
                json=self.PAYLOAD,
                headers=self.HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return {}

        raw_location = payload.get("d")
        if not isinstance(raw_location, str) or not raw_location.strip():
            return {}

        parts = [part.strip() for part in raw_location.split(",", 5)]
        if len(parts) != 6:
            return {}

        x_coordinate, y_coordinate, address, _, _, _ = parts

        try:
            twd97_x = float(x_coordinate)
            twd97_y = float(y_coordinate)
        except ValueError:
            return {}

        latitude, longitude = self._convert_twd97_tm2_to_wgs84(
            x=twd97_x,
            y=twd97_y,
        )

        return {
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
            "relative_address": address,
            "twd97_x": twd97_x,
            "twd97_y": twd97_y,
        }

    def _convert_twd97_tm2_to_wgs84(self, x: float, y: float) -> tuple[float, float]:
        # This feed appears to use Taiwan's common projected CRS:
        # TWD97 / TM2 zone 121 (EPSG:3826).
        a = 6378137.0
        b = 6356752.314245
        long0 = math.radians(121)
        k0 = 0.9999
        dx = 250000.0

        eccentricity = math.sqrt(1 - (b**2) / (a**2))
        x_adjusted = x - dx
        meridional_arc = y / k0

        mu = meridional_arc / (
            a
            * (
                1
                - eccentricity**2 / 4
                - 3 * eccentricity**4 / 64
                - 5 * eccentricity**6 / 256
            )
        )
        e1 = (1 - math.sqrt(1 - eccentricity**2)) / (
            1 + math.sqrt(1 - eccentricity**2)
        )

        j1 = 3 * e1 / 2 - 27 * e1**3 / 32
        j2 = 21 * e1**2 / 16 - 55 * e1**4 / 32
        j3 = 151 * e1**3 / 96
        j4 = 1097 * e1**4 / 512
        footprint_latitude = (
            mu
            + j1 * math.sin(2 * mu)
            + j2 * math.sin(4 * mu)
            + j3 * math.sin(6 * mu)
            + j4 * math.sin(8 * mu)
        )

        second_eccentricity_squared = eccentricity**2 / (1 - eccentricity**2)
        c1 = second_eccentricity_squared * math.cos(footprint_latitude) ** 2
        t1 = math.tan(footprint_latitude) ** 2
        r1 = a * (1 - eccentricity**2) / (
            (1 - eccentricity**2 * math.sin(footprint_latitude) ** 2) ** 1.5
        )
        n1 = a / math.sqrt(
            1 - eccentricity**2 * math.sin(footprint_latitude) ** 2
        )
        d = x_adjusted / (n1 * k0)

        latitude = footprint_latitude - (
            n1
            * math.tan(footprint_latitude)
            / r1
            * (
                d**2 / 2
                - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * second_eccentricity_squared)
                * d**4
                / 24
                + (
                    61
                    + 90 * t1
                    + 298 * c1
                    + 45 * t1**2
                    - 3 * c1**2
                    - 252 * second_eccentricity_squared
                )
                * d**6
                / 720
            )
        )
        longitude = long0 + (
            d
            - (1 + 2 * t1 + c1) * d**3 / 6
            + (
                5
                - 2 * c1
                + 28 * t1
                - 3 * c1**2
                + 8 * second_eccentricity_squared
                + 24 * t1**2
            )
            * d**5
            / 120
        ) / math.cos(footprint_latitude)

        return math.degrees(latitude), math.degrees(longitude)
