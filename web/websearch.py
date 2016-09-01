#!/usr/bin/env python
# -*- coding: utf-8 -*-
# WebSearch gate for OSMNames-SphinxSearch
#
# Copyright (C) 2016 Klokan Technologies GmbH (http://www.klokantech.com/)
#   All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Author: Martin Mikita (martin.mikita @ klokantech.com)
# Date: 15.07.2016

from flask import Flask, request, Response, render_template, url_for
from sphinxapi import *
from pprint import pprint, pformat
from json import dumps
from os import getenv
from time import time
import requests
import sys
import MySQLdb
import re

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
"""
Process query to Sphinx searchd with mysql
"""
def process_query_mysql(index, query, query_filter, start=0, count=0):
    global SEARCH_MAX_COUNT, SEARCH_DEFAULT_COUNT
    # default server configuration
    host = '127.0.0.1'
    port = 9306
    if getenv('WEBSEARCH_SERVER'):
        host = getenv('WEBSEARCH_SERVER')
    if getenv('WEBSEARCH_SERVER_PORT'):
        port = int(getenv('WEBSEARCH_SERVER_PORT'))

    try:
        db = MySQLdb.connect(host=host, port=port, user='root')
        cursor = db.cursor()
    except Exception as ex:
        result = {
            'total_found': 0,
            'matches': [],
            'message': str(ex),
            'status': False,
            'count': 0,
            'startIndex': start,
        }
        return False, result

    if count == 0:
        count = SEARCH_DEFAULT_COUNT
    count = min(SEARCH_MAX_COUNT, count)

    argsFilter = []
    whereFilter = []

    # Prepare query
    whereFilter.append('MATCH(%s)')
    argsFilter.append(query)

    # Prepare filter for query
    for f in ['class', 'type', 'street', 'city', 'county', 'state', 'country_code', 'country']:
        if query_filter[f] is None:
            continue
        inList = []
        for val in query_filter[f]:
            argsFilter.append(val)
            inList.append('%s')
        # Creates where condition: f in (%s, %s, %s...)
        whereFilter.append('{} in ({})'.format(f, ', '.join(inList)))

    # Prepare viewbox filter
    if 'viewbox' in query_filter and query_filter['viewbox'] is not None:
        bbox = query_filter['viewbox'].split(',')
        # latitude, south, north
        whereFilter.append('({:.12f} < lat AND lat < {:.12f})'
            .format(float(bbox[0]), float(bbox[2])))
        # longtitude, west, east
        whereFilter.append('({:.12f} < lon AND lon < {:.12f})'
            .format(float(bbox[1]), float(bbox[3])))

    sortBy = []
    # Prepare sorting by custom or default
    if query_filter['sortBy'] is not None:
        for attr in query_filter['sortBy']:
            attr = attr.split('-')
            # List of supported sortBy columns - to prevent SQL injection
            if attr[0] not in ('class', 'type', 'street', 'city',
                'county', 'state', 'country_code', 'country',
                'importance' 'weight', 'id'):
                print >> sys.stderr, 'Invalid sortBy column ' + attr[0]
                continue
            asc = 'ASC'
            if len(attr) > 1 and (attr[1] == 'desc' or attr[1] == 'DESC'):
                asc = 'DESC'
            sortBy.append('{} {}'.format(attr[0], asc))

    if len(sortBy) == 0:
        sortBy.append('weight DESC')

    # Field weights and other options
    # ranker=expr('sum(lcs*user_weight)*1000+bm25') == SPH_RANK_PROXIMITY_BM25
    # ranker=expr('sum((4*lcs+2*(min_hit_pos==1)+exact_hit)*user_weight)*1000+bm25') == SPH_RANK_SPH04
    # ranker=expr('sum((4*lcs+2*(min_hit_pos==1)+100*exact_hit)*user_weight)*1000+bm25') == SPH_RANK_SPH04 boosted with exact_hit
    # select @weight+IF(fieldcrc==$querycrc,10000,0) AS weight
    # options:
    #  - 'cutoff' - integer (max found matches threshold)
    #  - 'max_matches' - integer (per-query max matches value), default 1000
    #  - 'max_query_time' - integer (max search time threshold, msec)
    #  - 'retry_count' - integer (distributed retries count)
    #  - 'retry_delay' - integer (distributed retry delay, msec)
    option = "field_weights = (name = 100, display_name = 1)"
    option += ", retry_count = 2, retry_delay = 500, max_matches = 200, max_query_time = 20000"
    option += ", ranker=expr('sum((10*lcs+5*exact_order+10*exact_hit+5*wlccs)*user_weight)*1000+bm25')"
    # Prepare query for boost
    query_elements = re.compile("\s*,\s*|\s+").split(query)
    select_boost = []
    argsBoost = []
    # Boost whole query (street with spaces)
    # select_boost.append('IF(name=%s,1000000,0)')
    # argsBoost.append(re.sub(r"\**", "", query))
    # Boost each query part delimited by space
    # for qe in query_elements:
    #    select_boost.append('IF(name=%s,1000000,0)')
    #    argsBoost.append(re.sub(r"\**", "", qe))

    # Prepare SELECT
    sql = "SELECT WEIGHT()*importance+{} as weight, * FROM {} WHERE {} ORDER BY {} LIMIT %s, %s OPTION {};".format(
        '+'.join(select_boost),
        index,
        ' AND '.join(whereFilter),
        ', '.join(sortBy),
        option
    )

    status = True
    result = {
        'total_found': 0,
        'matches': [],
        'message': None,
    }

    try:
        args = argsBoost + argsFilter + [start, count]
        q = cursor.execute(sql, args)
        pprint([sql, args, cursor._last_executed, q])
        desc = cursor.description
        matches = []
        for row in cursor:
            match = {
                'weight' : 0,
                'attrs' : {},
                'id' : 0,
            }
            for (name, value) in zip(desc, row):
                col = name[0]
                if col == 'id':
                    match['id'] = value
                elif col == 'weight':
                    match['weight'] = value
                else:
                    match['attrs'][col] = value
            matches.append(match)
        # ~ for row in cursor
        result['matches'] = matches

        q = cursor.execute('SHOW META LIKE %s', ('total_found',))
        for row in cursor:
            result['total_found'] = row[1]
    except Exception as ex:
        status = False
        result['message'] = str(ex)

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
    if 'message' in result and result['message']:
        response['message'] = result['message']

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
    resp = Response(json, mimetype=mime)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp, code


