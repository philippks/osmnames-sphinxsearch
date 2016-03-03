#!/bin/sh -e
cp /sample.tsv /data/
mkdir -p /data/index/
# Index files
/usr/bin/indexer -c /etc/sphinx/sphinx.conf --rotate --all
# Start sphinx job in supervisor
supervisorctl -c /etc/supervisor/supervisord.conf start sphinx
