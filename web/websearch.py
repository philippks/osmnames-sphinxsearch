#!/usr/bin/env python
# -*- coding: utf-8 -*-
# WebSearch gate for SphinxSearch
#
# Copyright (C) 2016 Klokan Technologies GmbH (http://www.klokantech.com/)
#   All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Author: Martin Mikita (martin.mikita @ klokantech.com)
# Date: 01.03.2016

from flask import Flask, request, Response, render_template
from sphinxapi import *
from pprint import pprint, pformat
from json import dumps
from os import getenv

app = Flask(__name__, template_folder='templates/')
app.debug = not getenv('WEBSEARCH_DEBUG') is None
app.debug = True


# Return maximal number of results
SEARCH_MAX_COUNT = 100
SEARCH_DEFAULT_COUNT = 20
if getenv('SEARCH_MAX_COUNT'):
    SEARCH_MAX_COUNT = int(getenv('SEARCH_MAX_COUNT'))
if getenv('SEARCH_DEFAULT_COUNT'):
    SEARCH_DEFAULT_COUNT = int(getenv('SEARCH_DEFAULT_COUNT'))



# ---------------------------------------------------------
"""
Process query to Sphinx searchd
"""
def process_query(index, query, query_filter, start=0, count=0):
    # default server configuration
    host = 'localhost'
    port = 9312
    if getenv('WEBSEARCH_SERVER'):
        host = getenv('WEBSEARCH_SERVER')
    if getenv('WEBSEARCH_SERVER_PORT'):
        port = int(getenv('WEBSEARCH_SERVER_PORT'))
    pprint([host, port, getenv('WEBSEARCH_SERVER')])

    if count == 0:
        count = SEARCH_DEFAULT_COUNT
    count = min(SEARCH_MAX_COUNT, count)

    repeat = 3
    result = None
    # Repeate 3 times request because of socket.timeout
    while repeat > 0:
        try:
            cl = SphinxClient()
            cl.SetServer(host, port)
            cl.SetConnectTimeout(2.0) # float seconds
            cl.SetLimits(start, count) #offset, limit, maxmatches=0, cutoff=0
            # cl.SetRankingMode(SPH_RANK_SPH04)
            # Ranker - SPH04 with boosted exact hit
            cl.SetRankingMode(SPH_RANK_EXPR, '(sum((4*lcs+2*(min_hit_pos==1)+100*exact_hit)*user_weight)*100+bm25)*importance')
            # cl.SetMatchMode(SPH_MATCH_EXTENDED2) # default setting
            cl.SetSortMode(SPH_SORT_EXTENDED, '@relevance DESC, importance DESC')
            cl.SetFieldWeights({
                'name': 500,
                'display_name': 1,
            })

            # Prepare filter for query, except tags
            for f in ['class', 'type', 'street', 'city', 'county', 'state',
                      'country_code', 'country']:
                if f not in query_filter or query_filter[f] is None:
                    continue
                cl.SetFilterString(f, query_filter[f])

            if 'viewbox' in query_filter and query_filter['viewbox'] is not None:
                bbox = query_filter['viewbox'].split(',')
                # latitude, south, north
                lat = [float(bbox[0]), float(bbox[2])]
                # longtitude, west, east
                lon = [float(bbox[1]), float(bbox[3])]
                # Filter on lon lat now
                cl.SetFilterFloatRange('lon', lon[0], lon[1])
                cl.SetFilterFloatRange('lat', lat[0], lat[1])

            pprint(query)

            # Process query under index
            result = cl.Query ( query, index )
            repeat = 0

        except socket.timeout:
            repeat -= 1

    status = True
    if not result:
        result = {
            'message': cl.GetLastError(),
            'total_found': 0,
            'matches': [],
        }
        status = False

    result['count'] = count
    result['startIndex'] = start
    result['status'] = status

    return status, prepareResultJson(result, query_filter)


