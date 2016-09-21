# osmnames-sphinxsearch

Nominatim JSON API replacement made with osmnames.org data indexed by sphinx search

Using data from https://github.com/geometalab/OSMNames - Database of geographic place names from OpenStreetMap for full text search downloadable for free. Website: http://osmnames.org


# REST API

## Search for autocomplete: `/q/<query>.js`

This endpoint returns 20 results matching the `<query>`.


## Country specific search for autocomplete `/<country_code>/q/<query>.js`

This endpoint returns 20 results matching the `<query>` within a specific country, identified by the `<country_code` (lowercase ISO 3166 Alpha-2 code).


# Input data.tsv format

This service accepts only TSV file named `data.tsv` with the specific order of columns:

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
```

For the description of these columns, see [data format in geometalab/OSMNames repository](https://github.com/geometalab/OSMNames#data-format-of-tsv-export-of-osmnames).


# Usage of docker image

This docker image consists from internaly connected and setup OSMNames Websearch (REST API), SphinxSearch and nginx.

Whole service can be run from command-line with one command:

Run with demo data (10 lines) only

```
docker run -d --name klokantech-osmnames-sphinxsearch -p 80:80 klokantech/osmnames-sphinxsearch
```

You can attach your file `data.tsv`, which has to be located in the internal path `/data/input/data.tsv`:

```
docker run -d --name klokantech-osmnames-sphinxsearch \
    -v /path/to/folder/data.tsv:/data/input/ \
    -p 80:80 \
    klokantech/osmnames-sphinxsearch
```

This file will be indexed on the first run, or if index files are missing.
You can specify path for index folder as well:

```
docker run -d --name klokantech-osmnames-sphinxsearch \
    -v /path/to/index/folder/:/data/index/ \
    -v /path/to/data/folder/:/data/input/ \
    -p 80:80 \
    klokantech/osmnames-sphinxsearch
```

You can attach your path with the following folder structure directly with easier command:

```
/path/to/folder/
    - input/
        - data.tsv
    - index/
```

```
docker run -d --name klokantech-osmnames-sphinxsearch \
    -v /path/to/folder/:/data/ \
    -p 80:80 \
    klokantech/osmnames-sphinxsearch
```
