# See https://www.bitstamp.net/api/

from __future__ import print_function

import sys
from decimal import Decimal
from twisted.python import log

import common
from http import HTTPAPI


class Bitstamp(HTTPAPI): # XXX Only public data for the moment.

    def __init__(self, key, secret, host):
        super(Bitstamp, self).__init__(host)
        self.evt = common.ExchangeEvent(eventprefix="//bitstamp")


    # Public API

    def ticker(self):
        # last (last BTC price),
        # high (day), low (day), volume (day),
        # bid (highest buy order), ask (lowest sell order)
        self.http_call('api/ticker', lambda result, _:
                self.evt.emit('ticker', result)) # XXX Map to Decimal.

    def order_book(self, group=1):
        self.http_call('api/order_book', lambda result, _:
                self.evt.emit('order_book', result), # XXX Format.
                group=group)

    def transactions(self, timedelta=86400):
        """Obtain transactions for the last timedelta seconds."""
        self.http_call('api/transactions', self._handle_transactions)

    def reserves(self):
        """Obtain the Bitinstant USD reserves."""
        self.http_call('api/bitinstant', lambda result, _:
                self.evt.emit('reserves', Decimal(result['usd'])))

    def eur_usd_rate(self):
        # buy: buy conversion rate
        # sell: sell conversion rate
        self.http_call('api/eur_usd', lambda result, _:
                self.evt.emit('eur_usd', (
                    Decimal(result['buy']), Decimal(result['sell']))))

    def _handle_transactions(self, data, url):
        for item in reversed(data): # From oldest to newest.
            trade = common.Trade(item['tid'], int(item['date']), '',
                                 Decimal(item['price']),
                                 Decimal(item['amount']))
            self.evt.emit('trade_fetch', trade)
        self.evt.emit('trade_fetch', common.TRADE_EMPTY)

    # XXX Missing private.


def create_client(key='', secret='', addr='https://www.bitstamp.net'):
    return Bitstamp(key, secret, addr)
