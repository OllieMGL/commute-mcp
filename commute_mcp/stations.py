import csv
import difflib
from pathlib import Path

STATIONS_FILE = Path(__file__).parent / "data" / "stations.csv"


# returns a list of dictionaries station name as key
# {"stationName": "Abbey Wood", "lat": "51.490719", "long": "0.120343", "crsCode": "ABW", ...}
def load_stations() -> list[dict]:
    with open(STATIONS_FILE, encoding="utf-8", newline="") as file:  # with closes file automatically
        return list(csv.DictReader(file)) 


def find_stations(query: str, limit: int = 5) -> list[dict]:
    query = query.lower().strip()
    stations = load_stations()

    # First, look for names that contain the query
    matches = []
    for station in stations:
        if query in station["stationName"].lower():
            matches.append(station)
    if matches:
        return matches[:limit]

    # Nothing contains it, so typo --> look for similar names
    stations_by_name = {}
    for station in stations:
        stations_by_name[station["stationName"].lower()] = station

    # scores how similar two strings are, returns most similar
    close_names = difflib.get_close_matches(query, list(stations_by_name), n=limit) 

    results = []
    for name in close_names:
        results.append(stations_by_name[name])
    return results



if __name__ == "__main__":
    for station in find_stations("waterloo"):
        print(station["stationName"], station["crsCode"])
