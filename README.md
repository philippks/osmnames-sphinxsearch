# osmnames-sphinxsearch

Nominatim JSON API replacement made with osmnames.org data indexed by sphinx search

Using data from https://github.com/geometalab/OSMNames - Database of geographic place names from OpenStreetMap for full text search downloadable for free. Website: http://osmnames.org


# REST API

## Search for autocomplete: `/q/<query>.js`

This endpoint returns 20 results matching the `<query>`.


## Country specific search for autocomplete `/<country_code>/q/<query>.js`

This endpoint returns 20 results matching the `<query>` within a specific country, identified by the `<country_code` (lowercase ISO 3166 Alpha-2 code).


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
```

The source data should be **sorted by the column `importance`**.
For the description of these columns, see [data format in geometalab/OSMNames repository](https://github.com/geometalab/OSMNames#data-format-of-tsv-export-of-osmnames).


# Usage of docker image

This docker image consists from internaly connected and setup OSMNames Websearch (REST API), SphinxSearch and nginx.

Whole service can be run from command-line with one command:

Run with demo data (sample of 100k lines from [geometalab/OSMNames](https://github.com/OSMNames/OSMNames/releases/tag/v1.1)) only

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

The service for full-text search SphinxSearch requires indexing a source data.
The index operation is required only for the first time or if source data has been changed.
This operation takes longer on a source with more lines, and requires more space storage as well.

A demo sample data with 100 000 lines has **9.3 MiB gzip**-ed source data file and requires storage space of **133.8 MiB for the index** folder. The operation tooks in an average 15 seconds.

The [full planet source data](https://github.com/OSMNames/OSMNames/releases/download/v1.1/planet-latest.tsv.gz) with 21 million lines requires storage space of **27.4 GiB for the index** folder. The operation tooks in an average 48 minutes.

The index operation is done automatically if certain the index file is missing via the prepared script `sphinx-reindex.sh`. You can use this script to force index operation as well: `$ time bash sphinx-reindex.sh force`.
