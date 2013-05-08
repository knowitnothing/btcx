import os
import sys
import sqlite3
from decimal import Decimal

import tables

from btcx.common import currency_factor


def export_sqlite_table(db, table, outh5, currency='usd'):
    factor = currency_factor(currency)

    mapping = { # column name: mapped data type
            'tid': tables.Int64Col(pos=1),
            'timestamp': tables.Time32Col(pos=2),
            'ttype': tables.StringCol(1, pos=3), # a(sk) / b(id)
            'price': tables.UInt64Col(pos=4),
            'amount': tables.UInt64Col(pos=5)
            }

    column = {'tid': int, 'timestamp': int,
              'ttype': lambda x: str(x)[0] if x else x,
              'price': lambda x: Decimal(x) * factor,
              'amount': lambda x: Decimal(x) * factor}

    column_order = [None] * len(mapping)
    for data in db.execute('PRAGMA table_info([%s])' % table):
        order, name = data[:2] # PRIMARY KEY info might be useful too ?
        column_order[order] = name.encode('utf8')

    hdf5 = tables.openFile(outh5, mode='w')
    root = hdf5.root

    mtgox = hdf5.createGroup(root, 'mtgox_trades')
    btcusd = hdf5.createTable(mtgox, table, mapping, expectedrows=5e6)
    btcusd.cols.tid.createIndex()
    btcusd.cols.timestamp.createIndex()
    btcusd_row = btcusd.row

    print "Now be patient.."
    count = 0
    for data in db.execute('SELECT * FROM [%s]' % table):
        for di, co in zip(data, column_order):
            btcusd_row[co] = column[co](di)
        btcusd_row.append()

        if not count % 1e4:
            sys.stdout.write('.')
            sys.stdout.flush()
        count += 1
    print "Done!"

    btcusd.flush()
    hdf5.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print "Usage: %s somesqlite.db table out.h5" % sys.argv[0]
        print "  * Result will be written to out.h5 with group 'mtgox_trades'"
        print "    and a table of specified name"
        raise SystemExit

    dbname, tablename, out_h5 = sys.argv[1:]
    db = sqlite3.connect(dbname)
    export_sqlite_table(db, tablename, out_h5)
