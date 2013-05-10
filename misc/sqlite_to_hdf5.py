import os
import sys
import pandas
import sqlite3
from pandas.io import sql as psql


DB = sys.argv[1]
TABLE = 'btcusd'

h5_name = os.path.splitext(DB)[0]
h5_group = '%s_%s' % (h5_name, TABLE)

store = pandas.HDFStore('%s.h5' % h5_name)

storer = store.get_storer('/%s' % h5_group)
if storer is not None:
    # Already stored something, grab last transaction tid.
    last_item = store.select(h5_group, start=storer.nrows - 1)
    last_tid = int(last_item.index[0][1])
else:
    last_tid = -1 # all-time data. This might take some time.

db = sqlite3.connect(DB, detect_types=sqlite3.PARSE_COLNAMES)
db.text_factory = str
query = """SELECT datetime(timestamp, 'unixepoch') as "ts [timestamp]",
        CAST(price as FLOAT) as price, CAST(amount as FLOAT) as volume, tid
        FROM [%s] WHERE tid > ? ORDER BY tid ASC LIMIT 5000""" % TABLE

while True:
    dataframe = psql.frame_query(query, con=db, params=(last_tid, ),
            index_col=['ts', 'tid'])

    if not len(dataframe) or last_tid == dataframe.index[-1][1]:
        print "Done"
        break

    print last_tid, dataframe.index[-1][1], len(dataframe)
    store.append(h5_group, dataframe)
    last_tid = int(dataframe.index[-1][1])

store.close()
