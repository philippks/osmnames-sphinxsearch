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

# Name for Sphinx searchd Link name
# SPHINX_LINK_NAME = getenv('SPHINX_LINK_NAME')

# # Mapping array
# # Maps /path from URL into sphinx index (in sphinx.conf)
# indexPorts = {'sheets': 'maprank_sheets', 'series': 'maprank_series',
#   'sheets_id': 'maprank_sheets_id', 'series_id': 'maprank_series_id'}

# # Prepare porting path to sphinx index
# sheets_from = getenv('SPHINX_MAP_SHEETS_FROM')
# if sheets_from:
#   sheets_to = getenv('SPHINX_MAP_SHEETS_TO')
#   if sheets_to:
#     indexPorts[sheets_from] = sheets_to
# series_from = getenv('SPHINX_MAP_SERIES_FROM')
# if series_from:
#   series_to = getenv('SPHINX_MAP_SERIES_TO')
#   if series_to:
#     indexPorts[series_from] = series_to
# sheets_id_from = getenv('SPHINX_MAP_SHEETS_ID_FROM')
# if sheets_id_from:
#   sheets_id_to = getenv('SPHINX_MAP_SHEETS_TO')
#   if sheets_id_to:
#     indexPorts[sheets_id_from] = sheets_id_to
# series_id_from = getenv('SPHINX_MAP_SERIES_ID_FROM')
# if series_id_from:
#   series_id_to = getenv('SPHINX_MAP_SERIES_ID_TO')
#   if series_id_to:
#     indexPorts[series_id_from] = series_id_to

"""
Process query to Sphinx searchd
"""
def process_query(ret, index, query):
  # default server configuration
  host = 'localhost'
  port = 9312
  # try:
  #   if SPHINX_LINK_NAME:
  #     host = getenv(SPHINX_LINK_NAME + '_PORT_9312_TCP_ADDR')
  #     if host:
  #       port = int(getenv(SPHINX_LINK_NAME + '_PORT_9312_TCP_PORT'))
  #     else:
  #       host = 'localhost'
  # except Exception, e:
  #   ret['error'] = 'Cannot connect to sphinx: ' + str(e)
  #   return False, None

  # if index in indexPorts:
    # index = indexPorts[index]

  repeat = 3
  # Repeate 3 times request because of socket.timeout
  while repeat > 0:
    try:
      cl = SphinxClient()
      cl.SetServer (host, port)
      cl.SetConnectTimeout(0.5) # float seconds
      cl.SetLimits(0, 20)#offset, limit, maxmatches=0, cutoff=0
      # Process query under index
      res = cl.Query ( query, index )
      repeat = 0
    except socket.timeout:
      repeat -= 1
  if request.args.get('debug'):
    ret['deb'] = {'host': host, 'port': port, 'index': index, 'query': query}
  if not res:
    ret['error'] = cl.GetLastError()
    return False, None
  #return False,None

  result = []
  if res.has_key('matches'):
    ret['matches_type'] = str(type(res['matches']))
    # Format results
    for row in res['matches']:
      r = row['attrs']
      rr = {}
      r['id'] = r['osm_id']
      # del r['sid']
      # if 'bbox' in r:
      #   bbox = r['bbox'].split(',')
      #   bbox = [float(v) for v in bbox]
      #   r['bbox'] = bbox
      if 'sindex' in r:
        del r['sindex']
      # Fixing values and types
      for attr in r:
        if r[attr] == 'None' or r[attr] is None:
          continue
        if isinstance(r[attr], str):
          r[attr] = r[attr].decode('utf-8')
        if attr in ('ort', 'bls', 'knr'):
          rr[ attr.upper() ] = r[ attr ]
        else:
          rr[ attr ] = r[attr]
      # Make bbox from north, south, east, west attributes
      rr['bbox'] = "{}, {}, {}, {}".format(r['north'], r['south'], r['east'], r['west'])
      # Make latlon from lat, lon
      rr['latlon'] = "{}, {}".format(r['lat'], r['lon'])
      result.append(rr)
  ret['result'] = result
    # ret['result'] = res['matches']
  # if res.has_key('words'):
    # ret['words'] = res['words']
  return True, result

"""
Format response output
"""
def formatResponse(rc, result, query):
  # Format json - return empty
  if not rc and request.args.get('format') == 'json':
    result = []

  if request.args.get('format') == 'html':
    return render_template('answer.html', results = result, query=query)
    # return Response('<pre>' + pformat( result ) + '</pre>', mimetype='text/html')

  json = dumps( result )
  mime = 'application/json'
  # Append callback for JavaScript
  if request.args.get('callback'):
    json = request.args.get('callback') + "("+json+");";
    mime = 'application/javascript'
  return Response(json, mimetype=mime)


"""
Searching for display name
"""
@app.route('/displayName')
def displayName():
  ret = {}
  rc = False
  index = 'display_name_index'
  q = request.args.get('q')
  #if re
  rc, result = process_query(ret, index, q)
  if rc and not request.args.get('debug'):
    ret = result
  return formatResponse(rc, ret, q)

"""
Routing root
"""
@app.route('/')
def root():
  return render_template('home.html')
  # return "<h1>Hello World!</h1>"
  # return formatResponse(False, {})


if __name__ == '__main__':
    app.run(threaded=False, host='0.0.0.0', port=8000)
