from commute_mcp.stations import find_stations


def names(stations):
    return [station["stationName"] for station in stations]


def test_finds_station_containing_query():
    assert names(find_stations("Paddington")) == ["London Paddington"]


def test_search_ignores_case_and_spaces():
    assert names(find_stations("  pADDINGTON ")) == ["London Paddington"]


def test_returns_every_station_containing_query():
    assert names(find_stations("Bristol")) == ["Bristol Parkway", "Bristol Temple Meads"]


def test_respects_limit():
    assert len(find_stations("London", limit=3)) == 3


def test_typo_falls_back_to_similar_names():
    assert find_stations("Guidford")[0]["stationName"] == "Guildford"


def test_nothing_similar_returns_empty_list():
    assert find_stations("qqqqqqqqqq") == []


def test_station_has_crs_and_coordinates():
    station = find_stations("Guildford")[0]
    assert station["crsCode"] == "GLD"
    assert float(station["lat"]) > 51
    assert float(station["long"]) < 0
