import os

import httpx 
from dotenv import load_dotenv
from commute_mcp.models import Departure


load_dotenv()

BOARD_URL = "https://api1.raildata.org.uk/1010-live-departure-board-dep1_2/LDBWS/api/20220120/GetDepartureBoard/{crs}" 

async def get_departure_board(crs: str) -> list[Departure]:
    headers = {"x-apikey": os.environ.get("RAIL_API_KEY")}

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(BOARD_URL.format(crs=crs), headers=headers)
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
    departures = []
    for service in data.get("trainServices", []):
        departures.append(parse_service(service))
    return departures

if __name__ == "__main__":
    import asyncio  

    for departure in asyncio.run(get_departure_board("WAT")):
        print(departure)

