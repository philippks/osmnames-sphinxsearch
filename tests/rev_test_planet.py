"""
Unit tests for reverse geocoding

Author: Komodo Solutions
        enquiries@komodo-solutions.co.uk
        http://www.komodo-solutions.co.uk
Date:   11.07.2017

1) Uses planet-latest[-100k].tsv.gz
2) Start a new docker container (using run.sh)
3) Run from within the docker container (docker exec -it <container> bash)
"""
from time import time, mktime
import sys
sys.path.insert(0, '/usr/local/src/websearch')

import websearch

col_name = 'name'

start = time()

#tests for exact lon/lat matches

test, distance = websearch.reverse_search(-0.144055,51.489334,False);
assert(test['results'][0][col_name]=='London')
print("London passed")

test, distance = websearch.reverse_search(2.320031,48.85881,False);
assert(test['results'][0][col_name]=='Paris')
print("Paris passed")

test, distance = websearch.reverse_search(11.525788,48.154583,False);
assert(test['results'][0][col_name]=='Munich')
print("Munich passed")

test, distance = websearch.reverse_search(37.617496,55.750683,False);
assert(test['results'][0][col_name]=='Moscow')
print("Moscow passed")

test, distance = websearch.reverse_search(54.370575,24.474796,False);
assert(test['results'][0][col_name]=='Abu Dhabi')
print("Abu Dhabi passed")

test, distance = websearch.reverse_search(120.983658,14.597873,False);
assert(test['results'][0][col_name]=='Manila')
print("Manila passed")

test, distance = websearch.reverse_search(103.852036,1.290453,False);
assert(test['results'][0][col_name]=='Singapore')
print("Singapore passed")

test, distance = websearch.reverse_search(139.758972,35.682838,False);
assert(test['results'][0][col_name]=='Tokyo')
print("Tokyo passed")

test, distance = websearch.reverse_search(178.442169,-18.141588,False);
assert(test['results'][0][col_name]=='Suva')
print("Suva passed")

test, distance = websearch.reverse_search(-157.846649,21.325079,False);
assert(test['results'][0][col_name]=='Honolulu')
print("Honolulu passed")

test, distance = websearch.reverse_search(-122.439552,37.818977,False);
assert(test['results'][0][col_name]=='San Francisco')
print("San Francisco passed")

test, distance = websearch.reverse_search(-71.05957,42.360481,False);
assert(test['results'][0][col_name]=='Boston')
print("Boston passed")

test, distance = websearch.reverse_search(-43.463989,-22.938034,False);
assert(test['results'][0][col_name]=='Rio de Janeiro')
print("Rio de Janeiro passed")

#tests for closeness lon/lat matches

#test, distance = websearch.reverse_search(37.617496,55.750683,False);
test, distance = websearch.reverse_search(37.617490,55.750680,False);
assert(test['results'][0][col_name]=='Moscow')
print("Moscow passed")
test, distance = websearch.reverse_search(37.617490,55.750690,False);
assert(test['results'][0][col_name]=='Moscow')
print("Moscow passed")
test, distance = websearch.reverse_search(37.617500,55.750690,False);
assert(test['results'][0][col_name]=='Moscow')
print("Moscow passed")
test, distance = websearch.reverse_search(37.617500,55.750680,False);
assert(test['results'][0][col_name]=='Moscow')
print("Moscow passed")

#test, distance = websearch.reverse_search(178.442169,-18.141588,False);
test, distance = websearch.reverse_search(178.442160,-18.141580,False);
assert(test['results'][0][col_name]=='Suva')
print("Suva passed")
test, distance = websearch.reverse_search(178.442160,-18.141590,False);
assert(test['results'][0][col_name]=='Suva')
print("Suva passed")
test, distance = websearch.reverse_search(178.442170,-18.141590,False);
assert(test['results'][0][col_name]=='Suva')
print("Suva passed")
test, distance = websearch.reverse_search(178.442170,-18.141580,False);
assert(test['results'][0][col_name]=='Suva')
print("Suva passed")

#test, distance = websearch.reverse_search(-43.463989,-22.938034,False);
test, distance = websearch.reverse_search(-43.463980,-22.938030,False);
assert(test['results'][0][col_name]=='Rio de Janeiro')
print("Rio de Janeiro passed")
test, distance = websearch.reverse_search(-43.463980,-22.938040,False);
assert(test['results'][0][col_name]=='Rio de Janeiro')
print("Rio de Janeiro passed")
test, distance = websearch.reverse_search(-43.463990,-22.938040,False);
assert(test['results'][0][col_name]=='Rio de Janeiro')
print("Rio de Janeiro passed")
test, distance = websearch.reverse_search(-43.463990,-22.938030,False);
assert(test['results'][0][col_name]=='Rio de Janeiro')
print("Rio de Janeiro passed")

#test, distance = websearch.reverse_search(-122.439552,37.818977,False);
test, distance = websearch.reverse_search(-122.439550,37.818970,False);
assert(test['results'][0][col_name]=='San Francisco')
print("San Francisco passed")
test, distance = websearch.reverse_search(-122.439550,37.818980,False);
assert(test['results'][0][col_name]=='San Francisco')
print("San Francisco passed")
test, distance = websearch.reverse_search(-122.439560,37.818980,False);
assert(test['results'][0][col_name]=='San Francisco')
print("San Francisco passed")
test, distance = websearch.reverse_search(-122.439560,37.818970,False);
assert(test['results'][0][col_name]=='San Francisco')
print("San Francisco passed")

end = time()

print "tests completed in ", end - start
