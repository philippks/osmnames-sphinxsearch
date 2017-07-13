"""
Unit tests for reverse geocoding

Author: Komodo Solutions
        enquiries@komodo-solutions.co.uk
        http://www.komodo-solutions.co.uk
Date:   11.07.2017

1) Ensure that rev_test.tsv has been copied to data/input/data.tsv
2) Start a new docker container (using run.sh)
3) Run from within the docker container (docker exec -it <container> bash)
"""
from time import time, mktime
import sys
sys.path.insert(0, '/usr/local/src/websearch')

import websearch

col_id = 'osm_id'
col_name = 'name'

times = {}
times['start'] = time()

#test for precise lon/lat matches

test, distance = websearch.reverse_search(0.0,0.0,False);
assert(test['results'][0][col_name]=='zero zero')
print("test 1a passed")

test, distance = websearch.reverse_search(25.0,25.0,False);
assert(test['results'][0][col_name]=='NE quadrant 1')
print("test 1b passed")

test, distance = websearch.reverse_search(25.0,-25.0,False);
assert(test['results'][0][col_name]=='NW quadrant 1')
print("test 1c passed")

test, distance = websearch.reverse_search(-25.0,-25.0,False);
assert(test['results'][0][col_name]=='SW quadrant 1')
print("test 1d passed")

test, distance = websearch.reverse_search(-25.0,25.0,False);
assert(test['results'][0][col_name]=='SE quadrant 1')
print("test 1e passed")

#test for nearness matches

test, distance = websearch.reverse_search(24.5,24.5,False);
assert(test['results'][0][col_name]=='NE quadrant 1')
print("test 2a passed")

test, distance = websearch.reverse_search(24.5,-24.5,False);
assert(test['results'][0][col_name]=='NW quadrant 1')
print("test 2b passed")

test, distance = websearch.reverse_search(-24.5,-24.5,False);
assert(test['results'][0][col_name]=='SW quadrant 1')
print("test 2c passed")

test, distance = websearch.reverse_search(-24.5,24.5,False);
assert(test['results'][0][col_name]=='SE quadrant 1')
print("test 2d passed")

test, distance = websearch.reverse_search(25.2,25.2,False);
assert(test['results'][0][col_name]=='NE quadrant 2')
print("test 2e passed")

test, distance = websearch.reverse_search(25.2,-25.2,False);
assert(test['results'][0][col_name]=='NW quadrant 2')
print("test 2f passed")

test, distance = websearch.reverse_search(-25.2,-25.2,False);
assert(test['results'][0][col_name]=='SW quadrant 2')
print("test 2g passed")

test, distance = websearch.reverse_search(-25.2,25.2,False);
assert(test['results'][0][col_name]=='SE quadrant 2')
print("test 2h passed")

test, distance = websearch.reverse_search(25.04,25.04,False);
assert(test['results'][0][col_name]=='NE quadrant 1')
print("test 2i passed")

test, distance = websearch.reverse_search(25.04,-25.04,False);
assert(test['results'][0][col_name]=='NW quadrant 1')
print("test 2j passed")

test, distance = websearch.reverse_search(-25.04,-25.04,False);
assert(test['results'][0][col_name]=='SW quadrant 1')
print("test 2k passed")

test, distance = websearch.reverse_search(-25.04,25.04,False);
assert(test['results'][0][col_name]=='SE quadrant 1')
print("test 2l passed")

test, distance = websearch.reverse_search(25.06,25.06,False);
assert(test['results'][0][col_name]=='NE quadrant 2')
print("test 2m passed")

test, distance = websearch.reverse_search(25.06,-25.06,False);
assert(test['results'][0][col_name]=='NW quadrant 2')
print("test 2n passed")

test, distance = websearch.reverse_search(-25.06,-25.06,False);
assert(test['results'][0][col_name]=='SW quadrant 2')
print("test 2o passed")

test, distance = websearch.reverse_search(-25.06,25.06,False);
assert(test['results'][0][col_name]=='SE quadrant 2')
print("test 2p passed")

#tests for 180 meridian

# - +N
test, distance = websearch.reverse_search(178.3,40.8,False);
assert(test['results'][0][col_name]=='180 plus north')
print("test 3a passed")

test, distance = websearch.reverse_search(179.5,40.8,False);
assert(test['results'][0][col_name]=='180 plus north')
print("test 3b passed")

test, distance = websearch.reverse_search(-179.7,40.8,False);
assert(test['results'][0][col_name]=='180 plus north')
print("test 3c passed")

test, distance = websearch.reverse_search(178.3,40.0,False);
assert(test['results'][0][col_name]=='180 plus north')
print("test 3d passed")

test, distance = websearch.reverse_search(179.5,40.0,False);
assert(test['results'][0][col_name]=='180 plus north')
print("test 3e passed")

test, distance = websearch.reverse_search(-179.7,40.0,False);
assert(test['results'][0][col_name]=='180 plus north')
print("test 3f passed")

