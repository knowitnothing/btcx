import os
import pandas
import sqlite3
from pandas.io import sql as psql

def sqlite_table_to_hdf5(db_name, table):
    h5_name = os.path.splitext(db_name)[0]
    h5_group = '%s_%s' % (h5_name, table)

    h5_out = '%s.h5' % h5_name
    print "Storage: %s   Group: %s" % (h5_out, h5_group)
    store = pandas.HDFStore(h5_out)

    storer = store.get_storer('/%s' % h5_group)
    if storer is not None:
        # Already stored something, grab last transaction tid.
        last_item = store.select(h5_group, start=storer.nrows - 1)
        last_tid = int(last_item.index[0][1])
    else:
        last_tid = -1 # all-time data. This might take some time.
    print "Last transaction ID: %d" % last_tid

    db = sqlite3.connect(db_name, detect_types=sqlite3.PARSE_COLNAMES)
    query = """SELECT datetime(timestamp, 'unixepoch') as "ts [timestamp]",
        CAST(price as FLOAT) as price, CAST(amount as FLOAT) as volume, tid
        FROM [%s] WHERE tid > ? ORDER BY tid ASC LIMIT 5000""" % table

    while True:
        dataframe = psql.frame_query(query, con=db, params=(last_tid, ),
                index_col=['ts', 'tid'])

        if not len(dataframe) or last_tid == dataframe.index[-1][1]:
            print "Done."
            break

        print last_tid, dataframe.index[-1][1], len(dataframe)
        store.append(h5_group, dataframe)
        last_tid = int(dataframe.index[-1][1])

    store.close()


if __name__ == "__main__":
    import sys
    dbname = sys.argv[1]
    table = sys.argv[2] if len(sys.argv) > 2 else 'btcusd'
    sqlite_table_to_hdf5(dbname, table)
