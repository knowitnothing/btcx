from __future__ import print_function

import sqlite3

# Own modules
from btcx import mtgox


class TradeFetchStore(object):
    def __init__(self, db, table, mtgox, verbose=1):
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
        if verbose:
            print(self.last_tid)

    def load_from_last_stored(self, ignore=True):
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
                self.prev_last = self.last_tid
                self.mtgox.load_trades_since(tid=self.last_tid)
            return

        self.last_tid = max(self.last_tid, tid)
        if price is None:
            # Trade in a different currency or not primary.
            return

        if self.verbose > 5:
            print("trade", tid, timestamp, ttype, price, amount)
        self.cursor.execute("INSERT INTO [%s] VALUES (?,?,?,?,?)" % self.table,
                (tid, timestamp, ttype, str(price), str(amount)))


def setup_database(db, tablename):
    db.execute("""CREATE TABLE IF NOT EXISTS [%s] (
            tid INTEGER PRIMARY KEY, timestamp TIMESTAMP,
            ttype TEXT, price TEXT, amount TEXT)""" % tablename)
    db.execute("""
            CREATE INDEX IF NOT EXISTS [%s_ts] ON [%s] (timestamp)
            """ % (tablename, tablename))
    db.commit()

def setup_client(currency='USD', dbname='mtgox_trades.db'):
    table = "btc%s" % currency.lower()
    db = sqlite3.connect(dbname)
    setup_database(db, table)

    mtgox_client = mtgox.create_client('', '', currency) # No key/secret.
    tradefetch = TradeFetchStore(db, table, mtgox_client)
    return mtgox_client, tradefetch


if __name__ == "__main__":
    from twisted.internet import reactor
    mtgox_client, tradefetch = setup_client()
    mtgox_client.evt.listen('done', lambda _: reactor.stop())
    mtgox.start(mtgox_client)
    reactor.run()