test, distance = websearch.reverse_search(178.3,39.2,False);
assert(test['results'][0][col_name]=='180 plus north')
print("test 3g passed")

test, distance = websearch.reverse_search(179.5,39.2,False);
assert(test['results'][0][col_name]=='180 plus north')
print("test 3h passed")

test, distance = websearch.reverse_search(-179.7,39.2,False);
assert(test['results'][0][col_name]=='180 plus north')
print("test 3i passed")

# - -N
test, distance = websearch.reverse_search(179.3,49.2,False);
assert(test['results'][0][col_name]=='180 minus north')
print("test 4a passed")

test, distance = websearch.reverse_search(-179.5,49.2,False);
assert(test['results'][0][col_name]=='180 minus north')
print("test 4b passed")

test, distance = websearch.reverse_search(-178.7,49.2,False);
assert(test['results'][0][col_name]=='180 minus north')
print("test 4c passed")

test, distance = websearch.reverse_search(179.3,50.0,False);
assert(test['results'][0][col_name]=='180 minus north')
print("test 4d passed")

test, distance = websearch.reverse_search(-179.5,50.0,False);
assert(test['results'][0][col_name]=='180 minus north')
print("test 4e passed")

test, distance = websearch.reverse_search(-178.7,50.0,False);
assert(test['results'][0][col_name]=='180 minus north')
print("test 4f passed")

test, distance = websearch.reverse_search(179.3,50.8,False);
assert(test['results'][0][col_name]=='180 minus north')
print("test 4g passed")

test, distance = websearch.reverse_search(-179.5,50.8,False);
assert(test['results'][0][col_name]=='180 minus north')
print("test 4h passed")

test, distance = websearch.reverse_search(-178.7,50.8,False);
assert(test['results'][0][col_name]=='180 minus north')
print("test 4i passed")

# - +S
test, distance = websearch.reverse_search(178.3,-40.8,False);
assert(test['results'][0][col_name]=='180 plus south')
print("test 5a passed")

test, distance = websearch.reverse_search(179.5,-40.8,False);
assert(test['results'][0][col_name]=='180 plus south')
print("test 5b passed")

test, distance = websearch.reverse_search(-179.7,-40.8,False);
assert(test['results'][0][col_name]=='180 plus south')
print("test 5c passed")

test, distance = websearch.reverse_search(178.3,-40.0,False);
assert(test['results'][0][col_name]=='180 plus south')
print("test 5d passed")

test, distance = websearch.reverse_search(179.5,-40.0,False);
assert(test['results'][0][col_name]=='180 plus south')
print("test 5e passed")

test, distance = websearch.reverse_search(-179.7,-40.0,False);
assert(test['results'][0][col_name]=='180 plus south')
print("test 5f passed")

test, distance = websearch.reverse_search(178.3,-39.2,False);
assert(test['results'][0][col_name]=='180 plus south')
print("test 5g passed")

test, distance = websearch.reverse_search(179.5,-39.2,False);
assert(test['results'][0][col_name]=='180 plus south')
print("test 5h passed")

test, distance = websearch.reverse_search(-179.7,-39.2,False);
assert(test['results'][0][col_name]=='180 plus south')
print("test 5i passed")

# - -S
test, distance = websearch.reverse_search(179.3,-49.2,False);
assert(test['results'][0][col_name]=='180 minus south')
print("test 6a passed")

test, distance = websearch.reverse_search(-179.5,-49.2,False);
assert(test['results'][0][col_name]=='180 minus south')
print("test 6b passed")

test, distance = websearch.reverse_search(-178.7,-49.2,False);
assert(test['results'][0][col_name]=='180 minus south')
print("test 6c passed")

test, distance = websearch.reverse_search(179.3,-50.0,False);
assert(test['results'][0][col_name]=='180 minus south')
print("test 6d passed")

test, distance = websearch.reverse_search(-179.5,-50.0,False);
assert(test['results'][0][col_name]=='180 minus south')
print("test 6e passed")

test, distance = websearch.reverse_search(-178.7,-50.0,False);
assert(test['results'][0][col_name]=='180 minus south')
print("test 6f passed")

test, distance = websearch.reverse_search(179.3,-50.8,False);
assert(test['results'][0][col_name]=='180 minus south')
print("test 6g passed")

test, distance = websearch.reverse_search(-179.5,-50.8,False);
assert(test['results'][0][col_name]=='180 minus south')
print("test 6h passed")

test, distance = websearch.reverse_search(-178.7,-50.8,False);
assert(test['results'][0][col_name]=='180 minus south')
print("test 6i passed")

#test for full result set (>20 records)
"""
test, distance = websearch.reverse_search(44.000025,44.000025,True);
assert(len(test['debug']['matches'])==25)
print("test 7 passed")
"""
times['end'] = time()
times['duration'] = times['end'] - times['start']

print "tests completed in ", times['duration']
