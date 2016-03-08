#!/bin/sh -e
# Copy sample file if missing
if [ ! -f /data/input/data.tsv ]; then
    cp /sample.tsv /data/input/data.tsv
fi

# Index files, only if not exists
if [ ! -d /data/index ]; then
    mkdir -p /data/index/
    /usr/bin/indexer -c /etc/sphinx/sphinx.conf --rotate --all
fi

# Start sphinx job in supervisor
supervisorctl -c /etc/supervisor/supervisord.conf start sphinx
