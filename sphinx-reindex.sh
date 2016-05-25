#!/bin/sh -e
# Copy sample file if missing
if [ ! -f /data/input/data.tsv ]; then
    mkdir -p /data/input/
    cp /sample.tsv /data/input/data.tsv
fi

# Index files, only if not exists
if [ ! -f /data/index/ind_name.spa ]; then
    mkdir -p /data/index/
    /usr/bin/indexer -c /etc/sphinxsearch/sphinx.conf --rotate --all
fi

# Start sphinx job in supervisor
if [ -z "`pidof searchd`" ]; then
    supervisorctl -c /etc/supervisor/supervisord.conf start sphinx
fi
