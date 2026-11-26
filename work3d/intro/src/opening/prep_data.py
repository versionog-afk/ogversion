#!/usr/bin/env python3
"""Cut the outside data sets in raw/ down to what the renderer needs -> data/.

    python3 fetch_data.py && python3 prep_data.py

Nothing is invented here: every number written to data/ is copied from a
source file (coordinates rounded to 1e-5 degree, about one metre). Far away
from Kaunas the coast is thinned (every 12th vertex) because it only ever
shows near the horizon.
"""
import gzip
import json
import math
import os

import numpy as np

from geo import AE, KAUNAS_LAT, KAUNAS_LON, R_EARTH

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "data")
Q = 1e5  # coordinates are stored as integers of 1e-5 degree

LAND_KM = 3300.0     # coast and big lakes
TOWN_KM = 3200.0     # towns (beyond 1200 km only those of 5000 people and more)
ROAD_KM = 1200.0     # roads and built-up areas
RIVER_KM = 450.0

ae = AE()


def dist_km(lonlat):
    a = np.asarray(lonlat, dtype=np.float64)
    x, y = ae.forward(a[:, 1], a[:, 0])
    return np.hypot(x, y)


def pack(lonlat):
    a = np.rint(np.asarray(lonlat, dtype=np.float64)[:, :2] * Q).astype(np.int64)
    return a.reshape(-1).tolist()


def thin_ring(lonlat, keep_km):
    a = np.asarray(lonlat, dtype=np.float64)
    d = dist_km(a)
    if d.min() > keep_km:
        return None
    keep = (d < keep_km + 150.0) | (np.arange(len(a)) % 12 == 0)
    keep[0] = keep[-1] = True
    a = a[keep]
    return a if len(a) >= 4 else None


