# osmnames-sphinxsearch

Nominatim JSON API replacement made with osmnames.org data indexed by sphinx search

Using data from https://github.com/OSMNames/OSMNames - Database of geographic place names from OpenStreetMap for full text search downloadable for free. Website: http://osmnames.org


# REST API

## Search for autocomplete: `/q/<query>.js`

This endpoint returns 20 results matching the `<query>`.


## Country specific search for autocomplete `/<country_code>/q/<query>.js`

This endpoint returns 20 results matching the `<query>` within a specific country, identified by the `<country_code` (lowercase ISO 3166 Alpha-2 code).

## Place lookup search: `/r/<longitude>/<latitude>.js`

This endpoint returns 1 result matching the shortest distance from [longitude,latitude] to any entry in the data set.

## Class specific place lookup search: `/r/<class>/<longitude>/<latitude>.js`

This endpoint returns 1 result matching the shortest distance from [longtitude, latitude] to the class specific entry in the data set.

The `class` option can be a comma separated list of values (`/r/place,natural/<lon>/<lat>.js`).
The list of supported class are based on the processed data.
For example, using [OSMNames full data set](https://github.com/OSMNames/OSMNames/releases/tag/v2.0.4) contains [these values](https://github.com/OSMNames/OSMNames/blob/v2.0.4/osmnames/export_osmnames/functions.sql): `highway`, `waterway`, `natural`, `boundary`, `place`, `landuse` and `multiple`.

# Input data.tsv format

This service accepts only TSV file named `data.tsv` (or gzip-ed version named `data.tsv.gz`)
 with the specific order of columns:

```
name
alternative_names
osm_type
osm_id
class
type
lon
lat
place_rank
importance
street
city
county
state
country
country_code
display_name
west
south
east
north
wikidata
wikipedia
housenumbers
```

The source data should be **sorted by the column `importance`**, and include a header row.
For the description of these columns, see [data format in OSMNames documentation](http://osmnames.readthedocs.io/en/latest/introduction.html#output-format).

If no data is specified then a 100k OSMNames sample is automatically downloaded from from [OSMNames/OSMNames](https://github.com/OSMNames/OSMNames/releases/tag/v2.0.4).

# Usage of docker image

This docker image consists of our OSMNames Websearch (REST API), SphinxSearch and nginx.

The whole service can be run from command-line with one command:

```
docker run -d --name klokantech-osmnames-sphinxsearch -p 80:80 klokantech/osmnames-sphinxsearch
```

You can attach your file `data.tsv` (or `data.tsv.gz`), which has to be located in the internal path `/data/input/data.tsv` (or `/data/input/data.tsv.gz`):

```
docker run -d --name klokantech-osmnames-sphinxsearch \
    -v /path/to/folder/:/data/input/ \
    -p 80:80 \
    klokantech/osmnames-sphinxsearch
```

This file will be indexed on the first run or if index files are missing.

You can specify a path for index folder as well:

```
docker run -d --name klokantech-osmnames-sphinxsearch \
    -v /path/to/index/folder/:/data/index/ \
    -v /path/to/data/folder/:/data/input/ \
    -p 80:80 \
    klokantech/osmnames-sphinxsearch
```

You can attach your path with the following folder structure:

```
/path/to/folder/
    - input/
        - data.tsv (or data.tsv.gz)
    - index/
```

directly with simple command:

```
docker run -d -v /path/to/folder/:/data/ -p 80:80 klokantech/osmnames-sphinxsearch
```

# Index storage space

The SphinxSearch full-text search service requires indexing of the source data.
The index operation is required only for the first time or if the source data has been changed.
This operation takes longer on a source with more lines, and requires more space storage as well.

A demo sample data with 100 000 lines has **8.15 MiB gzip** source data file and requires storage space of **314 MiB for the index** folder. The operation takes (on average) 33 seconds.

The [full planet source data](https://github.com/OSMNames/OSMNames/releases/download/v2.0.3/planet-latest_geonames.tsv.gz) with 23 million lines requires storage space of **34 GiB for the index** folder. The operation takes (on average) 22 minutes.

The indexing is done automatically (if a particular index file is missing) via the `sphinx-reindex.sh` script. You can use this script to force run the index operation as well: `$ time bash sphinx-reindex.sh force`.
