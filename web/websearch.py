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

from flask import Flask, request, Response, render_template, url_for, redirect
from pprint import pprint, PrettyPrinter
from json import dumps
from os import getenv, path, utime
from time import time, mktime
from datetime import datetime
import sys
import MySQLdb
import re
import natsort
import rfc822   # Used for parsing RFC822 into datetime
import email    # Used for formatting TS into RFC822


# Prepare global variables
SEARCH_MAX_COUNT = 100
SEARCH_DEFAULT_COUNT = 20
if getenv('SEARCH_MAX_COUNT'):
    SEARCH_MAX_COUNT = int(getenv('SEARCH_MAX_COUNT'))
if getenv('SEARCH_DEFAULT_COUNT'):
    SEARCH_DEFAULT_COUNT = int(getenv('SEARCH_DEFAULT_COUNT'))

TMPFILE_DATA_TIMESTAMP = "/tmp/osmnames-sphinxsearch-data.timestamp"

NOCACHEREDIRECT = False
if getenv('NOCACHEREDIRECT'):
    NOCACHEREDIRECT = getenv('NOCACHEREDIRECT')

# Prepare global variable for Last-modified Header
try:
    mtime = path.getmtime(TMPFILE_DATA_TIMESTAMP)
except OSError:
    with open(TMPFILE_DATA_TIMESTAMP, 'a'):
        utime(TMPFILE_DATA_TIMESTAMP, None)
    mtime = time()
DATA_LAST_MODIFIED = email.utils.formatdate(mtime, usegmt=True)

# Filter attributes values
# dict[ attribute ] = list(values)
CHECK_ATTR_FILTER = ['country_code', 'class']
ATTR_VALUES = {}


app = Flask(__name__, template_folder='templates/')
app.debug = not (getenv('WEBSEARCH_DEBUG') is None)


# ---------------------------------------------------------
def get_db_cursor():
    # connect to the mysql server
    # default server configuration
    host = '127.0.0.1'
    port = 9306
    if getenv('WEBSEARCH_SERVER'):
        host = getenv('WEBSEARCH_SERVER')
    if getenv('WEBSEARCH_SERVER_PORT'):
        port = int(getenv('WEBSEARCH_SERVER_PORT'))

    db = MySQLdb.connect(host=host, port=port, user='root')
    cursor = db.cursor()
    return db, cursor


