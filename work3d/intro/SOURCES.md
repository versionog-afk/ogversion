# Outside data and material used for the intro

| what | used for | licence | where |
|---|---|---|---|
| Natural Earth 1:10m (land, lakes, rivers, roads, urban areas, populated places) | the opening frame: coast, water, lights | public domain | fetched by `src/opening/fetch_data.py` into `src/opening/raw/` (not in git); prepared extracts in `src/opening/data/` |
| world-atlas 2.0.2 (npm), built from Natural Earth | country and land outlines | ISC for the package, data public domain | same |
| GeoNames `cities1000` | positions and population of towns | CC BY 4.0: credit "GeoNames" wherever the data set itself is redistributed | same; the prepared extract `data/towns.json.gz` is derived from it |

Not used: any satellite imagery, any map tiles.

The four game frames in `ref/` are the owner's own and are local only.