def save(name, obj):
    path = os.path.join(OUT, name)
    with gzip.GzipFile(path, "wb", mtime=0) as f:
        f.write(json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    print("%-22s %8.1f kB" % (name, os.path.getsize(path) / 1024.0))


# ---- TopoJSON (world-atlas) ------------------------------------------------
def topo_rings(path, object_name, want_id=None):
    """Decode a world-atlas TopoJSON object into a list of rings (arrays of lon, lat)."""
    t = json.load(open(path))
    sx, sy = t["transform"]["scale"]
    tx, ty = t["transform"]["translate"]
    arcs = []
    for arc in t["arcs"]:
        a = np.cumsum(np.asarray(arc, dtype=np.float64), axis=0)
        arcs.append(np.stack([a[:, 0] * sx + tx, a[:, 1] * sy + ty], axis=1))

    def ring(idx):
        parts = []
        for i in idx:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            parts.append(a if not parts else a[1:])
        return np.concatenate(parts)

    rings = []
    for g in t["objects"][object_name]["geometries"]:
        if want_id is not None and str(g.get("id")) != want_id:
            continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        for poly in polys:
            for r in poly:
                rings.append(ring(r))
    return rings


def geojson_features(name):
    return json.load(open(os.path.join(RAW, name), encoding="utf-8"))["features"]


def polygon_rings(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    return []


def lines(geom):
    if geom is None:
        return []
    if geom["type"] == "LineString":
        return [geom["coordinates"]]
    if geom["type"] == "MultiLineString":
        return geom["coordinates"]
    return []


def main():
    os.makedirs(OUT, exist_ok=True)

    # coast: Natural Earth 1:10m land, as redistributed by world-atlas
    land = []
    for r in topo_rings(os.path.join(RAW, "world-atlas-2.0.2", "land-10m.json"), "land"):
        t = thin_ring(r, LAND_KM)
        if t is not None:
            land.append(pack(t))
    save("land.json.gz", {"source": "world-atlas@2.0.2 land-10m.json (Natural Earth 1:10m, v4.1.0)",
                          "unit": "1e-5 degree, flat [lon, lat, lon, lat, ...] per ring", "rings": land})

    # outline of Lithuania: used for checks and statistics only, never drawn in the film
    lt = topo_rings(os.path.join(RAW, "world-atlas-2.0.2", "countries-10m.json"), "countries", want_id="440")
    save("lithuania.json.gz", {"source": "world-atlas@2.0.2 countries-10m.json, id 440 (Natural Earth 1:10m)",
                               "unit": "1e-5 degree", "rings": [pack(r) for r in lt]})

    # lakes and reservoirs
    lakes = []
    for name, lim in (("ne_10m_lakes.geojson", LAND_KM), ("ne_10m_lakes_europe.geojson", 1500.0)):
        for f in geojson_features(name):
            if not f["geometry"]:
                continue
            for poly in polygon_rings(f["geometry"]):
                if dist_km(poly[0]).min() > lim:
                    continue
                lakes.append({"name": f["properties"].get("name"), "rings": [pack(r) for r in poly]})
    save("lakes.json.gz", {"source": "Natural Earth 1:10m lakes + European lakes supplement, v5.1.2",
                           "unit": "1e-5 degree", "lakes": lakes})

    # rivers near Kaunas (Nemunas, Neris and neighbours)
    rivers = []
    for name in ("ne_10m_rivers_lake_centerlines.geojson", "ne_10m_rivers_europe.geojson"):
        for f in geojson_features(name):
            p = f["properties"]
            for ln in lines(f["geometry"]):
                if len(ln) < 2 or dist_km(ln).min() > RIVER_KM:
                    continue
                rivers.append({"name": p.get("name"), "rank": p.get("scalerank"), "cla": p.get("featurecla"),
                               "line": pack(ln)})
    save("rivers.json.gz", {"source": "Natural Earth 1:10m river centre lines + European supplement, v5.1.2",
                            "unit": "1e-5 degree", "rivers": rivers})

    # roads
    roads = []
    for f in geojson_features("ne_10m_roads.geojson"):
        p = f["properties"]
        if p.get("type") in ("Ferry Route", "Ferry, seasonal", "Track"):
            continue
        for ln in lines(f["geometry"]):
            if len(ln) < 2 or dist_km(ln).min() > ROAD_KM:
                continue
            roads.append({"type": p.get("type"), "rank": p.get("scalerank"), "line": pack(ln)})
    save("roads.json.gz", {"source": "Natural Earth 1:10m roads, v5.1.2", "unit": "1e-5 degree", "roads": roads})

    # built-up areas
    urban = []
    for f in geojson_features("ne_10m_urban_areas.geojson"):
        if not f["geometry"]:
            continue
        for poly in polygon_rings(f["geometry"]):
            if dist_km(poly[0]).min() > ROAD_KM:
                continue
            urban.append({"area_sqkm": f["properties"].get("area_sqkm"), "rings": [pack(r) for r in poly]})
    save("urban.json.gz", {"source": "Natural Earth 1:10m urban areas, v5.1.2", "unit": "1e-5 degree", "areas": urban})

    # towns: GeoNames cities1000 (all populated places with 1000 inhabitants or more, and seats of administration)
    towns = []
    with open(os.path.join(RAW, "cities-with-1000-1.0.4", "cities1000.txt"), encoding="utf-8") as fh:
        rows = [ln.rstrip("\n").split("\t") for ln in fh]
    lat = np.array([float(r[4]) for r in rows])
    lon = np.array([float(r[5]) for r in rows])
    x, y = ae.forward(lat, lon)
    d = np.hypot(x, y)
    for r, dk in zip(rows, d):
        pop = int(r[14])
        if dk > TOWN_KM or pop <= 0 or (dk > 1200.0 and pop < 5000):
            continue
        towns.append([int(r[0]), r[1], float(r[4]), float(r[5]), pop, r[7], r[8]])
    towns.sort(key=lambda t: -t[4])
    save("towns.json.gz", {"source": "GeoNames cities1000 (dump of 2020-03-18, npm cities-with-1000@1.0.4), CC BY 4.0",
                           "columns": ["geonameid", "name", "lat", "lon", "population", "feature_code", "country"],
                           "towns": towns})

    # second, independent source for the positions of the main towns (cross-check only)
    places = []
    for f in geojson_features("ne_10m_populated_places_simple.geojson"):
        p = f["properties"]
        lo, la = f["geometry"]["coordinates"][:2]
        if dist_km([[lo, la]])[0] < 700.0:
            places.append([p.get("name"), la, lo, p.get("pop_max"), p.get("adm0_a3"), p.get("featurecla")])
    save("ne_places.json.gz", {"source": "Natural Earth 1:10m populated places (simple), v5.1.2",
                               "columns": ["name", "lat", "lon", "pop_max", "adm0_a3", "featurecla"],
                               "places": places})


if __name__ == "__main__":
    main()
