#!/bin/sh -e
mkdir -p /data/index/
cp /sample.tsv /data/
# Index files
/usr/bin/indexer -c /etc/sphinx/sphinx.conf --rotate --all
# Start sphinx job in supervisor
supervisorctl -c /etc/supervisor/supervisord.conf start sphinx
