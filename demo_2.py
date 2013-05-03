from __future__ import print_function

import sys
import sqlite3
from twisted.internet import reactor

# Own modules
from btcx import mtgox, cfgmanager


class TradeFetchStore(object):
    def __init__(self, db, table, mtgox, last_tid=0):
        self.db = db
        self.table = table
        self.cursor = db.cursor()
        self.mtgox = mtgox
        self.mtgox.evt.listen('connected', self.on_connect)
        self.mtgox.evt.listen('trade_fetch', self.on_trade_fetch)
        self.cursor.execute("""SELECT tid FROM %s
                ORDER BY tid DESC LIMIT 1""" % self.table)
        res = self.cursor.fetchone()
        self.prev_last = None
        self.last_tid = 0 if res is None else res[0]
        print(self.last_tid)

    def on_connect(self, _):
        self.mtgox.load_trades_since(tid=self.last_tid)

    def on_trade_fetch(self, (tid, timestamp, ttype, price, amount, coin)):
        if tid is None:
            self.db.commit()
            print("tid", self.last_tid, self.prev_last, "<<")
            if self.prev_last == self.last_tid:
                print("Got it all, congrats.")
                reactor.stop()
            else:
                # Ask for more!
                self.prev_last = self.last_tid
                self.mtgox.load_trades_since(tid=self.last_tid)
            return

        self.last_tid = max(self.last_tid, tid)
        if price is None:
            # Trade in a different currency or not primary.
            return

        #print("trade", tid, timestamp, ttype, price, amount)
        self.cursor.execute("INSERT INTO %s VALUES (?, ?, ?, ?, ?)"%self.table,
                (tid, timestamp, ttype, str(price), str(amount)))


def main():
    currency = 'USD' # Changing this to 'EUR' should work just fine.

    table = "btc%s" % (currency.lower())
    db = sqlite3.connect('mtgox_trades.db')
    cursor = db.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS %s (
            tid INTEGER PRIMARY KEY, timestamp TIMESTAMP,
            ttype TEXT, price TEXT, amount TEXT)""" % table)
    cursor.execute("""
            CREATE INDEX IF NOT EXISTS %s_ts ON %s (timestamp)
            """ % (table, table))
    db.commit()

    mtgox_client = mtgox.create_client('', '', currency) # No key/secret.
    tradefetch = TradeFetchStore(db, table, mtgox_client)
    mtgox.start(mtgox_client)

    reactor.run()


if __name__ == "__main__":
    main()
