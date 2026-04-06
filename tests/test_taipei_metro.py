from src.taipei_metro import estimate_walk_minutes, find_nearest_station


def test_find_nearest_station_returns_expected_station_for_xinyi_center():
    station = find_nearest_station(25.0332, 121.5660)

    assert station is not None
    assert station["name"] == "台北101/世貿"
    assert station["walk_minutes"] == 5


def test_estimate_walk_minutes_has_small_access_buffer():
    assert estimate_walk_minutes(0.0) == 2
    assert estimate_walk_minutes(0.4) == 7