# ---------------------------------------------------------
"""
Modify query - add asterisk for each element of query, set original query
"""
def modify_query_autocomplete(orig_query):
    query = '* '.join(re.compile("\s*,\s*|\s+").split(orig_query)) + '*'
    query = re.sub(r"\*+", "*", query)
    return query, orig_query

"""
Modify query - use and set original
"""
def modify_query_orig(orig_query):
    return orig_query, orig_query

"""
Modify query - remove house number, use and set modified query
"""
def modify_query_remhouse(orig_query):
    # Remove any number from the request
    query = re.sub(r"\d+([/, ]\d+)?", "", orig_query)
    if query == orig_query:
        return None, orig_query
    return query, query

"""
Modify query - split query elements as OR, use modified and set original query
"""
def modify_query_splitor(orig_query):
    if orig_query.startswith('@'):
        return None, orig_query
    query = ' | '.join(re.compile("\s*,\s*|\s+").split(orig_query))
    if query == orig_query:
        return None, orig_query
    return query, orig_query


# ---------------------------------------------------------
"""
Global searching
"""
@app.route('/')
def search():
    data = {'query': '', 'route': '/', 'template': 'answer.html'}
    layout = request.args.get('layout')
    if layout and layout in ('answer', 'home'):
        data['template'] = request.args.get('layout') + '.html'
    code = 400

    q = request.args.get('q')
    autocomplete = request.args.get('autocomplete')
    debug = request.args.get('debug')
    pprint([q, autocomplete, debug])

    times = {}
    if debug:
        times['start'] = time()

    query_filter = {
        'type': None, 'class': None,
        'street': None, 'city' : None,
        'county': None, 'state': None,
        'country': None, 'country_code': None,
        'viewbox': None,
        'sortBy': None,
    }
    filter = False
    for f in query_filter:
        if request.args.get(f):
            v = None
            # Some arguments may be list
            if f in ('type', 'class', 'city', 'county', 'country_code', 'sortBy', 'tags'):
                vl = request.args.getlist(f)
                if len(vl) == 1:
                    v = vl[0].encode('utf-8')
                    # This argument can be list separated by comma
                    v = v.split(',')
                elif len(vl) > 1:
                    v = [x.encode('utf-8') for x in vl]
            if v is None:
                vl = request.args.get(f)
                v = vl.encode('utf-8')
            query_filter[f] = v
            filter = True

    if not q and not filter:
        # data['result'] = {'error': 'Missing query!'}
        return render_template('home.html', route='/')

    data['query'] = q.encode('utf-8')

    start = 0
    count = 0
    if request.args.get('startIndex'):
        start = int(request.args.get('startIndex'))
    if request.args.get('count'):
        count = int(request.args.get('count'))

    data['url'] = request.url

    orig_query = data['query']

    if debug:
        times['prepare'] = time() - times['start']

    index_modifiers = []
    if autocomplete:
        index_modifiers.append( ('ind_name_prefix', modify_query_autocomplete) )
    index_modifiers.append( ('ind_name_prefix', modify_query_orig) )
    index_modifiers.append( ('ind_name_prefix', modify_query_remhouse, orig_query) )
    if autocomplete:
        index_modifiers.append( ('ind_name_infix', modify_query_autocomplete) )
    index_modifiers.append( ('ind_name_infix', modify_query_orig) )
    index_modifiers.append( ('ind_name_infix', modify_query_remhouse, orig_query) )
    if autocomplete:
        index_modifiers.append( ('ind_name_prefix_soundex', modify_query_autocomplete) )
        index_modifiers.append( ('ind_name_infix_soundex', modify_query_autocomplete) )
    index_modifiers.append( ('ind_name_prefix_soundex', modify_query_orig) )
    index_modifiers.append( ('ind_name_prefix_soundex', modify_query_remhouse, orig_query) )
    # We want first to try soundex, then splitor modifier for both index
    index_modifiers.append( ('ind_name_prefix', modify_query_splitor) )
    index_modifiers.append( ('ind_name_prefix_soundex', modify_query_splitor) )
    if debug:
        pprint(index_modifiers)

    rc = False
    result = {}
    proc_query = orig_query
    # Pair is (index, modify_function, [orig_query])
    for pair in index_modifiers:
        index = pair[0]
        modify = pair[1]
        if len(pair) >= 3:
            proc_query = pair[2]
        if debug and index not in times:
            times[index] = {}
        # Cycle through few modifications of query
        # Modification function return query with original query (possibly modified) used for the following processing
        query, proc_query = modify(proc_query)
        # No modification has been done
        if query is None:
            continue
        # Process modified query
        if debug:
            times['start_query'] = time()
        rc, result = process_query_mysql(index, query, query_filter, start, count)
        if debug:
            times[index][modify.__name__] = time() - times['start_query']
        if rc and len(result['results']) > 0:
            result['modify'] = modify.__name__
            result['query_succeed'] = query.decode('utf-8')
            result['index_succeed'] = index.decode('utf-8')
            break

    if rc:
        code = 200

    data['query'] = orig_query.decode('utf-8')
    if debug:
        times['process'] = time() - times['start']
        result['times'] = times
    data['result'] = result
    data['autocomplete'] = autocomplete
    data['debug'] = debug
    args = dict(request.args)
    if 'layout' in args:
        del(args['layout'])
    data['url_home'] = url_for('search', layout='home', **args)
    return formatResponse(data, code)


# ---------------------------------------------------------
"""
Homepage (content only for debug)
"""
# @app.route('/')
# def home():
#     return render_template('home.html', route='/search')



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
Custom template filters
"""
@app.template_filter()
def ppretty(value):
    return pformat(value)

"""
Main launcher
"""
if __name__ == '__main__':
        app.run(threaded=False, host='0.0.0.0', port=8000)

