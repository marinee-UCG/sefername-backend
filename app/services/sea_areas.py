"""A rough name for where a position lies at sea ("Arabian Sea"), for the under way card.

Hand-made boxes (lon_min, lon_max, lat_min, lat_max), most specific first: the first box that holds
the point wins. Good enough for "approximate area"; not a chart, not borders. None when nothing fits.
"""

AREAS: list[tuple[str, tuple[float, float, float, float]]] = [
    ("Sea of Marmara", (26.9, 29.95, 40.25, 41.1)),
    ("Bosphorus", (28.95, 29.2, 41.0, 41.25)),
    ("Dardanelles", (26.15, 26.9, 40.0, 40.5)),
    ("Black Sea", (27.4, 41.8, 40.9, 46.8)),
    ("Sea of Azov", (34.8, 39.4, 45.2, 47.3)),
    ("Aegean Sea", (22.5, 28.3, 35.2, 41.0)),
    ("Suez Canal", (32.2, 32.65, 29.9, 31.35)),
    ("Gulf of Suez", (32.3, 34.0, 27.6, 30.0)),
    ("Strait of Gibraltar", (-6.1, -5.25, 35.8, 36.2)),
    ("Adriatic Sea", (12.0, 20.0, 40.0, 45.8)),
    ("Tyrrhenian Sea", (9.0, 16.2, 37.8, 43.8)),
    ("Ionian Sea", (15.6, 22.5, 36.0, 40.5)),
    ("Mediterranean Sea", (-5.6, 36.3, 30.0, 44.5)),
    ("Red Sea", (32.2, 43.5, 12.4, 28.0)),
    ("Bab-el-Mandeb", (43.0, 43.7, 12.3, 13.0)),
    ("Gulf of Aden", (43.3, 51.3, 10.5, 15.5)),
    ("Strait of Hormuz", (55.5, 57.5, 25.8, 27.2)),
    ("Persian Gulf", (47.7, 56.5, 23.5, 30.5)),
    ("Gulf of Oman", (56.5, 61.8, 22.0, 26.5)),
    ("Arabian Sea", (51.3, 77.0, 0.0, 25.5)),
    ("Bay of Bengal", (78.0, 95.0, 5.0, 23.0)),
    ("Andaman Sea", (92.0, 99.0, 5.0, 17.0)),
    ("Singapore Strait", (103.5, 104.5, 1.0, 1.5)),
    ("Strait of Malacca", (95.0, 104.5, 1.0, 6.5)),
    ("Java Sea", (105.0, 119.0, -8.0, -3.0)),
    ("South China Sea", (99.0, 121.0, 1.5, 23.0)),
    ("Taiwan Strait", (117.5, 121.0, 22.0, 26.0)),
    ("East China Sea", (119.0, 131.0, 24.0, 33.5)),
    ("Yellow Sea", (117.5, 126.8, 33.5, 41.0)),
    ("Sea of Japan", (127.5, 142.0, 33.5, 52.0)),
    ("Philippine Sea", (121.0, 145.0, 5.0, 33.0)),
    ("Coral Sea", (142.0, 170.0, -30.0, -9.0)),
    ("Tasman Sea", (147.0, 175.0, -48.0, -30.0)),
    ("English Channel", (-5.8, 1.9, 48.5, 51.1)),
    ("North Sea", (-4.0, 9.5, 51.0, 61.0)),
    ("Baltic Sea", (9.5, 30.5, 53.5, 66.0)),
    ("Irish Sea", (-6.5, -2.8, 51.5, 55.5)),
    ("Bay of Biscay", (-10.0, -1.0, 43.2, 48.5)),
    ("Norwegian Sea", (-5.0, 20.0, 61.0, 72.0)),
    ("Gulf of Mexico", (-98.0, -80.5, 18.0, 31.0)),
    ("Caribbean Sea", (-89.0, -59.5, 8.5, 22.5)),
    ("Panama Canal", (-80.0, -79.4, 8.8, 9.45)),
    ("Gulf of Guinea", (-5.0, 12.0, -5.0, 6.5)),
    ("Mozambique Channel", (32.0, 50.0, -27.0, -10.0)),
    ("Cape of Good Hope", (16.0, 22.0, -37.5, -33.0)),
    ("Cape Horn", (-70.0, -62.0, -58.5, -54.5)),
    ("North Atlantic Ocean", (-80.0, -5.0, 0.0, 65.0)),
    ("South Atlantic Ocean", (-70.0, 20.0, -60.0, 0.0)),
    ("Indian Ocean", (20.0, 120.0, -60.0, 0.0)),
    ("North Pacific Ocean", (120.0, 260.0, 0.0, 65.0)),
    ("South Pacific Ocean", (140.0, 290.0, -60.0, 0.0)),
    ("Southern Ocean", (-180.0, 180.0, -90.0, -60.0)),
    ("Arctic Ocean", (-180.0, 180.0, 66.0, 90.0)),
]


def sea_area(lat: float, lon: float) -> str | None:
    for name, (lon0, lon1, lat0, lat1) in AREAS:
        # The Pacific boxes run past 180°: test the point both as it is and shifted by 360°
        for x in (lon, lon + 360):
            if lon0 <= x <= lon1 and lat0 <= lat <= lat1:
                return name
    return None


def area_stats(passages: list[tuple[list[tuple[float, float]], float, int]]) -> list[dict]:
    """Days, miles and voyages per sea area, for the sea chart's hover.

    `passages`: (sailed coordinates as (lon, lat), hours at sea, voyage id) for each voyage.
    Each leg's miles go to the area of its middle; a voyage's hours are shared out by those miles.
    Every area is returned (in AREAS order, most specific first) so the app can tell which one the
    pointer is over; the ones never sailed have zeros.
    """
    from app.services.noon_track import haversine_nm

    totals = {name: {"nm": 0.0, "hours": 0.0, "voyages": set()} for name, _ in AREAS}
    for coordinates, hours, voyage_id in passages:
        legs = []
        for (lon_a, lat_a), (lon_b, lat_b) in zip(coordinates, coordinates[1:]):
            miles = haversine_nm(lat_a, lon_a, lat_b, lon_b)
            name = sea_area((lat_a + lat_b) / 2, (lon_a + lon_b) / 2)
            if name is not None and miles > 0:
                legs.append((name, miles))
        sailed = sum(miles for _, miles in legs)
        for name, miles in legs:
            totals[name]["nm"] += miles
            totals[name]["hours"] += hours * miles / sailed if sailed else 0
            totals[name]["voyages"].add(voyage_id)
    return [
        {
            "name": name,
            "box": list(box),
            "nm": round(totals[name]["nm"]),
            "days": round(totals[name]["hours"] / 24, 1),
            "voyages": len(totals[name]["voyages"]),
        }
        for name, box in AREAS
    ]
