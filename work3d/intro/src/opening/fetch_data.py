#!/usr/bin/env python3
"""Download the outside data sets into raw/ (local only, not in git).

Every file is pinned to a version and checked against a SHA-256, so a rebuild
uses exactly the data the committed pictures were made from. Only needed when
data/ has to be regenerated: the compact subsets in data/ are committed.

    python3 fetch_data.py

Uses curl (it honours HTTPS_PROXY and CURL_CA_BUNDLE). Licences: ../../SOURCES.md
"""
import hashlib
import os
import subprocess
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")

NE_TAG = "v5.1.2"
NE_BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/%s/geojson/" % NE_TAG

# (url, local name, sha256, members to extract from a tarball or None)
FILES = [
    ("https://registry.npmjs.org/world-atlas/-/world-atlas-2.0.2.tgz", "world-atlas-2.0.2.tgz",
     "032e7765f2ce00edaeafec23ff22bc3b77e42987c257da944cc585b452c05b97",
     ["package/land-10m.json", "package/countries-10m.json", "package/LICENSE"]),
    ("https://registry.npmjs.org/cities-with-1000/-/cities-with-1000-1.0.4.tgz", "cities-with-1000-1.0.4.tgz",
     "aadd9eb4c4878500b2728f6e431e5b1c94e94ce3fea98f87d34024ad682fa8f5",
     ["package/cities1000.txt", "package/README.md"]),
    (NE_BASE + "ne_10m_roads.geojson", "ne_10m_roads.geojson",
     "66a0c7b438e92fd124822cc5921cfa11042f48c294ade5e0f03f2c6640fd0248", None),
    (NE_BASE + "ne_10m_urban_areas.geojson", "ne_10m_urban_areas.geojson",
     "5136ffd816a9b28c0f295e6797b4c03eaa421be80d78b90f542db4a932dd4497", None),
    (NE_BASE + "ne_10m_lakes.geojson", "ne_10m_lakes.geojson",
     "2d036f53dedec578001c5c30c2959ee7d4eebc1306900fa4367c49929ec8f2d9", None),
    (NE_BASE + "ne_10m_lakes_europe.geojson", "ne_10m_lakes_europe.geojson",
     "b4dd9e7a5edd0d07b54768b5404d1ebe77f80b9d579c85fff65f90cf50369769", None),
    (NE_BASE + "ne_10m_rivers_lake_centerlines.geojson", "ne_10m_rivers_lake_centerlines.geojson",
     "bb854a900ecbd3b408df46d5e16e3e0f974ba55993f9d8b5c26e855273c0905a", None),
    (NE_BASE + "ne_10m_rivers_europe.geojson", "ne_10m_rivers_europe.geojson",
     "90712202ac46985812e90840df9acd5101599a9c649868d5bc55ee96c2fedd4c", None),
    (NE_BASE + "ne_10m_populated_places_simple.geojson", "ne_10m_populated_places_simple.geojson",
     "fd3fa867a320cbd5c5b6bb5bc550afeec2939fb2cef688e508007282a55ac42f", None),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(RAW, exist_ok=True)
    for url, name, digest, members in FILES:
        path = os.path.join(RAW, name)
        if not (os.path.exists(path) and sha256(path) == digest):
            print("fetch", url)
            subprocess.run(["curl", "-fsSL", "--retry", "3", "-m", "600", "-o", path + ".part", url], check=True)
            got = sha256(path + ".part")
            if got != digest:
                os.remove(path + ".part")
                sys.exit("SHA-256 mismatch for %s: got %s" % (name, got))
            os.replace(path + ".part", path)
        else:
            print("ok   ", name)
        if members:
            out = os.path.join(RAW, name[:-4])
            os.makedirs(out, exist_ok=True)
            with tarfile.open(path, "r:gz") as tar:
                for m in members:
                    src = tar.extractfile(m)
                    with open(os.path.join(out, os.path.basename(m)), "wb") as dst:
                        dst.write(src.read())
    print("raw data ready in", RAW)


if __name__ == "__main__":
    main()
