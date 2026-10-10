from dataclasses import dataclass
from datetime import datetime

@dataclass
class CurrentWeather:
    time: datetime
    conditions: str
    temperature_c: float
    feels_like_c: float
    precipitation_mm: float
    wind_speed_kmh: float


@dataclass
class HourlyForecast:
    time: datetime
    conditions: str
    temperature_c: float
    precipitation_probability: int
    precipitation_mm: float
    wind_speed_kmh: float