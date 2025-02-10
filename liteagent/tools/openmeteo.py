import httpx

from liteagent import tool, Tools


class OpenMeteo(Tools):
    client: httpx.AsyncClient = httpx.AsyncClient()

    forecast_attributes: list[str] = [
        "weather_code",
        "temperature_2m_max",
        "temperature_2m_min",
        "apparent_temperature_max",
        "apparent_temperature_min",
        "sunrise",
        "sunset",
        "daylight_duration",
        "sunshine_duration",
        "uv_index_max",
        "uv_index_clear_sky_max",
        "precipitation_sum",
        "rain_sum",
        "showers_sum",
        "snowfall_sum",
        "precipitation_hours",
        "precipitation_probability_max",
        "wind_speed_10m_max",
        "wind_gusts_10m_max",
        "wind_direction_10m_dominant",
        "shortwave_radiation_sum",
        "et0_fao_evapotranspiration"
    ]

    @tool
    async def geocoding(
        self,
        location: str,
        count: int | None
    ) -> dict:
        """ use this tool for retrieving the coordinates of the specified location """

        count = count or 10

        base_url = 'https://geocoding-api.open-meteo.com/v1'

        response = await self.client.request(
            url=f"{base_url}/search?name={location}&count={count}&language=en&format=json",
            method='GET'
        )

        response.raise_for_status()
        return response.json()

    @tool
    async def forecast(
        self,
        latitude: float,
        longitude: float,
    ) -> dict:
        """ use this tool for retrieving the forecast based on coordinates. use `geocoding` for getting the exact coordinates first. """

        base_url = 'https://api.open-meteo.com/v1'

        response = await self.client.request(
            url=f"{base_url}/forecast?latitude={latitude}&longitude={longitude}&daily={','.join(self.forecast_attributes)}",
            method='GET'
        )

        response.raise_for_status()
        return response.json()

openmeteo = OpenMeteo()
