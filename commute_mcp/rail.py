import os

import httpx 
from dotenv import load_dotenv
from commute_mcp.models import Departure


load_dotenv()

BOARD_URL = "https://api1.raildata.org.uk/1010-live-departure-board-dep1_2/LDBWS/api/20220120/GetDepartureBoard/{crs}"

class MissingApiKeyError(Exception):
    """Raised when RAIL_API_KEY is not set."""


async def get_departure_board(
    crs: str, destination_crs: str | None = None, limit: int = 10 # crs is station you are leaving from, destination is optional 
) -> list[Departure]:
    
    api_key = os.environ.get("RAIL_API_KEY")
    if not api_key:
        raise MissingApiKeyError("RAIL_API_KEY is not set. Add it to your .env file.")
    
    headers = {"x-apikey": api_key}

    params = {"numRows": limit}
    if destination_crs:
        params["filterCrs"] = destination_crs
        params["filterType"] = "to" # trains that call at this station after leaving

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            BOARD_URL.format(crs=crs), headers=headers, params=params
        )
        response.raise_for_status()

    return parse_departure_board(response.json())


def parse_service(service: dict) -> Departure:
    destinations = []
    for place in service["destination"]:
        destinations.append(place["locationName"])

    return Departure(
        scheduled=service["std"],
        expected=service["etd"],
        destination=" and ".join(destinations),
        platform=service.get("platform"),
        operator=service["operator"],
        is_cancelled=service["isCancelled"],
        reason=service.get("cancelReason") or service.get("delayReason"),
        service_id=service["serviceID"],
    )


def parse_departure_board(data: dict) -> list[Departure]:
    services = data.get("trainServices", []) + data.get("busServices", []) # bus services included for rail replacement
    departures = []
    for service in services:
        departures.append(parse_service(service))
    return departures


if __name__ == "__main__":
    import asyncio  

    for departure in asyncio.run(get_departure_board("GLD", limit=3)):
        print(departure)

