# See -- if you know what to see, please tell me --

from __future__ import print_function

from decimal import Decimal

import common
from http import HTTPAPI


class BTCChina(HTTPAPI): # XXX Only public data for the moment.

    def __init__(self, key, secret, host):
        super(BTCChina, self).__init__(host)
        self.evt = common.Event(eventprefix="//btcchina")


    # Public API

    def ticker(self):
        # last (last BTC price),
        # high (day), low (day), vol (day),
        # buy (highest buy order), sell (lowest sell order)
        # Coin RMB (Renminbi)
        self.http_call('bc/ticker', lambda result, _:
                self.evt.emit('ticker', result['ticker']))

    def trades(self):
        self.http_call('bc/trades', self._handle_trades)

    def _handle_trades(self, data, url):
        # A list of trades. Each item contains date, price, amount, tid.
        for item in data:
            trade = common.Trade(int(item['tid']), int(item['date']), '',
                                 Decimal(str(item['price'])),
                                 Decimal(str(item['amount'])))
            self.evt.emit('trade_fetch', trade)
        self.evt.emit('trade_fetch', common.TRADE_EMPTY)

    # XXX Not sure what is missing.


def create_client(key='', secret='', addr='https://btcchina.com/'):
    return BTCChina(key, secret, addr)
