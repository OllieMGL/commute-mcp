import os
import re
import httpx

from dotenv import load_dotenv
from commute_mcp.models import Departure, DepartureBoard
from commute_mcp.cache import TTLCache


load_dotenv()

BOARD_URL = "https://api1.raildata.org.uk/1010-live-departure-board-dep1_2/LDBWS/api/20220120/GetDepBoardWithDetails/{crs}"
HTML_TAG = re.compile(r"<[^>]+>") # Disruption messages from the API contain HTML links ==> strip tags AI gets plain text.
DEPARTURES_CACHE = TTLCache(30)  # departures change quickly, so keep them for 30 seconds

class MissingApiKeyError(Exception):
    """Raised when RAIL_API_KEY is not set."""


async def get_departure_board(
    crs: str, destination_crs: str | None = None, limit: int = 10 # crs is station you are leaving from, destination is optional 
) -> DepartureBoard:
    
    api_key = os.environ.get("RAIL_API_KEY")
    if not api_key:
        raise MissingApiKeyError("RAIL_API_KEY is not set. Add it to your .env file.")
    
    key = (crs, destination_crs, limit)
    cached = DEPARTURES_CACHE.get(key)
    if cached is not None:
        return cached

    headers = {"x-apikey": api_key}

    params = {"numRows": min(limit, 9)} # the with-details board allows at most 9 rows
    if destination_crs:
        params["filterCrs"] = destination_crs
        params["filterType"] = "to" # trains that call at this station after leaving

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            BOARD_URL.format(crs=crs), headers=headers, params=params
        )
        response.raise_for_status()

    board = parse_departure_board(response.json(), destination_crs)
    DEPARTURES_CACHE.set(key, board)
    return board

def find_calling_point(service: dict, crs: str | None) -> dict | None:
    for calling_points in service.get("subsequentCallingPoints", []):
        for point in calling_points["callingPoint"]:
            if point["crs"] == crs:
                return point
    return None


def parse_service(service: dict, destination_crs: str | None = None) -> Departure:
    destinations = []
    for place in service["destination"]:
        destinations.append(place["locationName"])

    # None if no destination was given, or the train doesn't call there
    arrival = find_calling_point(service, destination_crs)
    arrival_scheduled = None
    arrival_expected = None
    if arrival:
        arrival_scheduled = arrival["st"]
        arrival_expected = arrival.get("et")

    return Departure(
        scheduled=service["std"],
        expected=service["etd"],
        destination=" and ".join(destinations),
        platform=service.get("platform"),
        operator=service["operator"],
        is_cancelled=service["isCancelled"],
        reason=service.get("cancelReason") or service.get("delayReason"),
        service_id=service["serviceID"],
        arrival_scheduled=arrival_scheduled,
        arrival_expected=arrival_expected,
    )

def parse_message(message: dict) -> str:
    return HTML_TAG.sub("", message["Value"]).strip()

def parse_departure_board(data: dict, destination_crs: str | None = None) -> DepartureBoard:

    services = data.get("trainServices", []) + data.get("busServices", []) # bus services included for rail replacement
    departures = []
    for service in services:
        departures.append(parse_service(service, destination_crs))

    messages = []
    for message in data.get("nrccMessages", []): # returns an empty list when no disruptions 
        messages.append(parse_message(message))

    return DepartureBoard(
        station=data["locationName"],
        departures=departures,
        messages=messages,
    )


if __name__ == "__main__":
    import asyncio

    board = asyncio.run(get_departure_board("GLD", limit=3))
    print(board.station)
    print(board.messages)
    for departure in board.departures:
        print(departure)

