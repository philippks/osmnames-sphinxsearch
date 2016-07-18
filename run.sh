#!/bin/sh

# cp sample.tsv data/

SOURCE_DIR=/data/osmnames-sphinxsearch
mkdir -p $SOURCE_DIR/data $SOURCE_DIR/tmp
sudo rm -rf $SOURCE_DIR/tmp

docker stop osmnames-sphinxsearch
docker rm osmnames-sphinxsearch
docker build -t klokantech/osmnames-sphinxsearch:devel .
docker run -d --name osmnames-sphinxsearch \
    -p 9013:80 -p 9313:9312 \
    -v `pwd`/web/:/usr/local/src/websearch/ \
    -v $SOURCE_DIR/data/:/data/ \
    -v $SOURCE_DIR/tmp/:/tmp/ \
    klokantech/osmnames-sphinxsearch:devel
