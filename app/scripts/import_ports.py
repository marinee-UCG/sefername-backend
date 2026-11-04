"""Load the port list from the searoute package into the ports table.

Run from the backend folder:
    python -m app.scripts.import_ports

Safe to run again: existing ports (same locode) are updated, not duplicated.
"""
import json
from importlib.resources import files

from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app.models.port import Port


def load_ports():
    path = files("searoute") / "data" / "ports.geojson"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["features"]


def to_row(feature):
    props = feature["properties"]
    # GeoJSON order is [lon, lat]
    lon, lat = feature["geometry"]["coordinates"]
    locode = props["port"]

    # A UN/LOCODE is always 5 characters; skip broken entries
    if len(locode) != 5:
        return None
    country_code = locode[:2]

    return {
        "locode": locode,
        "name": props["name"],
        "country_code": country_code,
        "lat": lat,
        "lon": lon,
    }


def main():
    rows = []
    seen = set()

    for feature in load_ports():
        row = to_row(feature)
        if row is None:
            continue
        # The data lists some codes twice; keep the first one
        if row["locode"] in seen:
            continue
        seen.add(row["locode"])
        rows.append(row)

    # Upsert: insert new ports, update the ones already in the table
    stmt = insert(Port).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["locode"],
        set_={
            "name": stmt.excluded.name,
            "country_code": stmt.excluded.country_code,
            "lat": stmt.excluded.lat,
            "lon": stmt.excluded.lon,
        },
    )

    with SessionLocal() as db:
        db.execute(stmt)
        db.commit()

    print(f"{len(rows)} ports imported")


if __name__ == "__main__":
    main()
