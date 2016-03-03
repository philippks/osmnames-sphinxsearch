FROM debian:8

RUN apt-get -qq update && apt-get install -qq -y --no-install-recommends \
    ca-certificates \
    curl \
    libexpat1 \
    libpq5 \
    mysql-client \
    nginx \
    python \
    python-setuptools \
    python-shapely \
    python-pip \
    python-crypto \
    python-flask \
    python-shapely \
    python-pil \
    unixodbc \
    uwsgi \
    uwsgi-plugin-python

RUN curl -s \
    http://sphinxsearch.com/files/sphinxsearch_2.2.9-release-1~wheezy_amd64.deb \
    -o /tmp/sphinxsearch.deb \
&& dpkg -i /tmp/sphinxsearch.deb \
&& rm /tmp/sphinxsearch.deb \
&& easy_install -q flask-cache \
&& pip install -q supervisor \
&& mkdir -p /var/log/sphinx \
&& mkdir -p /var/log/supervisord

COPY conf/sphinx/*.conf /etc/sphinx/
COPY conf/nginx/nginx.conf /etc/nginx/sites-available/default
COPY supervisor/*.conf /etc/supervisor/conf.d/
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY web /usr/local/src/websearch
COPY sample.tsv /
COPY sphinx-reindex.sh /

ENV SPHINX_PORT 9312

EXPOSE 80
CMD ["/usr/local/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
