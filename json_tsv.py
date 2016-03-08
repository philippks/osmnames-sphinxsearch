import fileinput
import json
from pprint import pprint

columns = {
    "id": "i:osm_id",
    "osm_id": "i:osm_id",
    "display_name": "s:display_name",
    "name":  "s:display_name",
    "class": "s:class",
    "type": "s:type",
    "north": "f:boundingbox.0",
    "south": "f:boundingbox.1",
    "east": "f:boundingbox.2",
    "west": "f:boundingbox.3",
    "lat": "f:lat",
    "lon": "f:lon",
}

column_order = ["id", "display_name", "class", "type", "lon", "lat", "west", "south", "east", "north"]

# s = []
# for col in columns:
    # s.append("\"{}\"".format(col))
# pprint(s)
# print("\t".join(s))
# print("\"osm_id\"\t\"display_name\"\t\"name\"\t\"class\"\t\"type\"\t\"north\"\t\"south\"\t\"east\"\t\"west\"\t\"lat\"\t\"lon\"")

for line in fileinput.input():
    try:
        obj = json.loads(line)
    except ValueError:
        raise
        continue
    s = []
    for col in column_order:
        json_column = columns[col]
        format = json_column[0]
        json_column = columns[col][2:]
        value = ""
        # pprint([format, json_column, columns[col]])
        if '.' in json_column:
            cx = json_column.split('.')
            # pprint( obj[cx[0]] )
            # pprint( obj[cx[0]][0] )
            value = obj[cx[0]][int(cx[1])]
        else:
            value = obj[json_column]
            # pprint(cx)
        if format == 's':
            #s.append( "\"{}\"".format(value) )
            s.append( "{}".format(value) )
        elif format == 'i':
            s.append( str(int(value)) )
        elif format == 'f':
            s.append( str(float(value)) )
        # else:
            # pprint(col)
    #pprint(s)
    print("\t".join(s))
    #print("{}".format())