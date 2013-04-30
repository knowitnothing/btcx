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
        self.last_tid = 0 if res is None else res[0]
        print(self.last_tid)

    def on_connect(self, _):
        self.mtgox.load_trades_since(tid=self.last_tid)

    def on_trade_fetch(self, (tid, timestamp, ttype, price, amount, coin)):
        if tid is None:
            self.db.commit()
            print("tid", self.last_tid, "<<")
            # ask for more!
            self.mtgox.load_trades_since(tid=self.last_tid)
            return
        #print("trade", tid, timestamp, ttype, price, amount)
        self.cursor.execute("INSERT INTO %s VALUES (?, ?, ?, ?, ?)"%self.table,
                (tid, timestamp, ttype, str(price), str(amount)))
        self.last_tid = max(self.last_tid, tid)


def main(key, secret):
    currency = 'USD' # Changing this to 'EUR' should work just fine.

    table = "btc%s" % (currency.lower())
    db = sqlite3.connect('mtgox_trades.db')
    cursor = db.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS %s (
            tid INTEGER PRIMARY KEY, timestamp INTEGER,
            ttype TEXT, price TEXT, amount TEXT)""" % table)
    db.commit()

    mtgox_client = mtgox.create_client(key, secret, currency)
    tradefetch = TradeFetchStore(db, table, mtgox_client)
    mtgox.start(mtgox_client)

    reactor.run()


if __name__ == "__main__":
    print('Create or/and load a key/secret pair for MtGox.\n')
    key, secret = cfgmanager.obtain_key_secret(sys.argv[1:])
    if key:
        main(key, secret)
