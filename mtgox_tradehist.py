from __future__ import print_function

import time
import sqlite3
import calendar
from decimal import Decimal

# Own modules
from btcx import mtgox


class TradeFetchStore(object):
    def __init__(self, db, table, mtgox_cli, max_hours_ago=4, verbose=1):
        self.verbose = verbose

        self.db = db
        self.table = table
        self.cursor = db.cursor()
        self.mtgox = mtgox_cli
        self.mtgox.call(self.load_from_last_stored,
                on_event=('connected', 'partial_download'))
        self.mtgox.evt.listen('trade_fetch', self.on_trade_fetch)
        self.cursor.execute("""SELECT tid FROM [%s]
                ORDER BY tid DESC LIMIT 1""" % self.table)
        res = self.cursor.fetchone()
        self.prev_last = None

        # Number of calls made and which did not finish yet.
        self._pending = False

        self.last_tid = 0 if res is None else res[0]
        if max_hours_ago is not None:
            self.last_tid = max(self.last_tid, mtgox.calc_tid(max_hours_ago))
        # Otherwise, if self.last_tid == 0 then be ready to download the
        # entire trade history!

        if verbose:
            print(self.last_tid)

    def load_from_last_stored(self, client):
        if self.verbose:
            print("Loading from", self.last_tid)
        if self._pending:
            if self.verbose:
                print("There is a pending call, returning")
            return
        self._pending = True
        client.load_trades_since(tid=self.last_tid)

    def on_trade_fetch(self, trade):
        if trade.id is None:
            self._pending = False
            self.db.commit()
            if self.verbose:
                print("tid", self.last_tid, self.prev_last, "<<")
            if self.prev_last == self.last_tid:
                if self.verbose:
                    print("Got it all, congrats.")
                self.mtgox.evt.emit('done', None)
            else:
                # Ask for more!
                if self.last_tid == 218868:
                    # Skip to id 1309100000000000 as MtGox is no
                    # longer returning data when 218868 <= tid < X.
                    jump_to = 1309100000000000
                    print("Jumping from tid %d to %d" % (self.last_tid,
                        jump_to))
                    self.last_tid = jump_to
                self.mtgox.evt.emit('partial_download', None)
                self.prev_last = self.last_tid
            return

        self.last_tid = max(self.last_tid, trade.id)
        if trade.price is None:
            # Trade in a different currency or not primary.
            return

        if self.verbose > 5:
            print("trade", trade)
        self.store_trade(trade)

    def store_trade(self, trade):
        query = "INSERT OR REPLACE INTO [%s] VALUES (?,?,?,?,?)" % self.table
        self.cursor.execute(query, (
            trade.id, trade.timestamp, trade.type,
            str(trade.price), str(trade.amount)))



def trades_from_db(db, hours_ago=Decimal('1.0'), raw_tid=None, rounding=True,
        table='btcusd'):
    if raw_tid is not None:
        since = raw_tid
    else:
        since = mtgox.calc_tid(hours_ago)
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
    reactor.run()
