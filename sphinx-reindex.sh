#!/bin/sh

set -e

# Copy sample file if missing
if [ ! -f /data/input/data.tsv ]; then
    mkdir -p /data/input/
    cp /sample.tsv /data/input/data.tsv
fi

# Index files, only if not exists, or forced by the script
if [ ! -f /data/index/ind_name_prefix.spa -o "$1" = "force" ]; then
    mkdir -p /data/index/
    /usr/bin/indexer -c /etc/sphinxsearch/sphinx.conf --rotate --all
    touch /tmp/osmnames-sphinxsearch-data.timestamp
fi

# Start sphinx job in supervisor
if [ -z "`pidof searchd`" ]; then
    supervisorctl -c /etc/supervisor/supervisord.conf start sphinx
fi
