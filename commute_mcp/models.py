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

@dataclass
class Departure:
    scheduled: str
    expected: str
    destination: str
    platform: str | None
    operator: str
    is_cancelled: bool
    reason: str | None
    service_id: str

@dataclass
class DepartureBoard:
    station: str
    departures: list[Departure]
    messages: list[str]