def get_query_result(cursor, sql, args):
    """
    Get result from SQL Query.

    Boolean, {'matches': [{'weight': 0, 'id', 'attrs': {}}], 'total_found': 0}
    """
    status = False
    result = {
        'matches': [],
        'status': False,
        'total_found': 0,
    }
    try:
        q = cursor.execute(sql, args)  # noqa
        # pprint([sql, args, cursor._last_executed, q])
        desc = cursor.description
        matches = []
        status = True
        for row in cursor:
            match = {
                'weight': 0,
                'attrs': {},
                'id': 0,
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

        cursor.execute('SHOW META LIKE %s', ('total_found',))
        for row in cursor:
            result['total_found'] = int(row[1])
    except Exception as ex:
        result['message'] = str(ex)

    result['status'] = status
    return status, result


# ---------------------------------------------------------
def get_attributes_values(index, attributes):
    """
    Get attributes distinct values, using data from index.

    dict[ attribute ] = list(values)
    """
    global ATTR_VALUES

    try:
        db, cursor = get_db_cursor()
    except Exception as ex:
        print(str(ex))
        return False

    # Loop over attributes
    if isinstance(attributes, str):
        attributes = [attributes, ]

    for attr in attributes:
        # clear values
        ATTR_VALUES[attr] = []
        count = 200
        total_found = 0
        # get attributes values for index
        sql_query = 'SELECT {} FROM {} GROUP BY {} LIMIT {}, {}'
        sql_meta = 'SHOW META LIKE %s'
        found = 0
        try:
            while total_found == 0 or found < total_found:
                cursor.execute(sql_query.format(attr, index, attr, found, count), ())
                for row in cursor:
                    found += 1
                    ATTR_VALUES[attr].append(str(row[0]))
                if total_found == 0:
                    cursor.execute(sql_meta, ('total_found',))
                    for row in cursor:
                        total_found = int(row[1])
                        # Skip this attribute, if total found is more than max_matches
                        if total_found > 1000:
                            del(ATTR_VALUES[attr])
                            found = total_found
            if found == 0:
                del(ATTR_VALUES[attr])
        except Exception as ex:
            db.close()
            print(str(ex))
            return False

    db.close()
    return True


# ---------------------------------------------------------
def process_search_index(index, query, query_filter, start=0, count=0, field_weights=''):
    """Process query to Sphinx searchd with mysql."""
    if count == 0:
        count = SEARCH_DEFAULT_COUNT
    count = min(SEARCH_MAX_COUNT, count)

    status = True
    result = {
        'total_found': 0,
        'matches': [],
        'message': None,
        'start_index': start,
        'count': count,
        'status': status,
    }

    try:
        db, cursor = get_db_cursor()
    except Exception as ex:
        status = False
        result['message'] = str(ex)
        result['status'] = status
        return status, result

    argsFilter = []
    whereFilter = []

    # Prepare filter for query
    for f in ['class', 'type', 'street', 'city', 'county', 'state', 'country_code', 'country']:
        if f not in query_filter or query_filter[f] is None:
            continue
        inList = []
        for val in query_filter[f]:
            if f in ATTR_VALUES and val not in ATTR_VALUES[f]:
                status = False
                result['message'] = 'Invalid attribute value.'
                result['status'] = status
                return status, result
            argsFilter.append(val)
            inList.append('%s')
        # Creates where condition: f in (%s, %s, %s...)
        whereFilter.append('{} in ({})'.format(f, ', '.join(inList)))

    # Prepare viewbox filter
    if 'viewbox' in query_filter and query_filter['viewbox'] is not None:
        bbox = query_filter['viewbox'].split(',')
        # latitude, south, north
        whereFilter.append('({:.12f} < lat AND lat < {:.12f})'.format(
            float(bbox[0]), float(bbox[2])))
        # longtitude, west, east
        whereFilter.append('({:.12f} < lon AND lon < {:.12f})'.format(
            float(bbox[1]), float(bbox[3])))

    # MATCH query should be last in the WHERE condition
    # Prepare query
    whereFilter.append('MATCH(%s)')
    argsFilter.append(query)

    sortBy = []
    # Prepare sorting by custom or default
    if 'sortBy' in query_filter and query_filter['sortBy'] is not None:
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
    option = "retry_count = 2, retry_delay = 500, max_matches = 200, max_query_time = 20000"
    option += ", cutoff = 2000"
    option += ", ranker=expr('sum((10*lcs+5*exact_order+10*exact_hit+5*wlccs)*user_weight)*1000+bm25')"
    if len(field_weights) > 0:
        option += ", field_weights = ({})".format(field_weights)
    # Prepare query for boost
    query_elements = re.compile("\s*,\s*|\s+").split(query)
    select_boost = []
    argsBoost = []
    # Boost whole query (street with spaces)
    # select_boost.append('IF(name=%s,1000000,0)')
    # argsBoost.append(re.sub(r"\**", "", query))
    # Boost each query part delimited by space
    # Only if there is more than 1 query elements
    if False and len(query_elements) > 1:
        for qe in query_elements:
            select_boost.append('IF(name=%s,1000000,0)')
            argsBoost.append(re.sub(r"\**", "", qe))

    # Prepare SELECT
    sql = "SELECT WEIGHT()*importance+{} as weight, * FROM {} WHERE {} ORDER BY {} LIMIT %s, %s OPTION {};".format(
        '+'.join(select_boost) if len(select_boost) > 0 else '0',
        index,
        ' AND '.join(whereFilter),
        ', '.join(sortBy),
        option
    )

    args = argsBoost + argsFilter + [start, count]
    status, result = get_query_result(cursor, sql, args)
    db.close()

    result['start_index'] = start
    result['count'] = count
    result['status'] = status
    return status, result


# ---------------------------------------------------------
def mergeResultObject(result_old, result_new):
    """
    Merge two result objects into one.

    Order matches by weight
    """
    # Merge matches
    weight_matches = {}
    unique_id = 0
    unique_ids_list = []

    for matches in [result_old['matches'], result_new['matches'], ]:
        for row in matches:
            if row['id'] in unique_ids_list:
                result_old['total_found'] -= 1  # Decrease total found number
                continue
            unique_ids_list.append(row['id'])
            weight = str(row['weight'])
            if weight in weight_matches:
                weight += '_{}'.format(unique_id)
                unique_id += 1
            weight_matches[weight] = row

    # Sort matches according to the weight and unique id
    sorted_matches = natsort.natsorted(weight_matches.items(), reverse=True)
    matches = []
    i = 0
    for row in sorted_matches:
        matches.append(row[1])
        i += 1
        # Append only first #count rows
        if 'count' in result_old and i >= result_old['count']:
            break

    result = result_old.copy()
    result['matches'] = matches
    result['total_found'] += result_new['total_found']
    if 'message' in result_new and result_new['message']:
        result['message'] = ', '.join(result['message'], result_new['message'])

    return result


# ---------------------------------------------------------
def prepareResultJson(result):
    """Prepare JSON from pure Result array from SphinxQL."""
    if 'start_index' not in result:
        result = {
            'start_index': 0,
            'count': 0,
            'total_found': 0,
            'matches': [],
        }

    response = {
        'results': [],
        'startIndex': result['start_index'],
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
                try:
                    res[attr] = r[attr].decode('utf-8')
                except:
                    res[attr] = r[attr]
            else:
                res[attr] = r[attr]
        # Prepare bounding box from West/South/East/North attributes
        if 'west' in res:
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
    next_index = result['start_index'] + result['count']
    if next_index <= result['total_found']:
        response['nextIndex'] = next_index
    prev_index = result['start_index'] - result['count']
    if prev_index >= 0:
        response['previousIndex'] = prev_index

    response['results'] = prepareNameSuffix(response['results'])

    return response


# ---------------------------------------------------------
def parseDisplayName(row):
    # commas = row['display_name'].count(',')
    parts = row['display_name'].split(', ')
    newrow = {}
    if len(parts) == 5:
        newrow['city'] = parts[1]
        newrow['state'] = parts[3]
        newrow['country'] = parts[4]
    if len(parts) == 6:
        newrow['city'] = parts[1]
        newrow['state'] = parts[4]
        newrow['county'] = parts[4]
        newrow['country'] = parts[5]

    for field in newrow:
        if field not in row:
            row[field] = newrow[field]
        if not row[field]:
            row[field] = newrow[field]

    return row


def prepareNameSuffix(results):
    """Parse and prepare name_suffix based on results."""
    counts = {'country_code': [], 'state': [], 'city': [], 'name': [], 'county': []}

    # Separate different country codes
    for row in results:
        for field in counts.keys():
            if field not in row:
                continue
            if row[field] in counts[field]:
                continue
            # Skip states for not-US
            if 'country_code' in row and row['country_code'] != 'us' and field == 'state':
                continue
            counts[field].append(row[field])

    # Prepare name suffix based on counts
    newresults = []
    for row in results:
        try:
            if not row['city']:
                row = parseDisplayName(row)

            name_suffix = []
            if (row['type'] != 'city' and len(row['city']) > 0 and row['name'] != row['city'] and
               (len(counts['city']) > 1 or len(counts['name']) > 1)):
                name_suffix.append(row['city'])
            if row['country_code'] == 'us' and len(counts['state']) > 1 and len(row['state']) > 0:
                name_suffix.append(row['state'])
            if len(counts['county']) > 1:
                name_suffix.append(row['county'])
            if len(counts['country_code']) > 1:
                name_suffix.append(row['country_code'].upper())
            row['name_suffix'] = ', '.join(name_suffix)
        except:
            pass
        newresults.append(row)

    return newresults


# ---------------------------------------------------------
def formatResponse(data, code=200):
    """Format response output."""
    # Format json - return empty
    result = data['result'] if 'result' in data else {}
    if app.debug and 'debug' in data:
        result['debug'] = data['debug']
    output_format = 'json'
    if request.args.get('format'):
        output_format = request.args.get('format')
    if 'format' in data:
        output_format = data['format']

    tpl = data['template'] if 'template' in data else 'answer.html'
    if output_format == 'html' and tpl is not None:
        if 'route' not in data:
            data['route'] = '/'
        return render_template(tpl, rc=(code == 200), **data), code

    json = dumps(result)
    mime = 'application/json'
    # Append callback for JavaScript
    if request.args.get('json_callback'):
        json = "{}({});".format(
            request.args.get('json_callback'),
            json)
        mime = 'application/javascript'
    if request.args.get('callback'):
        json = "{}({});".format(
            request.args.get('callback'),
            json)
        mime = 'application/javascript'
    resp = Response(json, mimetype=mime)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    # Cache results for 4 hours in Web Browsers and 12 hours in CDN caches
    resp.headers['Cache-Control'] = 'public, max-age=14400, s-maxage=43200'
    resp.headers['Last-Modified'] = DATA_LAST_MODIFIED
    return resp, code


# ---------------------------------------------------------
def modify_query_autocomplete(orig_query):
    """Modify query - add asterisk for each element of query, set original query."""
    query = '* '.join(re.compile("\s*,\s*|\s+").split(orig_query)) + '*'
    query = re.sub(r"\*+", "*", query)
    return query, orig_query


def modify_query_orig(orig_query):
    """Modify query - use and set original."""
    return orig_query, orig_query


def modify_query_remhouse(orig_query):
    """Modify query - remove house number, use and set modified query."""
    # Remove any number from the request
    query = re.sub(r"\d+([/, ]\d+)?", "", orig_query)
    if query == orig_query:
        return None, orig_query
    return query, query


def modify_query_splitor(orig_query):
    """Modify query - split query elements as OR, use modified and set original query."""
    if orig_query.startswith('@'):
        return None, orig_query
    query = ' | '.join(re.compile("\s*,\s*|\s+").split(orig_query))
    if query == orig_query:
        return None, orig_query
    return query, orig_query


def modify_query_postcode(orig_query):
    """Modify query - search and extract UK PostCode."""
    # Find UK postcode via regexp
    q = orig_query.upper()
    prog = re.compile(r"([A-Z0-9]{2,4}) ?([A-Z0-9]{3,3})")
    m = prog.match(q)
    if m:
        return "{} {}".format(m.group(1), m.group(2)), orig_query
    else:
        return None, orig_query


# ---------------------------------------------------------
def process_query_modifiers(orig_query, index_modifiers, debug_result, times,
                            query_filter, start, count, debug=False):
    """Process array of modifiers and return results."""
    rc = False
    result = {}
    proc_query = orig_query
    # Pair is (index, modify_function, [field_weights, [orig_query]])
    for pair in index_modifiers:
        index = pair[0]
        modify = pair[1]
        field_weights = ''
        if len(pair) >= 3:
            field_weights = pair[2]
        if len(pair) >= 4:
            proc_query = pair[3]
        if debug and index not in times:
            times[index] = {}
        # Cycle through few modifications of the query
        # Modification function return query with original query
        #  (possibly modified) used for the following processing
        query, proc_query = modify(proc_query)
        # No modification has been done
        if query is None:
            continue
        # Process modified query
        if debug:
            times['start_query'] = time()
        rc, result_new = process_search_index(
            index, query, query_filter,
            start, count, field_weights)
        if debug:
            times[index][modify.__name__] = time() - times['start_query']
        if rc and 'matches' in result_new and len(result_new['matches']) > 0:
            # Merge matches with previous result
            if 'matches' in result and len(result['matches']) > 0:
                result = mergeResultObject(result, result_new)
            else:
                result = result_new.copy()
                debug_result['modify'] = []
                debug_result['query_succeed'] = []
                debug_result['index_succeed'] = []
            debug_result['modify'].append(modify.__name__)
            debug_result['query_succeed'].append(query.decode('utf-8'))
            debug_result['index_succeed'].append(index.decode('utf-8'))
            # Only break, if we have enough matches
            if len(result['matches']) >= result['count']:
                break
        elif 'matches' not in result:
            result = result_new
    # for pair in index_modifiers
    return rc, result


# ---------------------------------------------------------
def search(orig_query, query_filter, autocomplete=False, start=0, count=0,
           debug=False, times={}, debug_result={}):
    """Common search method."""
    # Basic steps to search - using query modifiers over different index
    # 0. Detect pure Lat Lon (2 float numbers) query [last]
    # 1. Search in PostCodes (UK)
    # 2. Boosted prefix+exact on name
    # 3. Prefix on names - full text
    # 4. Infix with Soundex on names - full text
    # 5. If no results, try splitor on prefix and infix

    # Pair is (index, modify_function, [field_weights, [index_weights, [orig_query]]])
    index_modifiers = []
    result = {
        'matches': []
    }

    # 0. Detect pure Lat Lon (2 float numbers)
    floats = re.compile(r"(-?[0-9]+.?[0-9]*) (-?[0-9]+.?[0-9]*)")
    m = floats.match(orig_query)
    lat = lon = None
    if m:
        lat = float(m.group(1))
        lon = float(m.group(2))
    else:
        # Try parsing 50°00'00.0"N 14°00'00.0"E or similar requests
        query = orig_query
        query = query.replace('°', ' ')
        query = query.replace('\'', ' ')
        query = query.replace('\"', ' ')
        latlon = re.compile(r"([-0-9. ]+)([N|S]) *([-0-9. ]+)([E|W])").match(
            query.upper())
        if latlon:
            def degree_to_float(val, face):
                multipler = 1 if face in ['N', 'E'] else -1
                return multipler * sum(
                    float(x) / 60 ** n for n, x in enumerate(
                        re.split(r" +", val)))
            lat = degree_to_float(latlon.group(1).strip(), latlon.group(2))
            lon = degree_to_float(latlon.group(3).strip(), latlon.group(4))
    if lat and lon:
        classes = query_filter['class'] if 'class' in query_filter else []
        rev_result, distance = reverse_search(lon, lat, classes, debug)
        matches = [
            {
                'id': 0,
                'weight': 0,
                'attrs': {
                    'name': orig_query,
                    'display_name': orig_query,
                    'lat': lat,
                    'lon': lon,
                    'west': lon,
                    'south': lat,
                    'east': lon,
                    'north': lat,
                    'type': 'latlon',
                }
            },
        ]
        if len(rev_result['matches']):
            matches.append(rev_result['matches'][0])
        result = {
            'start_index': 0,
            'count': len(matches),
            'total_found': len(matches),
            'matches': matches
        }
        return True, result

    # 1. PostCodes (GB)
    index_modifiers.append((
        'ind_postcodes_infix',
        modify_query_postcode,
        'postcode = 1000')
    )

    # 2. Boosted name
    if autocomplete:
        index_modifiers.append((
            'ind_name_exact',
            modify_query_autocomplete,
            'name = 1000, alternative_names = 990',)
        )
        index_modifiers.append((
            'ind_name_prefix',
            modify_query_autocomplete,
            'name = 900, alternative_names = 890',)
        )
    index_modifiers.append((
        'ind_name_exact',
        modify_query_orig,
        'name = 800, alternative_names = 790',)
    )
    index_modifiers.append((
        'ind_name_prefix',
        modify_query_orig,
        'name = 700, alternative_names = 690',)
    )
    index_modifiers.append((
        'ind_name_exact',
        modify_query_remhouse,
        'name = 600, alternative_names = 590',
        orig_query,)
    )
    index_modifiers.append((
        'ind_name_prefix',
        modify_query_remhouse,
        'name = 500, alternative_names = 490',
        orig_query,)
    )

    # 3. Prefix on names
    if autocomplete:
        index_modifiers.append((
            'ind_names_prefix',
            modify_query_autocomplete,
            'name = 300, alternative_names = 290, display_name = 70',)
        )
    index_modifiers.append((
        'ind_names_prefix',
        modify_query_orig,
        'name = 200, alternative_names = 190, display_name = 60',)
    )
    index_modifiers.append((
        'ind_names_prefix',
        modify_query_remhouse,
        'name = 100, alternative_names = 95, display_name = 50',
        orig_query,)
    )

    if debug:
        pprint(index_modifiers)

    # 1. + 2. + 3.
    rc, result = process_query_modifiers(
        orig_query, index_modifiers, debug_result,
        times, query_filter, start, count, debug)

    if debug:
        pprint(rc)
        pprint(result)

    result_first = result
    # 4. + 5.
    if not rc or 'matches' not in result or len(result['matches']) == 0:
        index_modifiers = []
        # 4. Infix with soundex on names
        if autocomplete:
            index_modifiers.append((
                'ind_names_infix_soundex',
                modify_query_autocomplete,
                'name = 90, alternative_names = 89, display_name = 40',)
            )
        index_modifiers.append((
            'ind_names_infix_soundex',
            modify_query_orig,
            'name = 70, alternative_names = 69, display_name = 20',)
        )
        index_modifiers.append((
            'ind_names_infix_soundex',
            modify_query_remhouse,
            'name = 50, alternative_names = 49, display_name = 10',
            orig_query,)
        )
        # 5. If no result were found, try splitor modifier on prefix and infix soundex
        index_modifiers.append((
            'ind_names_prefix',
            modify_query_splitor,
            'name = 20, alternative_names = 19, display_name = 1',)
        )
        index_modifiers.append((
            'ind_names_infix_soundex',
            modify_query_splitor,
            'name = 10, alternative_names = 9, display_name = 1',)
        )
        rc, result = process_query_modifiers(
            orig_query, index_modifiers, debug_result,
            times, query_filter, start, count, debug)

    if debug:
        pprint(rc)
        pprint(result)
    if 'matches' not in result:
        result = result_first
    return rc, result


# ---------------------------------------------------------
def has_modified_header(headers):
    """
    Check request header for 'if-modified-since'.

    Return True if content wasn't modified (According to the timestamp)
    """
    global DATA_LAST_MODIFIED

    modified = headers.get('if-modified-since')
    if modified:
        oldLastModified = DATA_LAST_MODIFIED
        try:
            mtime = path.getmtime(TMPFILE_DATA_TIMESTAMP)
        except OSError:
            with open(TMPFILE_DATA_TIMESTAMP, 'a'):
                utime(TMPFILE_DATA_TIMESTAMP, None)
            mtime = time()
        DATA_LAST_MODIFIED = email.utils.formatdate(mtime, usegmt=True)
        if DATA_LAST_MODIFIED != oldLastModified:
            # reload attributes if index changed
            get_attributes_values('ind_name_exact', CHECK_ATTR_FILTER)
        # pprint([headers, modified, DATA_LAST_MODIFIED, mtime])
        # pprint([mtime, rfc822.parsedate(modified), mktime(rfc822.parsedate(modified))])
        modified_file = datetime.fromtimestamp(mtime)
        modified_file = modified_file.replace(microsecond=0)
        modified_date = datetime.fromtimestamp(mktime(rfc822.parsedate(modified)))

        # pprint([
        #     'Data: ', modified_file,
        #     'Header: ', modified_date,
        #     modified_file <= modified_date,
        # ])
        if modified_file <= modified_date:
            return True
    return False


# ---------------------------------------------------------
@app.route('/q/<query>.js', defaults={'country_code': None})
@app.route('/<country_code>/q/<query>.js')
def search_url(country_code, query):
    """Autocomplete searching via HTTP URL."""
    autocomplete = True
    code = 400
    data = {'query': '', 'route': '/', 'format': 'json'}
    query_filter = {}

    if has_modified_header(request.headers):
        data['result'] = {}
        return formatResponse(data, 304)

    if country_code is not None:
        if len(country_code) > 3:
            data['result'] = {'message': 'Invalid country code value.'}
            return formatResponse(data, code)
        query_filter = {'country_code': country_code.encode('utf-8').split(',')}

    # Common search for query with filters
    rc, result = search(query.encode('utf-8'), query_filter, autocomplete)
    if rc and len(result['matches']) > 0:
        code = 200

    data['query'] = query
    data['result'] = prepareResultJson(result)

    return formatResponse(data, code)


# Alias without redirect
@app.route('/q/<query>', defaults={'country_code': None})
@app.route('/<country_code>/q/<query>')
def search_url_public(country_code, query):
    if NOCACHEREDIRECT:
        return redirect(NOCACHEREDIRECT, code=302)

    return search_url(country_code, query)


# ---------------------------------------------------------
@app.route('/')
def search_query():
    """Global searching via HTTP Query."""
    if NOCACHEREDIRECT:
        return redirect(NOCACHEREDIRECT, code=302)

    data = {'query': '', 'route': '/', 'template': 'answer.html'}
    layout = request.args.get('layout')
    if layout and layout in ('answer', 'home'):
        data['template'] = request.args.get('layout') + '.html'
    code = 400

    if has_modified_header(request.headers):
        data['result'] = {}
        return formatResponse(data, 304)

    q = request.args.get('q')
    autocomplete = request.args.get('autocomplete')
    debug = request.args.get('debug')
    if debug:
        pprint([q, autocomplete, debug])

    times = {}
    debug_result = {}
    if debug:
        times['start'] = time()

    query_filter = {
        'type': None, 'class': None,
        'street': None, 'city': None,
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

    data['url'] = request.url
    data['query'] = q.encode('utf-8')
    orig_query = data['query']

    start = 0
    count = 0
    if request.args.get('startIndex'):
        try:
            start = int(request.args.get('startIndex'))
        except:
            pass
    if request.args.get('count'):
        try:
            count = int(request.args.get('count'))
        except:
            pass

    if debug:
        times['prepare'] = time() - times['start']

    # Common search for query with filters
    rc, result = search(orig_query, query_filter, autocomplete, start, count, debug, times, debug_result)
    if rc and len(result['matches']) > 0:
        code = 200

    data['query'] = orig_query.decode('utf-8')
    if debug:
        times['process'] = time() - times['start']
        debug_result['times'] = times
    data['result'] = prepareResultJson(result)
    data['debug_result'] = debug_result
    data['autocomplete'] = autocomplete
    data['debug'] = debug
    args = dict(request.args)
    if 'layout' in args:
        del(args['layout'])
    data['url_home'] = url_for('search_query', layout='home', **args)
    return formatResponse(data, code)


# ---------------------------------------------------------


class MyPrettyPrinter(PrettyPrinter):
    def format(self, object, context, maxlevels, level):
        if isinstance(object, unicode):
            return ('"' + object.encode('utf-8') + '"', True, False)
        return PrettyPrinter.format(self, object, context, maxlevels, level)


# Custom template filter - nl2br
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


# Custom template filter - ppretty
@app.template_filter()
def ppretty(value):
    return MyPrettyPrinter().pformat(value).decode('utf-8')


# =============================================================================
"""
Reverse geo-coding support

Author: Komodo Solutions
        enquiries@komodo-solutions.co.uk
        http://www.komodo-solutions.co.uk
Date:   11.07.2017
"""


# reverse_search - find the closest place in the data set to the supplied coordinates
# lon     - float   - the longitude coordinate, in degrees, for the closest place match
# lat     - float   - the latitude coordinate, in degrees, for the closest place match
# classes - array   - the array of classes to filter, empty array without filtering
# debug   - boolean - if true, include diagnostics in the result
# returns - result, distance tuple
def reverse_search(lon, lat, classes, debug):
    result = {
        'total_found': 0,
        'count': 0,
        'matches': []
    }

    if debug:
        result['debug'] = {
            'longitude': lon,
            'latitude': lat,
            'queries': [],
            'results': [],
        }

    try:
        db, cursor = get_db_cursor()
    except Exception as ex:
        status = False
        result['message'] = str(ex)
        result['status'] = status
        return result, 0

    # We attempt to find rows using a small bounding box to
    # limit the impact of the distance calculation.
    # If no rows are found with the current bounding box
    # we double it and try again, until a result is returned.

    delta = 0.0004
    count = 0

    while count == 0:
        delta *= 2
        lon_min = lon - delta
        lon_max = lon + delta
        lat_min = lat - delta
        lat_max = lat + delta

        # Bound the latitude
        lat_min = max(min(lat_min, 90.0), -90.0)
        lat_max = max(min(lat_max, 90.0), -90.0)
        # we use the built-in GEODIST function to calculate distance
        select = ("SELECT *, GEODIST(" + str(lat) + ", " + str(lon) +
                  ", lat, lon, {in=degrees, out=meters}) as distance"
                  " FROM ind_name_exact WHERE ")

        """
        SphinxQL does not support the OR operator or the NOT BETWEEN syntax so the only
        viable approach is to use 2 queries with different longitude conditions for
        180 meridan spanning cases
        """
        wherelon = []
        if (lon_min < -180.0):
            wherelon.append("lon BETWEEN {} AND 180.0".format(360.0 + lon_min))
            wherelon.append("lon BETWEEN -180.0 AND {}".format(lon_max))
        elif (lon_max > 180.0):
            wherelon.append("lon BETWEEN {} AND 180.0".format(lon_min))
            wherelon.append("lon BETWEEN -180.0 AND {}".format(-360.0 + lon_max))
        else:
            wherelon.append("lon BETWEEN {} AND {}".format(lon_min, lon_max))
        # latitude condition is the same for all cases
        wherelat = "lat BETWEEN {} AND {}".format(lat_min, lat_max)
        # limit the result set to the single closest match
        limit = " ORDER BY distance ASC LIMIT 1"

        myresult = {}
        if not classes:
            classes = [""]
        # form the final queries and execute
        for where in wherelon:
            for cl in classes:
                sql = select + " AND ".join([where, wherelat])
                if cl:
                    sql += " AND class='{}' ".format(cl)
                sql += limit
                # Boolean, {'matches': [{'weight': 0, 'id', 'attrs': {}}], 'total_found': 0}
                status, result_new = get_query_result(cursor, sql, ())
                if debug:
                    result['debug']['queries'].append(sql)
                    result['debug']['results'].append(result_new)
                if 'matches' in myresult and len(myresult['matches']) > 0:
                    myresult = mergeResultObject(myresult, result_new)
                else:
                    myresult = result_new.copy()

        count = len(myresult['matches'])
    db.close()

    if debug:
        result['debug']['matches'] = myresult['matches']

    smallest_row = None
    smallest_distance = None

    # For the rows returned, find the smallest calculated distance
    # (the 180 meridian case may result in 2 rows to check)
    for match in myresult['matches']:
        distance = match['attrs']['distance']

        if smallest_row is None or distance < smallest_distance:
            smallest_row = match
            smallest_distance = distance

    result = mergeResultObject(result, myresult)
    result['count'] = 1
    result['matches'] = [smallest_row]
    result['start_index'] = 1
    result['status'] = True
    result['total_found'] = 1
    return result, smallest_distance


# ---------------------------------------------------------
@app.route('/r/<lon>/<lat>.js', defaults={'classes': None})
@app.route('/r/<classes>/<lon>/<lat>.js')
def reverse_search_url(lon, lat, classes):
    """REST API for reverse_search."""
    code = 400
    data = {'format': 'json'}

    debug = request.args.get('debug')
    times = {}

    if debug:
        times['start'] = time()

    try:
        lon = float(lon)
        lat = float(lat)
    except:
        data['result'] = {'message': 'Longitude and latitude must be numeric.'}
        return formatResponse(data, code)

    if lon < -180.0 or lon > 180.0:
        data['result'] = {'message': 'Invalid longitude.'}
        return formatResponse(data, code)
    if lat < -90.0 or lat > 90.0:
        data['result'] = {'message': 'Invalid latitude.'}
        return formatResponse(data, code)

    if debug:
        times['prepare'] = time() - times['start']

    code = 200
    filter_classes = []
    if classes:
        # This argument can be list separated by comma
        filter_classes = classes.encode('utf-8').split(',')
    result, distance = reverse_search(lon, lat, filter_classes, debug)
    data['result'] = prepareResultJson(result)
    if debug:
        times['process'] = time() - times['start']
        data['debug'] = result['debug']
        data['debug']['distance'] = distance
        data['debug_times'] = times

    return formatResponse(data, code)


@app.route('/r/<lon>/<lat>', defaults={'classes': None})
@app.route('/r/<classes>/<lon>/<lat>')
def reverse_search_url_public(lon, lat, classes):
    if NOCACHEREDIRECT:
        return redirect(NOCACHEREDIRECT, code=302)

    return reverse_search_url(lon, lat, classes)

# =============================================================================
# End Reverse geo-coding support
# =============================================================================


# Load attributes at runtime
get_attributes_values('ind_name_exact', CHECK_ATTR_FILTER)
pprint(ATTR_VALUES)


"""
Main launcher
"""
if __name__ == '__main__':
    app.run(threaded=False, host='0.0.0.0', port=8000)