# ---------------------------------------------------------
def prepareResultJson(result, query_filter):
    from pprint import pprint

    response = {
        'results': [],
        'startIndex': result['startIndex'],
        'count': result['count'],
        'totalResults': result['total_found'],
    }

    for row in result['matches']:
        r = row['attrs']
        res = {'rank': row['weight'], 'id': row['id']}
        for attr in r:
            if isinstance(r[attr], str):
                res[attr] = r[attr].decode('utf-8')
            else:
                res[ attr ] = r[attr]
        # res['boundingbox'] = "{}, {}, {}, {}".format(r['north'], r['south'], r['east'], r['west'])
        res['boundingbox'] = [res['west'], res['south'], res['east'], res['north']]
        del res['west']
        del res['south']
        del res['east']
        del res['north']
        # Empty values for KlokanTech NominatimMatcher JS
        # res['address'] = {
        #     'country_code': '',
        #     'country': '',
        #     'city': None,
        #     'town': None,
        #     'village': None,
        #     'hamlet': rr['name'],
        #     'suburb': '',
        #     'pedestrian': '',
        #     'house_number': '1'
        # }
        response['results'].append(res)

    # Prepare next and previous index
    nextIndex = result['startIndex'] + result['count']
    if nextIndex <= result['total_found']:
        response['nextIndex'] = nextIndex
    prevIndex = result['startIndex'] - result['count']
    if prevIndex >= 0:
        response['previousIndex'] = prevIndex

    return response



# ---------------------------------------------------------
"""
Format response output
"""
def formatResponse(data, code=200):
    # Format json - return empty
    result = data['result'] if 'result' in data else {}
    format = 'json'
    if request.args.get('format'):
        format = request.args.get('format')
    if 'format' in data:
        format = data['format']

    tpl = data['template'] if 'template' in data else 'answer.html'
    if format == 'html' and tpl is not None:
        if not 'route' in data:
            data['route'] = '/'
        return render_template(tpl, rc=(code == 200), **data), code

    json = dumps( result )
    mime = 'application/json'
    # Append callback for JavaScript
    if request.args.get('json_callback'):
        json = request.args.get('json_callback') + "("+json+");";
        mime = 'application/javascript'
    if request.args.get('callback'):
        json = request.args.get('callback') + "("+json+");";
        mime = 'application/javascript'
    return Response(json, mimetype=mime), code



# ---------------------------------------------------------
"""
Searching for display name
"""
@app.route('/displayName')
def displayName():
    ret = {}
    code = 400
    index = 'ind_name'
    q = request.args.get('q')
    if not q.startswith('@'):
        q = '@display_name ' + q
    data = {'query': q, 'index': index, 'route': '/displayName', 'template': 'answer.html'}
    rc, result = process_query(index, q)
    if rc:
        code = 200
    data['result'] = result
    return formatResponse(data, code)



# ---------------------------------------------------------
"""
Global searching
"""
@app.route('/search')
def search():
    data = {'query': '', 'route': '/search', 'template': 'answer.html'}
    code = 400

    index = 'search_index'
    q = request.args.get('q')

    query_filter = {
        'type': None, 'class': None,
        'street': None, 'city' : None,
        'county': None, 'state': None,
        'country_code': None, 'viewbox': None,
    }
    filter = False
    for f in query_filter:
        if request.args.get(f):
            v = request.args.get(f)
            query_filter[f] = v.encode('utf-8')
            filter = True

    if not q and not filter:
        data['result'] = {'error': 'Missing query!'}
        return formatResponse(data, 404)

    data['query'] = q.encode('utf-8')

    start = 0
    count = 0
    if request.args.get('startIndex'):
        start = int(request.args.get('startIndex'))
    if request.args.get('count'):
        count = int(request.args.get('count'))

    data['url'] = request.url

    rc, result = process_query(index, data['query'], query_filter, start, count)

    data['query'] = data['query'].decode('utf-8')
    if rc and len(result['results']) == 0: # and not data['query'].startswith('@')
        pattern = re.compile("\s*,\s*|\s+")
        query = pattern.split(data['query'])
        query2 = ' | '.join(query)
        rc, result = process_query(index, query2, query_filter, start, count)

    if rc:
        code = 200

    data['result'] = result

    return formatResponse(data, code)


# ---------------------------------------------------------
"""
Homepage (content only for debug)
"""
@app.route('/')
def home():
    return render_template('home.html', route='/search')



# ---------------------------------------------------------
"""
Custom template filters
"""
@app.template_filter()
def nl2br(value):
    if isinstance(value, dict):
        for key in value:
            value[key] = nl2br(value[key])
        return value
    elif isinstance(value, str):
        return value.replace('\n', '<br>')
    else:
        return value

"""
Main launcher
"""
if __name__ == '__main__':
        app.run(threaded=False, host='0.0.0.0', port=8000)

