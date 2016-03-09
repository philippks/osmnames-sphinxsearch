#!/bin/sh

sudo rm -rf tmp
mkdir -p data log tmp
# cp sample.tsv data/

docker stop osmnames-sphinxsearch
docker rm osmnames-sphinxsearch
docker build -t klokantech/osmnames-sphinxsearch:devel .
docker run -d --name osmnames-sphinxsearch \
    -p 9001:80 \
    -v `pwd`/data/:/data/ \
    -v `pwd`/tmp/:/tmp/ \
    klokantech/osmnames-sphinxsearch:devel
