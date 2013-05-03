from __future__ import print_function

import time
import sqlite3
import calendar
from decimal import Decimal

# Own modules
from btcx import mtgox


class TradeFetchStore(object):
    def __init__(self, db, table, mtgox, max_hours_ago=4, verbose=1):
        self.verbose = verbose

        self.db = db
        self.table = table
        self.cursor = db.cursor()
        self.mtgox = mtgox
        self.mtgox.evt.listen('connected', self.load_from_last_stored)
        self.mtgox.evt.listen('trade_fetch', self.on_trade_fetch)
        self.cursor.execute("""SELECT tid FROM [%s]
                ORDER BY tid DESC LIMIT 1""" % self.table)
        res = self.cursor.fetchone()
        self.prev_last = None

        self.last_tid = 0 if res is None else res[0]
        if max_hours_ago is not None:
            self.last_tid = max(self.last_tid, calc_tid(max_hours_ago))
        # Otherwise, if self.last_tid == 0 then be ready to download the
        # entire trade history!

        if verbose:
            print(self.last_tid)

    def load_from_last_stored(self, ignore=True):
        if self.verbose:
            print("Loading from", self.last_tid)
        self.mtgox.load_trades_since(tid=self.last_tid)

    def on_trade_fetch(self, (tid, timestamp, ttype, price, amount, coin)):
        if tid is None:
            self.db.commit()
            if self.verbose:
                print("tid", self.last_tid, self.prev_last, "<<")
            if self.prev_last == self.last_tid:
                if self.verbose:
                    print("Got it all, congrats.")
                self.mtgox.evt.emit('done', None)
            else:
                # Ask for more!
                self.mtgox.evt.emit('partial_download', None)
                self.prev_last = self.last_tid
                self.mtgox.load_trades_since(tid=self.last_tid)
            return

        self.last_tid = max(self.last_tid, tid)
        if price is None:
            # Trade in a different currency or not primary.
            return

        if self.verbose > 5:
            print("trade", tid, timestamp, ttype, price, amount)
        self.cursor.execute("INSERT INTO %s VALUES (?, ?, ?, ?, ?)"%self.table,
                (tid, timestamp, ttype, str(price), str(amount)))


# Either give a string to hours_ago or a Decimal object.
# XXX Duplicated code from load_trades_since at btcx.mtgox.
def calc_tid(hours_ago):
    hours_ago = Decimal(hours_ago)
    one_second = Decimal(1e6) # in microseconds
    now = int(time.time()) * one_second
    return int(now - (hours_ago * (one_second * 60 * 60)))


def trades_from_db(db, hours_ago=Decimal('1.0'), raw_tid=None, rounding=True,
        table='btcusd'):
    if raw_tid is not None:
        since = raw_tid
    else:
        since = calc_tid(hours_ago)
        if rounding:
            # Round to start on some exact minute.
            tstruct = list(time.gmtime(since/1e6))
            tstruct[5] = 0 # 0 seconds
            tstruct[4] = 0 # 0 minutes
            since = int(calendar.timegm(tstruct) * 1e6)

    return db.execute("""SELECT tid, timestamp, price, amount FROM [%s]
            WHERE tid > ? ORDER BY tid ASC""" % table, (since, )), since / 1e6

def setup_database(db, tablename):
    db.execute("""CREATE TABLE IF NOT EXISTS [%s] (
            tid INTEGER PRIMARY KEY, timestamp TIMESTAMP,
            ttype TEXT, price TEXT, amount TEXT)""" % tablename)
    db.execute("""
            CREATE INDEX IF NOT EXISTS [%s_ts] ON [%s] (timestamp)
            """ % (tablename, tablename))
    db.commit()

def setup_client(currency='USD', dbname='mtgox_trades.db', **kwargs):
    table = "btc%s" % currency.lower()
    db = sqlite3.connect(dbname)
    setup_database(db, table)

    mtgox_client = mtgox.create_client('', '', currency) # No key/secret.
    tradefetch = TradeFetchStore(db, table, mtgox_client, **kwargs)
    return mtgox_client, tradefetch, db


if __name__ == "__main__":
    from twisted.internet import reactor
    mtgox_client, tradefetch = setup_client()
    mtgox_client.evt.listen('done', lambda _: reactor.stop())
    mtgox.start(mtgox_client)
    reactor.run()