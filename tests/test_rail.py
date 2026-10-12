import httpx
import pytest

from commute_mcp.rail import (
    MissingApiKeyError,
    find_calling_point,
    get_departure_board,
    parse_departure_board,
    parse_message,
)

RAIL_API = "https://api1.raildata.org.uk/"


# Parsing

def test_parse_message_strips_html():
    message = {"Value": "See the <a href='https://example.com'>National Rail</a> website."}
    assert parse_message(message) == "See the National Rail website."


def test_find_calling_point_found(departure_board_data):
    train = departure_board_data["trainServices"][0]
    point = find_calling_point(train, "WOK")
    assert point["st"] == "18:11"


def test_find_calling_point_not_called_at(departure_board_data):
    train = departure_board_data["trainServices"][0]
    assert find_calling_point(train, "BRI") is None


def test_find_calling_point_without_calling_points():
    # The plain (not "with details") board has no subsequentCallingPoints
    assert find_calling_point({"std": "18:01"}, "WAT") is None


def test_parse_departure_board(departure_board_data):
    board = parse_departure_board(departure_board_data, "WAT")
    assert board.station == "Guildford"
    assert len(board.departures) == 2

    first = board.departures[0]
    assert first.scheduled == "18:01"
    assert first.expected == "18:03"
    assert first.destination == "London Waterloo"
    assert first.platform == "5"
    assert first.reason == "This train has been delayed by a speed restriction"
    assert first.service_id == "1111111GUILDFD_"


def test_parse_departure_board_arrival_times(departure_board_data):
    board = parse_departure_board(departure_board_data, "WAT")
    assert board.departures[0].arrival_scheduled == "18:41"
    assert board.departures[0].arrival_expected == "18:43"
    assert board.departures[1].arrival_expected == "On time"


def test_parse_departure_board_without_destination_has_no_arrivals(departure_board_data):
    board = parse_departure_board(departure_board_data)
    assert board.departures[0].arrival_scheduled is None
    assert board.departures[0].arrival_expected is None


def test_parse_departure_board_messages_have_no_html(departure_board_data):
    board = parse_departure_board(departure_board_data)
    assert board.messages == [
        "Disruption between Woking and London Waterloo. See the National Rail website."
    ]


def test_parse_departure_board_includes_rail_replacement_buses(bus_board_data):
    # During engineering works the API sends buses and no trainServices at all
    board = parse_departure_board(bus_board_data)
    assert len(board.departures) == 1
    assert board.departures[0].platform == "BUS"
    assert board.departures[0].destination == "Woking"
    assert board.messages == [
        "Buses replace trains between Guildford and Woking due to engineering works."
    ]


# API calls (respx fakes National Rail, so no real request is made)


async def test_request_sends_key_and_filter(respx_mock, departure_board_data):
    route = respx_mock.get(url__startswith=RAIL_API).mock(
        return_value=httpx.Response(200, json=departure_board_data)
    )
    await get_departure_board("GLD", destination_crs="WAT", limit=3)

    request = route.calls.last.request
    assert request.url.path.endswith("/GetDepBoardWithDetails/GLD")
    assert request.headers["x-apikey"] == "test-key"
    assert request.url.params["numRows"] == "3"
    assert request.url.params["filterCrs"] == "WAT"
    assert request.url.params["filterType"] == "to"


async def test_request_without_destination_has_no_filter(respx_mock, departure_board_data):
    route = respx_mock.get(url__startswith=RAIL_API).mock(
        return_value=httpx.Response(200, json=departure_board_data)
    )
    await get_departure_board("GLD")

    assert "filterCrs" not in route.calls.last.request.url.params


async def test_limit_is_capped_at_nine(respx_mock, departure_board_data):
    route = respx_mock.get(url__startswith=RAIL_API).mock(
        return_value=httpx.Response(200, json=departure_board_data)
    )
    await get_departure_board("GLD", limit=10)

    assert route.calls.last.request.url.params["numRows"] == "9"


async def test_missing_api_key_raises_before_any_request(monkeypatch, respx_mock):
    monkeypatch.delenv("RAIL_API_KEY")
    route = respx_mock.get(url__startswith=RAIL_API)

    with pytest.raises(MissingApiKeyError):
        await get_departure_board("GLD")
    assert not route.called


async def test_server_error_raises(respx_mock):
    respx_mock.get(url__startswith=RAIL_API).mock(return_value=httpx.Response(500))
    with pytest.raises(httpx.HTTPStatusError):
        await get_departure_board("GLD")


async def test_board_is_cached(respx_mock, departure_board_data):
    route = respx_mock.get(url__startswith=RAIL_API).mock(
        return_value=httpx.Response(200, json=departure_board_data)
    )
    first = await get_departure_board("GLD", "WAT")
    second = await get_departure_board("GLD", "WAT")

    assert route.call_count == 1
    assert second is first


async def test_different_question_is_not_served_from_cache(respx_mock, departure_board_data):
    route = respx_mock.get(url__startswith=RAIL_API).mock(
        return_value=httpx.Response(200, json=departure_board_data)
    )
    await get_departure_board("GLD", "WAT", limit=1)
    await get_departure_board("GLD", "WAT", limit=2)

    assert route.call_count == 2


async def test_errors_are_not_cached(respx_mock, departure_board_data):
    # First request fails, second succeeds: the failure must not be remembered
    respx_mock.get(url__startswith=RAIL_API).mock(
        side_effect=[httpx.Response(500), httpx.Response(200, json=departure_board_data)]
    )
    with pytest.raises(httpx.HTTPStatusError):
        await get_departure_board("GLD")

    board = await get_departure_board("GLD")
    assert board.station == "Guildford"
